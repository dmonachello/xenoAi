from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import sqlite3

import pytest

from xenosculpt.comfyui.client import (
    ComfyHistory,
    ComfyPromptRejected,
    ComfySubmission,
    ComfySystem,
)
from xenosculpt.core import WorkspaceError
from xenosculpt.comfyui.workspace import ComfyProject, RunState
from xenosculpt.comfyui.workflow import LiteralInput


FIXTURE = Path(__file__).parent / "fixtures" / "comfyui" / "empty-image-api.json"
PNG = b"\x89PNG\r\n\x1a\n" + b"test-image"


class ScriptedClient:
    origin = "http://127.0.0.1:8188"

    def __init__(self) -> None:
        self.submissions = 0
        self.request: dict[str, object] | None = None

    def system_stats(self) -> ComfySystem:
        return ComfySystem(version="0.3.45", raw={"system": {"comfyui_version": "0.3.45"}})

    def submit(self, request: dict[str, object]) -> ComfySubmission:
        self.submissions += 1
        self.request = request
        return ComfySubmission(prompt_id=str(request["prompt_id"]), raw={"number": 1})

    def history(self, prompt_id: str) -> ComfyHistory | None:
        return ComfyHistory(
            completed=True,
            success=True,
            raw={
                "prompt": [1, prompt_id, self.request["prompt"], {}, []],
                "outputs": {"2": {"images": [{"filename": "out.png", "subfolder": "", "type": "output"}]}},
                "status": {"completed": True, "status_str": "success"},
            },
        )

    def download(self, locator: dict[str, str]) -> tuple[bytes, str]:
        return PNG, "image/png"


class ChangedPromptClient(ScriptedClient):
    def history(self, prompt_id: str) -> ComfyHistory | None:
        result = super().history(prompt_id)
        assert result is not None
        result.raw["prompt"][2]["1"]["inputs"]["width"] = 64.0
        return result


class UnsupportedOutputClient(ScriptedClient):
    def history(self, prompt_id: str) -> ComfyHistory | None:
        result = super().history(prompt_id)
        assert result is not None
        result.raw["outputs"] = {"2": {"audio": [{"filename": "out.wav"}]}}
        return result


class RejectedClient(ScriptedClient):
    def submit(self, request: dict[str, object]) -> ComfySubmission:
        raise ComfyPromptRejected({"error": {"type": "prompt_outputs_failed_validation"}})


class FailedExecutionClient(ScriptedClient):
    def history(self, prompt_id: str) -> ComfyHistory | None:
        return ComfyHistory(
            completed=True,
            success=False,
            raw={
                "prompt": [1, prompt_id, self.request["prompt"], {}, []],
                "outputs": {},
                "status": {
                    "completed": False,
                    "status_str": "error",
                    "messages": [["execution_error", {"exception_message": "bad node"}]],
                },
            },
        )


def test_run_is_durable_and_retains_content_addressed_output(tmp_path) -> None:
    project = ComfyProject.create(tmp_path / "image.csp", FIXTURE)
    client = ScriptedClient()

    run = project.run(client, timeout_seconds=1, poll_seconds=0)

    assert run.state is RunState.SUCCEEDED
    assert run.comfyui_version == "0.3.45"
    assert client.submissions == 1
    assert len(run.outputs) == 1
    assert Path(run.outputs[0].path).read_bytes() == PNG
    assert project.resume(run.id, client, timeout_seconds=1, poll_seconds=0).id == run.id
    assert client.submissions == 1


def test_run_retains_server_normalized_prompt_identity(tmp_path) -> None:
    project = ComfyProject.create(tmp_path / "image.csp", FIXTURE)
    run = project.run(ChangedPromptClient(), timeout_seconds=1, poll_seconds=0)

    assert run.state is RunState.SUCCEEDED
    assert run.accepted_prompt_sha256 != run.submitted_prompt_sha256


def test_run_is_incomplete_for_unsupported_outputs(tmp_path) -> None:
    project = ComfyProject.create(tmp_path / "image.csp", FIXTURE)
    run = project.run(UnsupportedOutputClient(), timeout_seconds=1, poll_seconds=0)

    assert run.state is RunState.OUTPUT_INCOMPLETE
    assert "unsupported output" in run.error["message"]


def test_successful_run_rechecks_retained_output_hash(tmp_path) -> None:
    project = ComfyProject.create(tmp_path / "image.csp", FIXTURE)
    run = project.run(ScriptedClient(), timeout_seconds=1, poll_seconds=0)
    Path(run.outputs[0].path).write_bytes(b"corrupt")

    with pytest.raises(WorkspaceError, match="hash verification"):
        project.get_run(run.id)


def test_run_rejects_corrupt_stored_request_identity(tmp_path) -> None:
    project = ComfyProject.create(tmp_path / "image.csp", FIXTURE)
    client = ScriptedClient()
    original_history = client.history

    def corrupt_before_history(prompt_id: str) -> ComfyHistory | None:
        with sqlite3.connect(project.database) as connection:
            connection.execute("UPDATE comfy_runs SET request_sha256 = 'bad'")
            connection.commit()
        return original_history(prompt_id)

    client.history = corrupt_before_history  # type: ignore[method-assign]
    with pytest.raises(WorkspaceError, match="request failed hash verification"):
        project.run(client, timeout_seconds=1, poll_seconds=0)


def test_definite_prompt_validation_failure_is_rejected(tmp_path) -> None:
    project = ComfyProject.create(tmp_path / "image.csp", FIXTURE)

    run = project.run(RejectedClient(), timeout_seconds=1, poll_seconds=0)

    assert run.state is RunState.REJECTED
    assert run.comfyui_version == "0.3.45"
    assert run.error["details"]["error"]["type"] == "prompt_outputs_failed_validation"


def test_execution_failure_retains_actionable_diagnostics(tmp_path) -> None:
    project = ComfyProject.create(tmp_path / "image.csp", FIXTURE)

    run = project.run(FailedExecutionClient(), timeout_seconds=1, poll_seconds=0)

    assert run.state is RunState.FAILED
    assert run.error["status_str"] == "error"
    assert run.error["messages"][0][1]["exception_message"] == "bad node"
    assert run.comfyui_version == "0.3.45"


def test_request_must_remain_bound_to_revision_artifact(tmp_path) -> None:
    project = ComfyProject.create(tmp_path / "image.csp", FIXTURE)
    run = project.run(ScriptedClient(), timeout_seconds=1, poll_seconds=0)
    with sqlite3.connect(project.database) as connection:
        request = json.loads(
            connection.execute(
                "SELECT request_json FROM comfy_runs WHERE id = ?", (run.id,)
            ).fetchone()[0]
        )
        request["prompt"]["1"]["inputs"]["width"] = 128
        request_text = json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        connection.execute(
            "UPDATE comfy_runs SET request_json = ?, request_sha256 = ? WHERE id = ?",
            (request_text, sha256(request_text.encode()).hexdigest(), run.id),
        )
        connection.commit()

    with pytest.raises(WorkspaceError, match="revision artifact"):
        project.get_run(run.id)


def test_terminal_run_state_cannot_regress(tmp_path) -> None:
    project = ComfyProject.create(tmp_path / "image.csp", FIXTURE)
    run = project.run(ScriptedClient(), timeout_seconds=1, poll_seconds=0)

    project._update_run(
        run.id,
        RunState.SUBMITTED,
        error={"message": "stale poller"},
    )

    current = project.get_run(run.id)
    assert current.state is RunState.SUCCEEDED
    assert current.error is None


def test_output_path_must_remain_inside_run_artifacts(tmp_path) -> None:
    project = ComfyProject.create(tmp_path / "image.csp", FIXTURE)
    run = project.run(ScriptedClient(), timeout_seconds=1, poll_seconds=0)
    with sqlite3.connect(project.database) as connection:
        connection.execute(
            "UPDATE comfy_outputs SET relative_path = ? WHERE run_id = ?",
            ("../outside.png", run.id),
        )
        connection.commit()

    with pytest.raises(WorkspaceError, match="escapes run-artifacts"):
        project.get_run(run.id)


def test_run_revision_identity_cannot_be_shadowed_by_branch_name(tmp_path) -> None:
    project = ComfyProject.create(tmp_path / "image.csp", FIXTURE)
    run = project.run(ScriptedClient(), timeout_seconds=1, poll_seconds=0)
    project.create_branch(run.revision_id, checkout=True)
    project.set_input("1", "width", LiteralInput(96), message="advance shadow branch")

    assert project.get_run(run.id).revision_id == run.revision_id
