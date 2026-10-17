from __future__ import annotations

from pathlib import Path

import sqlite3

from xenosculpt.comfyui.workspace import ComfyProject
from xenosculpt.comfyui.workflow import LiteralInput


FIXTURE = Path(__file__).parent / "fixtures" / "comfyui" / "empty-image-api.json"


def test_workspace_uses_shared_history_and_comfy_identity(tmp_path) -> None:
    project = ComfyProject.create(tmp_path / "image.csp", FIXTURE)
    result = project.set_input("1", "width", LiteralInput(96), message="wider")

    assert result.created is True
    assert project.status().head.id == result.revision.id
    assert project.compare("HEAD~1", "HEAD") == [
        {"after": 96, "before": 64, "kind": "value_changed", "path": "/1/inputs/width"}
    ]
    with sqlite3.connect(project.database) as connection:
        metadata = dict(connection.execute("SELECT key, value FROM metadata"))
    assert metadata["application_id"] == "comfyui"
    assert metadata["document_kind"] == "comfyui/api-workflow/v1"


def test_noop_input_edit_does_not_create_revision(tmp_path) -> None:
    project = ComfyProject.create(tmp_path / "image.csp", FIXTURE)
    before = project.status().head.id

    result = project.set_input("1", "width", LiteralInput(64), message="same")

    assert result.created is False
    assert project.status().head.id == before
