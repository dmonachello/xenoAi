"""ComfyUI workspace facade over the application-neutral revision core."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
import json
import os
from pathlib import Path
import sqlite3
import time
from typing import Any, Protocol
from uuid import uuid4

from xenosculpt.core import (
    ApplicationIdentity,
    ApplyResult,
    Revision,
    RevisionWorkspace,
    WorkspaceError,
)

from .client import ComfyHistory, ComfyPromptRejected, ComfySubmission, ComfySystem
from .workflow import (
    ApiWorkflow,
    InputMutation,
    LiteralInput,
    NodeLink,
    apply_input,
    compare_workflows,
    parse_workflow,
)


COMFYUI_APPLICATION = ApplicationIdentity(
    "comfyui", "comfyui/api-workflow/v1", ".json"
)
_SCHEMA_VERSION = "1"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":"))


class RunState(str, Enum):
    PREPARED = "prepared"
    SUBMISSION_UNKNOWN = "submission_unknown"
    SUBMITTED = "submitted"
    OUTPUT_INCOMPLETE = "output_incomplete"
    SUCCEEDED = "succeeded"
    REJECTED = "rejected"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class RunOutput:
    node_id: str
    ordinal: int
    sha256: str
    bytes: int
    media_type: str
    path: str


@dataclass(frozen=True, slots=True)
class ComfyRun:
    id: str
    revision_id: str
    artifact_sha256: str
    prompt_id: str
    server_origin: str
    created_at: str
    updated_at: str
    state: RunState
    comfyui_version: str | None
    environment: dict[str, Any] | None
    submitted_prompt_sha256: str
    accepted_prompt_sha256: str | None
    outputs: tuple[RunOutput, ...]
    error: dict[str, Any] | None


@dataclass(frozen=True, slots=True)
class ComfyStatus:
    root: str
    application_id: str
    document_kind: str
    current_branch: str | None
    branches: dict[str, str]
    head: Revision
    node_count: int
    latest_run: ComfyRun | None


class ComfyApi(Protocol):
    origin: str

    def system_stats(self) -> ComfySystem: ...
    def submit(self, request: dict[str, object]) -> ComfySubmission: ...
    def history(self, prompt_id: str) -> ComfyHistory | None: ...
    def download(self, locator: dict[str, str]) -> tuple[bytes, str]: ...


class ComfyProject(RevisionWorkspace):
    def __init__(self, root: Path) -> None:
        super().__init__(root, COMFYUI_APPLICATION)
        self.run_artifacts = self.root / "run-artifacts"

    @classmethod
    def create(cls, root: str | Path, source: str | Path) -> "ComfyProject":
        workspace = cls(Path(root))
        source_path = Path(source).resolve()
        if workspace.root.exists():
            raise WorkspaceError(f"refusing to overwrite: {workspace.root}")
        source_data = source_path.read_bytes()
        workflow = parse_workflow(source_data)
        data = workflow.to_bytes()
        workspace.root.mkdir(parents=True)
        workspace.run_artifacts.mkdir()
        temporary_database = workspace.root / f".project.{uuid4().hex}.tmp"
        try:
            connection = sqlite3.connect(temporary_database)
            try:
                created_at = _now()
                workspace.initialize_history(
                    connection,
                    source_data=data,
                    created_at=created_at,
                    operation="init",
                    details={"source_sha256": sha256(source_data).hexdigest()},
                    message="Import ComfyUI API workflow",
                    prompt=None,
                    metadata={
                        "schema_version": _SCHEMA_VERSION,
                        "created_at": created_at,
                        "source_path": str(source_path),
                    },
                )
                connection.executescript(
                    """
                    CREATE TABLE comfy_runs (
                        id TEXT PRIMARY KEY,
                        revision_id TEXT NOT NULL REFERENCES revisions(id),
                        artifact_sha256 TEXT NOT NULL,
                        prompt_id TEXT NOT NULL UNIQUE,
                        client_id TEXT NOT NULL,
                        server_origin TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        state TEXT NOT NULL,
                        request_sha256 TEXT NOT NULL,
                        request_json TEXT NOT NULL,
                        submission_json TEXT,
                        history_json TEXT,
                        environment_json TEXT,
                        error_json TEXT
                    );
                    CREATE INDEX comfy_runs_revision_created
                    ON comfy_runs(revision_id, created_at DESC, id DESC);
                    CREATE TABLE comfy_outputs (
                        id TEXT PRIMARY KEY,
                        run_id TEXT NOT NULL REFERENCES comfy_runs(id),
                        node_id TEXT NOT NULL,
                        ordinal INTEGER NOT NULL,
                        artifact_sha256 TEXT NOT NULL,
                        bytes INTEGER NOT NULL,
                        media_type TEXT NOT NULL,
                        relative_path TEXT NOT NULL,
                        locator_json TEXT NOT NULL,
                        UNIQUE(run_id, node_id, ordinal)
                    );
                    """
                )
                connection.commit()
            finally:
                connection.close()
            os.replace(temporary_database, workspace.database)
        finally:
            if temporary_database.exists():
                temporary_database.unlink()
        return workspace

    @classmethod
    def open(cls, root: str | Path) -> "ComfyProject":
        workspace = cls(Path(root))
        if not workspace.database.is_file():
            raise WorkspaceError(f"not a project workspace: {workspace.root}")
        with workspace._connect() as connection:
            row = connection.execute("SELECT value FROM metadata WHERE key = 'schema_version'").fetchone()
            if row is None or row[0] != _SCHEMA_VERSION:
                raise WorkspaceError("unsupported or missing ComfyUI workspace schema")
            workspace.verify_application_identity(connection)
        workspace.run_artifacts.mkdir(exist_ok=True)
        return workspace

    def _revision_for_ref(self, connection: sqlite3.Connection, ref: str) -> Revision:
        if ref.startswith("HEAD~") and ref[5:].isdigit():
            count = int(ref[5:])
            revision = self._get_revision(connection, "HEAD")
            for _ in range(count):
                if revision.parent_id is None:
                    raise WorkspaceError(f"reference {ref!r} is before the first revision")
                revision = self._get_revision(connection, revision.parent_id)
            return revision
        return self._get_revision(connection, ref)

    def status(self) -> ComfyStatus:
        with self._connect() as connection:
            head = self._get_revision(connection, "HEAD")
            _, branch = self._head_id(connection)
            branches = dict(connection.execute("SELECT name, revision_id FROM branches ORDER BY name"))
            latest = connection.execute(
                "SELECT * FROM comfy_runs WHERE revision_id = ? ORDER BY created_at DESC, id DESC LIMIT 1",
                (head.id,),
            ).fetchone()
        workflow = parse_workflow(self._artifact_data(head))
        return ComfyStatus(
            str(self.root),
            self.application.name,
            self.application.document_kind,
            branch,
            branches,
            head,
            workflow.node_count,
            None if latest is None else self._run_from_row(latest),
        )

    def set_input(
        self,
        node_id: str,
        input_name: str,
        value: LiteralInput | NodeLink,
        *,
        message: str = "Set ComfyUI node input",
    ) -> ApplyResult[InputMutation]:
        with self._connect() as connection:
            head = self._get_revision(connection, "HEAD")
        workflow = parse_workflow(self._artifact_data(head))
        changed, mutation = apply_input(workflow, node_id, input_name, value)
        changed = parse_workflow(changed.to_bytes())
        if not mutation.changed:
            return ApplyResult(head, False, mutation)
        details = {
            "node_id": node_id,
            "class_type": workflow.document[node_id]["class_type"],
            "input_name": input_name,
            "before": mutation.before,
            "after": mutation.after,
        }
        revision = self._record_revision(
            changed.to_bytes(), "comfyui-set-input-v1", details, message, None, head.id
        )
        return ApplyResult(revision, True, mutation)

    def compare(self, before: str, after: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            left = self._revision_for_ref(connection, before)
            right = self._revision_for_ref(connection, after)
        return compare_workflows(
            parse_workflow(self._artifact_data(left)),
            parse_workflow(self._artifact_data(right)),
        )

    def run(
        self,
        client: ComfyApi,
        *,
        timeout_seconds: float = 600,
        poll_seconds: float = 1,
        required_version: str = "0.3.45",
        allow_version_mismatch: bool = False,
    ) -> ComfyRun:
        with self._connect() as connection:
            revision = self._get_revision(connection, "HEAD")
        workflow = parse_workflow(self._artifact_data(revision))
        run_id = str(uuid4())
        prompt_id = str(uuid4())
        client_id = str(uuid4())
        request = {"prompt": workflow.document, "prompt_id": prompt_id, "client_id": client_id}
        created_at = _now()
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO comfy_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL, NULL)",
                (
                    run_id,
                    revision.id,
                    revision.artifact_sha256,
                    prompt_id,
                    client_id,
                    client.origin,
                    created_at,
                    created_at,
                    RunState.PREPARED.value,
                    sha256(_json(request).encode()).hexdigest(),
                    _json(request),
                ),
            )
            connection.commit()
        try:
            system = client.system_stats()
        except Exception as error:
            self._update_run(
                run_id,
                RunState.REJECTED,
                error={"type": type(error).__name__, "message": str(error)},
            )
            return self.get_run(run_id)
        if system.version != required_version and not allow_version_mismatch:
            self._update_run(
                run_id,
                RunState.REJECTED,
                environment=system.raw,
                error={"message": f"expected ComfyUI {required_version}, got {system.version}"},
            )
            return self.get_run(run_id)
        try:
            submission = client.submit(request)
        except ComfyPromptRejected as error:
            self._update_run(
                run_id,
                RunState.REJECTED,
                environment=system.raw,
                error={"type": type(error).__name__, "details": error.details},
            )
            return self.get_run(run_id)
        except Exception as error:
            self._update_run(
                run_id,
                RunState.SUBMISSION_UNKNOWN,
                environment=system.raw,
                error={"type": type(error).__name__, "message": str(error)},
            )
            return self.get_run(run_id)
        self._update_run(
            run_id,
            RunState.SUBMITTED,
            environment=system.raw,
            submission=submission.raw,
        )
        return self._wait_for_run(run_id, client, timeout_seconds, poll_seconds)

    def resume(
        self,
        run_id: str,
        client: ComfyApi,
        *,
        timeout_seconds: float = 600,
        poll_seconds: float = 1,
    ) -> ComfyRun:
        run = self.get_run(run_id)
        if run.server_origin != client.origin:
            raise WorkspaceError("run server does not match the selected ComfyUI server")
        if run.state in {RunState.SUCCEEDED, RunState.REJECTED, RunState.FAILED}:
            return run
        return self._wait_for_run(run_id, client, timeout_seconds, poll_seconds)

    def get_run(self, run_id: str) -> ComfyRun:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM comfy_runs WHERE id = ?", (run_id,)).fetchone()
        if row is None:
            raise WorkspaceError(f"unknown ComfyUI run: {run_id}")
        return self._run_from_row(row)

    def _wait_for_run(self, run_id: str, client: ComfyApi, timeout: float, poll: float) -> ComfyRun:
        deadline = time.monotonic() + max(timeout, 0)
        run = self.get_run(run_id)
        while True:
            try:
                history = client.history(run.prompt_id)
            except Exception as error:
                self._update_run(run_id, run.state, error={"type": type(error).__name__, "message": str(error)})
                return self.get_run(run_id)
            if history is not None and history.completed:
                if not history.success:
                    status = history.raw.get("status", {})
                    self._update_run(
                        run_id,
                        RunState.FAILED,
                        history=history.raw,
                        error={
                            "type": "comfyui_execution_error",
                            "status_str": status.get("status_str") if isinstance(status, dict) else None,
                            "messages": status.get("messages", []) if isinstance(status, dict) else [],
                        },
                    )
                    return self.get_run(run_id)
                if not self._history_has_prompt_identity(run_id, history.raw):
                    self._update_run(
                        run_id,
                        RunState.FAILED,
                        history=history.raw,
                        error={"message": "ComfyUI history has the wrong prompt identity"},
                    )
                    return self.get_run(run_id)
                return self._retain_outputs(run_id, client, history)
            if time.monotonic() >= deadline:
                return self.get_run(run_id)
            time.sleep(max(poll, 0.01))

    def _history_has_prompt_identity(self, run_id: str, history: dict[str, Any]) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM comfy_runs WHERE id = ?",
                (run_id,),
            ).fetchone()
        if row is None:
            return False
        self._verify_request_row(row)
        prompt = history.get("prompt")
        if not isinstance(prompt, list) or len(prompt) < 3:
            return False
        if prompt[1] != row["prompt_id"] or not isinstance(prompt[2], dict):
            return False
        parse_workflow((_json(prompt[2]) + "\n").encode("utf-8"))
        return True

    def _retain_outputs(self, run_id: str, client: ComfyApi, history: ComfyHistory) -> ComfyRun:
        current = self.get_run(run_id)
        if current.state in {RunState.SUCCEEDED, RunState.REJECTED, RunState.FAILED}:
            return current
        outputs = history.raw.get("outputs", {})
        retained = 0
        try:
            if not isinstance(outputs, dict) or not outputs:
                raise WorkspaceError("ComfyUI history contains no image outputs")
            for node_id in sorted(outputs, key=str):
                node = outputs[node_id]
                if not isinstance(node, dict) or set(node) != {"images"}:
                    raise WorkspaceError("ComfyUI returned an unsupported output kind")
                images = node["images"]
                if not isinstance(images, list) or not images:
                    raise WorkspaceError("ComfyUI returned an invalid image output list")
                for ordinal, item in enumerate(images):
                    if not isinstance(item, dict) or not all(isinstance(item.get(k), str) for k in ("filename", "subfolder", "type")):
                        raise WorkspaceError("ComfyUI returned an invalid image locator")
                    locator = {key: item[key] for key in ("filename", "subfolder", "type")}
                    data, media_type = client.download(locator)
                    extension = _image_extension(data, media_type)
                    digest = sha256(data).hexdigest()
                    relative = f"run-artifacts/{digest}{extension}"
                    path = self.root / relative
                    if path.exists() and path.read_bytes() != data:
                        raise WorkspaceError("run artifact hash collision")
                    if not path.exists():
                        temporary = self.run_artifacts / f".{digest}.{uuid4().hex}.tmp"
                        with temporary.open("xb") as stream:
                            stream.write(data)
                            stream.flush()
                            os.fsync(stream.fileno())
                        os.replace(temporary, path)
                    with self._connect() as connection:
                        values = (
                            sha256(f"{run_id}:{node_id}:{ordinal}".encode()).hexdigest(),
                            run_id,
                            str(node_id),
                            ordinal,
                            digest,
                            len(data),
                            media_type,
                            relative,
                            _json(locator),
                        )
                        connection.execute(
                            "INSERT OR IGNORE INTO comfy_outputs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            values,
                        )
                        stored = connection.execute(
                            "SELECT * FROM comfy_outputs WHERE run_id = ? AND node_id = ? AND ordinal = ?",
                            (run_id, str(node_id), ordinal),
                        ).fetchone()
                        if stored is None or tuple(stored) != values:
                            raise WorkspaceError("retained ComfyUI output evidence conflicts")
                        connection.commit()
                    retained += 1
            if retained == 0:
                raise WorkspaceError("ComfyUI history contains no retained images")
        except Exception as error:
            self._update_run(
                run_id,
                RunState.OUTPUT_INCOMPLETE,
                history=history.raw,
                error={"type": type(error).__name__, "message": str(error)},
            )
            return self.get_run(run_id)
        self._update_run(run_id, RunState.SUCCEEDED, history=history.raw, error=None)
        return self.get_run(run_id)

    def _update_run(
        self,
        run_id: str,
        state: RunState,
        *,
        submission: dict[str, Any] | None = None,
        history: dict[str, Any] | None = None,
        environment: dict[str, Any] | None = None,
        error: dict[str, Any] | None = None,
    ) -> None:
        values = {
            "state": state.value,
            "updated_at": _now(),
            "submission_json": None if submission is None else _json(submission),
            "history_json": None if history is None else _json(history),
            "environment_json": None if environment is None else _json(environment),
            "error_json": None if error is None else _json(error),
        }
        assignments = ["state = ?", "updated_at = ?"]
        parameters: list[Any] = [values["state"], values["updated_at"]]
        for column in ("submission_json", "history_json", "environment_json", "error_json"):
            if values[column] is not None or (column == "error_json" and state is RunState.SUCCEEDED):
                assignments.append(f"{column} = ?")
                parameters.append(values[column])
        parameters.append(run_id)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT state FROM comfy_runs WHERE id = ?", (run_id,)
            ).fetchone()
            if row is None:
                raise WorkspaceError(f"unknown ComfyUI run: {run_id}")
            current = RunState(row["state"])
            terminal = {RunState.SUCCEEDED, RunState.REJECTED, RunState.FAILED}
            if current in terminal:
                connection.rollback()
                return
            allowed = {
                RunState.PREPARED: {
                    RunState.PREPARED,
                    RunState.SUBMITTED,
                    RunState.SUBMISSION_UNKNOWN,
                    RunState.REJECTED,
                },
                RunState.SUBMITTED: {
                    RunState.SUBMITTED,
                    RunState.SUCCEEDED,
                    RunState.FAILED,
                    RunState.OUTPUT_INCOMPLETE,
                },
                RunState.SUBMISSION_UNKNOWN: {
                    RunState.SUBMISSION_UNKNOWN,
                    RunState.SUCCEEDED,
                    RunState.FAILED,
                    RunState.OUTPUT_INCOMPLETE,
                },
                RunState.OUTPUT_INCOMPLETE: {
                    RunState.OUTPUT_INCOMPLETE,
                    RunState.SUCCEEDED,
                    RunState.FAILED,
                },
            }
            if state not in allowed[current]:
                connection.rollback()
                raise WorkspaceError(
                    f"invalid ComfyUI run transition: {current.value} -> {state.value}"
                )
            connection.execute(
                f"UPDATE comfy_runs SET {', '.join(assignments)} WHERE id = ?",
                parameters,
            )
            connection.commit()

    def _run_from_row(self, row: sqlite3.Row) -> ComfyRun:
        request = self._verify_request_row(row)
        with self._connect() as connection:
            output_rows = connection.execute(
                "SELECT * FROM comfy_outputs WHERE run_id = ? ORDER BY node_id, ordinal",
                (row["id"],),
            ).fetchall()
        outputs = tuple(
            RunOutput(
                item["node_id"],
                item["ordinal"],
                item["artifact_sha256"],
                item["bytes"],
                item["media_type"],
                str(self.root / item["relative_path"]),
            )
            for item in output_rows
        )
        for output in outputs:
            path = Path(output.path)
            resolved = path.resolve()
            if not resolved.is_relative_to(self.run_artifacts.resolve()):
                raise WorkspaceError("retained ComfyUI output path escapes run-artifacts")
            if not path.is_file():
                raise WorkspaceError(f"retained ComfyUI output is missing: {path}")
            data = path.read_bytes()
            if len(data) != output.bytes or sha256(data).hexdigest() != output.sha256:
                raise WorkspaceError(f"retained ComfyUI output failed hash verification: {path}")
            extension = _image_extension(data, output.media_type)
            if path.suffix.lower() != extension or path.stem != output.sha256:
                raise WorkspaceError("retained ComfyUI output path provenance is invalid")
        accepted_prompt_sha256 = None
        if row["history_json"] is not None:
            history = json.loads(row["history_json"])
            prompt = history.get("prompt") if isinstance(history, dict) else None
            if isinstance(prompt, list) and len(prompt) >= 3 and isinstance(prompt[2], dict):
                accepted_prompt_sha256 = sha256(_json(prompt[2]).encode("utf-8")).hexdigest()
        environment = None
        comfyui_version = None
        if row["environment_json"] is not None:
            environment = json.loads(row["environment_json"])
            if not isinstance(environment, dict):
                raise WorkspaceError("stored ComfyUI environment is invalid")
            system = environment.get("system")
            version = system.get("comfyui_version") if isinstance(system, dict) else None
            if not isinstance(version, str):
                raise WorkspaceError("stored ComfyUI environment has no version")
            comfyui_version = version
        return ComfyRun(
            row["id"],
            row["revision_id"],
            row["artifact_sha256"],
            row["prompt_id"],
            row["server_origin"],
            row["created_at"],
            row["updated_at"],
            RunState(row["state"]),
            comfyui_version,
            environment,
            sha256(_json(request["prompt"]).encode("utf-8")).hexdigest(),
            accepted_prompt_sha256,
            outputs,
            None if row["error_json"] is None else json.loads(row["error_json"]),
        )

    def _verify_request_row(self, row: sqlite3.Row) -> dict[str, Any]:
        request_text = row["request_json"]
        if sha256(request_text.encode("utf-8")).hexdigest() != row["request_sha256"]:
            raise WorkspaceError("stored ComfyUI request failed hash verification")
        try:
            request = json.loads(request_text)
        except json.JSONDecodeError as error:
            raise WorkspaceError("stored ComfyUI request is invalid JSON") from error
        if not isinstance(request, dict) or request.get("prompt_id") != row["prompt_id"]:
            raise WorkspaceError("stored ComfyUI request identity is inconsistent")
        with self._connect() as connection:
            revision_row = connection.execute(
                "SELECT * FROM revisions WHERE id = ?", (row["revision_id"],)
            ).fetchone()
        if revision_row is None:
            raise WorkspaceError("ComfyUI run revision is missing")
        revision = self._revision(revision_row)
        if revision.artifact_sha256 != row["artifact_sha256"]:
            raise WorkspaceError("ComfyUI run artifact does not match its revision")
        workflow = parse_workflow(self._artifact_data(revision))
        if _json(request.get("prompt")) != _json(workflow.document):
            raise WorkspaceError("ComfyUI run request does not match its revision artifact")
        return request


def _image_extension(data: bytes, media_type: str) -> str:
    signatures = (
        (b"\x89PNG\r\n\x1a\n", "image/png", ".png"),
        (b"\xff\xd8\xff", "image/jpeg", ".jpg"),
        (b"RIFF", "image/webp", ".webp"),
    )
    for signature, expected, extension in signatures:
        if data.startswith(signature) and media_type == expected:
            if expected != "image/webp" or data[8:12] == b"WEBP":
                return extension
    raise WorkspaceError("downloaded output is not a supported image")
