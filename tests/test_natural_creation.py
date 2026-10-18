from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
import json

import pytest

from xenodream_xxp.creation import (
    CreationError,
    CreationRecipe,
    CreationSeed,
    ModelCreation,
    apply_creation,
    preview_creation,
)
from xenodream_xxp.cli import main
from xenodream_xxp.openai_planner import decode_creation_response
from xenodream_xxp.openai_planner import request_creation
from xenodream_xxp.workspace import ProjectWorkspace
from xenosculpt_openai.auth import AccessLease, AuthError
from xenosculpt_openai.storage import Secret


def _creation(recipe: str, *, seed: CreationSeed = CreationSeed.CUBE) -> ModelCreation:
    return ModelCreation(
        recipe=CreationRecipe(
            seed=seed,
            recipe=recipe,
            summary="A verified composition.",
            unsupported=(),
        ),
        model="test-model",
        response_id="resp_test",
    )


def test_preview_evaluates_a_natural_creation_without_writes(tmp_path) -> None:
    workspace = tmp_path / "creation.xsp"
    creation = _creation(
        "add Sphere at 55 0 0; "
        "apply Sphere profile cushion-core to object Sphere3"
    )

    preview = preview_creation("make a cushioned two-part form", creation)

    assert not workspace.exists()
    assert preview.output_sha256 != preview.seed_sha256
    assert [node.name for node in preview.scene.nodes] == [
        "Group1",
        "Cube2",
        "Sphere3",
    ]
    assert len(preview.operations) == 2


def test_apply_creation_publishes_verified_workspace_and_export(tmp_path) -> None:
    workspace = tmp_path / "creation.xsp"
    export = tmp_path / "creation.xxp"
    prompt = "make a cushioned cube and sphere form"
    creation = _creation(
        "add Sphere at 55 0 0; "
        "apply Sphere profile cushion-core to object Sphere3"
    )

    result = apply_creation(
        workspace,
        prompt=prompt,
        creation=creation,
        message="Create from natural language",
        export=export,
    )

    opened = ProjectWorkspace.open(workspace)
    assert opened.status().head.artifact_sha256 == result.preview.output_sha256
    assert sha256(export.read_bytes()).hexdigest() == result.preview.output_sha256
    history = opened.history()
    assert history[-1].prompt == prompt
    assert history[-1].details["creation"]["response_id"] == "resp_test"
    assert history[0].prompt == prompt
    assert history[0].details["planning"]["planner"] == {
        "name": "openai-responses",
        "version": "test-model",
    }


def test_creation_rejects_unsupported_intent_before_writing(tmp_path) -> None:
    creation = ModelCreation(
        CreationRecipe(
            CreationSeed.CUBE,
            "set object Cube2 scale to 60 60 60",
            "A cube with text.",
            ("embossed text is unsupported",),
        ),
        "test-model",
        "resp_unsupported",
    )

    with pytest.raises(CreationError, match="embossed text"):
        apply_creation(
            tmp_path / "must-not-exist.xsp",
            prompt="make a cube with embossed text",
            creation=creation,
            message="must fail",
        )

    assert not (tmp_path / "must-not-exist.xsp").exists()


def test_decode_creation_response_rejects_duplicate_recipe_keys() -> None:
    body = {
        "id": "resp_1",
        "model": "test-model",
        "output": [
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": (
                            '{"seed":"Cube","recipe":"",'
                            '"recipe":"set object Cube2 scale to 60 60 60",'
                            '"summary":"cube","unsupported":[]}'
                        ),
                    }
                ],
            }
        ],
    }

    with pytest.raises(CreationError, match="duplicate JSON key"):
        decode_creation_response(json.dumps(body).encode("utf-8"), "test-model")


def test_create_cli_dry_run_and_apply(monkeypatch, tmp_path, capsys) -> None:
    creation = _creation("set object Cube2 scale to 60 55 50")
    monkeypatch.setattr(
        "xenodream_xxp.cli.request_creation",
        lambda prompt, **options: creation,
    )
    workspace = tmp_path / "prompted.xsp"
    export = tmp_path / "prompted.xxp"
    arguments = [
        "create",
        str(workspace),
        "--prompt",
        "make a broad cube",
        "--model",
        "test-model",
        "--auth",
        "api-key",
        "--export",
        str(export),
    ]

    assert main([*arguments, "--dry-run"]) == 0
    dry_run = json.loads(capsys.readouterr().out)
    assert dry_run["created"] is False
    assert dry_run["operations"][0]["type"] == "object-mutation"
    assert not workspace.exists()
    assert not export.exists()

    assert main(arguments) == 0
    applied = json.loads(capsys.readouterr().out)
    assert applied["created"] is True
    assert applied["translated_recipe"] == "set object Cube2 scale to 60 55 50"
    assert workspace.is_dir()
    assert export.is_file()


def test_create_cli_defaults_to_chatgpt_without_api_key_fallback(
    monkeypatch, tmp_path, capsys
) -> None:
    creation = ModelCreation(
        _creation("set object Cube2 scale to 60 55 50").recipe,
        "test-model",
        "resp_chatgpt",
        "chatgpt-plan",
    )

    class FakeAuth:
        def acquire(self, account=None):
            assert account is None
            return AccessLease(
                Secret("plan-token"),
                "acct_test",
                datetime(2026, 10, 18, tzinfo=UTC),
            )

    monkeypatch.setattr("xenodream_xxp.cli.ChatGPTPlanAuth", FakeAuth)
    monkeypatch.setattr(
        "xenodream_xxp.cli.request_creation_chatgpt",
        lambda prompt, **options: creation,
    )
    workspace = tmp_path / "chatgpt.xsp"
    assert main(
        [
            "create",
            str(workspace),
            "--prompt",
            "make a broad cube",
            "--model",
            "test-model",
            "--dry-run",
        ]
    ) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["usage_source"] == "chatgpt-plan"
    assert not workspace.exists()


def test_create_auth_failure_never_creates_workspace(monkeypatch, tmp_path, capsys) -> None:
    class MissingAuth:
        def acquire(self, account=None):
            raise AuthError("run 'xenosculpt auth login'")

    monkeypatch.setattr("xenodream_xxp.cli.ChatGPTPlanAuth", MissingAuth)
    workspace = tmp_path / "missing-auth.xsp"
    assert main(
        [
            "create",
            str(workspace),
            "--prompt",
            "make a cube",
            "--model",
            "test-model",
        ]
    ) == 2
    assert "auth login" in capsys.readouterr().err
    assert not workspace.exists()


@pytest.mark.parametrize("seed", tuple(CreationSeed))
def test_every_creation_seed_compiles_to_a_described_scene(seed) -> None:
    preview = preview_creation("create the supported seed", _creation("", seed=seed))

    assert preview.seed_sha256 == preview.output_sha256
    assert len(preview.scene.nodes) == 2
    assert preview.scene.diagnostics == ()


def test_invalid_translated_recipe_never_creates_workspace(tmp_path) -> None:
    workspace = tmp_path / "invalid.xsp"
    with pytest.raises(CreationError, match="not executable"):
        apply_creation(
            workspace,
            prompt="invent unsupported geometry",
            creation=_creation("make geometry somehow"),
            message="invalid",
        )
    assert not workspace.exists()


def test_openai_request_uses_strict_structured_output(monkeypatch) -> None:
    response_body = json.dumps(
        {
            "id": "resp_payload",
            "model": "test-model-2026",
            "output": [
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": json.dumps(
                                {
                                    "seed": "Torus",
                                    "recipe": "set object Torus2 scale to 60 60 30",
                                    "summary": "A flattened torus.",
                                    "unsupported": [],
                                }
                            ),
                        }
                    ],
                }
            ],
        }
    ).encode()
    captured = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self, limit):
            captured["limit"] = limit
            return response_body

    def fake_urlopen(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return Response()

    monkeypatch.setattr("xenodream_xxp.openai_planner.urlopen", fake_urlopen)
    result = request_creation(
        "make a flattened torus",
        model="test-model",
        api_key="secret-test-key",
    )

    payload = json.loads(captured["request"].data)
    assert payload["text"]["format"]["type"] == "json_schema"
    assert payload["text"]["format"]["strict"] is True
    assert payload["store"] is False
    assert result.model == "test-model-2026"
    assert result.recipe.seed is CreationSeed.TORUS
