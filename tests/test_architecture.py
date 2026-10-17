from __future__ import annotations

from hashlib import sha256
import sqlite3
import subprocess
import sys

import pytest

from xenodream_xxp import ProjectWorkspace, Revision, compile_cube, compile_cylinder
from xenodream_xxp.adapter import XenoDreamArtifactAdapter
from xenodream_xxp.workspace import ApplyResult, ArtifactInfo, WorkspaceError
from xenosculpt.core.model import (
    ApplicationIdentity,
    ApplyResult as CoreApplyResult,
    ArtifactInfo as CoreArtifactInfo,
    Revision as CoreRevision,
)
from xenosculpt.core.workspace import RevisionWorkspace


def test_core_import_does_not_load_xenodream_package() -> None:
    script = (
        "import sys; import xenosculpt.core.workspace; "
        "assert not any(name == 'xenodream_xxp' or "
        "name.startswith('xenodream_xxp.') for name in sys.modules)"
    )

    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr


def test_xenodream_workspace_specializes_revision_workspace() -> None:
    assert issubclass(ProjectWorkspace, RevisionWorkspace)
    assert isinstance(ProjectWorkspace.adapter, XenoDreamArtifactAdapter)


def test_compatibility_types_have_one_core_definition() -> None:
    assert Revision is CoreRevision
    assert ArtifactInfo is CoreArtifactInfo
    assert ApplyResult is CoreApplyResult


def test_xenodream_adapter_owns_xdx_admission() -> None:
    descriptor = XenoDreamArtifactAdapter().inspect(compile_cube())

    assert descriptor.xdx_version == "1.220"


def test_core_initializes_history_without_xenodream_schema(tmp_path) -> None:
    identity = ApplicationIdentity("test-app", "test/document/v1", ".json")
    workspace = RevisionWorkspace(tmp_path / "generic.xsp", identity)
    workspace.root.mkdir()
    data = b'{"value":1}'
    details = {"source_sha256": sha256(data).hexdigest()}

    with sqlite3.connect(workspace.database) as connection:
        revision = workspace.initialize_history(
            connection,
            source_data=data,
            created_at="2026-10-17T00:00:00Z",
            operation="init",
            details=details,
            message="Import document",
            prompt=None,
            metadata={"schema_version": "1"},
        )
        connection.commit()

    workspace.create_branch("alternate")
    exported = workspace.export(tmp_path / "document.json")
    assert exported.revision_id == revision.id
    assert (workspace.artifacts / f"{revision.artifact_sha256}.json").is_file()


def test_xenodream_schema_and_revision_identity_remain_compatible(tmp_path) -> None:
    source = tmp_path / "cylinder.xxp"
    source.write_bytes(compile_cylinder())
    workspace = ProjectWorkspace.create(tmp_path / "cylinder.xsp", source)

    assert workspace.status().head.id == (
        "5e1471810921ed8f6698951a2223cfbc05a5b3858e6970c20f5d4dfdd5086ff4"
    )
    with sqlite3.connect(workspace.database) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        metadata = dict(connection.execute("SELECT key, value FROM metadata"))

    assert tables == {
        "branches",
        "fabrication_assessments",
        "metadata",
        "revisions",
        "state",
        "validations",
    }
    assert metadata["schema_version"] == "3"
    assert metadata["application_id"] == "xenodream-x"
    assert metadata["document_kind"] == "xenodream/xdx-project/v1"
    assert metadata["artifact_suffix"] == ".xxp"


def test_open_binds_legacy_workspace_to_xenodream(tmp_path) -> None:
    source = tmp_path / "cube.xxp"
    source.write_bytes(compile_cube())
    workspace = ProjectWorkspace.create(tmp_path / "legacy.xsp", source)
    with sqlite3.connect(workspace.database) as connection:
        connection.execute(
            "DELETE FROM metadata WHERE key IN "
            "('application_id', 'document_kind', 'artifact_suffix')"
        )
        connection.commit()

    ProjectWorkspace.open(workspace.root)

    with sqlite3.connect(workspace.database) as connection:
        metadata = dict(connection.execute("SELECT key, value FROM metadata"))
    assert metadata["application_id"] == "xenodream-x"
    assert metadata["document_kind"] == "xenodream/xdx-project/v1"
    assert metadata["artifact_suffix"] == ".xxp"


def test_open_rejects_mismatched_application_identity(tmp_path) -> None:
    source = tmp_path / "cube.xxp"
    source.write_bytes(compile_cube())
    workspace = ProjectWorkspace.create(tmp_path / "wrong-app.xsp", source)
    with sqlite3.connect(workspace.database) as connection:
        connection.execute(
            "UPDATE metadata SET value = 'comfyui' WHERE key = 'application_id'"
        )
        connection.commit()

    with pytest.raises(WorkspaceError, match="application identity"):
        ProjectWorkspace.open(workspace.root)


def test_identity_mismatch_does_not_migrate_foreign_workspace(tmp_path) -> None:
    source = tmp_path / "cube.xxp"
    source.write_bytes(compile_cube())
    workspace = ProjectWorkspace.create(tmp_path / "foreign.xsp", source)
    with sqlite3.connect(workspace.database) as connection:
        connection.execute("DROP TABLE fabrication_assessments")
        connection.execute("DROP TABLE validations")
        connection.execute(
            "UPDATE metadata SET value = '1' WHERE key = 'schema_version'"
        )
        connection.execute(
            "UPDATE metadata SET value = 'comfyui' WHERE key = 'application_id'"
        )
        connection.commit()

    with pytest.raises(WorkspaceError, match="application identity"):
        ProjectWorkspace.open(workspace.root)

    with sqlite3.connect(workspace.database) as connection:
        schema_version = connection.execute(
            "SELECT value FROM metadata WHERE key = 'schema_version'"
        ).fetchone()[0]
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    assert schema_version == "1"
    assert "validations" not in tables
    assert "fabrication_assessments" not in tables
