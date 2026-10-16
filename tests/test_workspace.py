from __future__ import annotations

from decimal import Decimal as D
from pathlib import Path

import pytest

from xenodream_xxp.generator import CubeSpec, Vector3, compile_cube
from xenodream_xxp.mutation import CenteredRowMutation, ObjectMutation
from xenodream_xxp.workspace import (
    FabricationConstraints,
    ProjectWorkspace,
    WorkspaceError,
)


def _source(tmp_path: Path) -> Path:
    path = tmp_path / "source.xxp"
    path.write_bytes(compile_cube())
    return path


def test_create_records_constraints_and_preserves_source(tmp_path) -> None:
    source = _source(tmp_path)
    original = source.read_bytes()
    workspace = ProjectWorkspace.create(
        tmp_path / "sculpture.xsp",
        source,
        FabricationConstraints(
            process="FDM",
            build_volume_mm=Vector3(D("220"), D("220"), D("250")),
            min_feature_mm=D("1.2"),
        ),
    )

    status = workspace.status()
    assert status.current_branch == "main"
    assert status.branches == {"main": status.head.id}
    assert status.xdx_version == "1.220"
    assert status.constraints.process == "FDM"
    assert status.constraints.min_feature_mm == D("1.2")
    assert Path(status.artifact_path).read_bytes() == original
    assert source.read_bytes() == original
    assert ProjectWorkspace.open(workspace.root).status() == status


def test_apply_creates_revision_and_noop_is_idempotent(tmp_path) -> None:
    workspace = ProjectWorkspace.create(tmp_path / "project.xsp", _source(tmp_path))
    initial = workspace.status().head

    applied = workspace.apply(
        ObjectMutation(
            "Cube2", position=Vector3(D("25"), D("0"), D("0"))
        ),
        message="move right",
        prompt="move the cube right",
    )
    assert applied.created is True
    assert applied.revision.parent_id == initial.id
    assert applied.revision.prompt == "move the cube right"
    assert workspace.status().head.id == applied.revision.id
    assert len(workspace.history()) == 2

    repeated = workspace.apply(
        ObjectMutation(
            "Cube2", position=Vector3(D("25"), D("0"), D("0"))
        ),
        message="repeat",
    )
    assert repeated.created is False
    assert repeated.revision.id == applied.revision.id
    assert len(workspace.history()) == 2


def test_branch_checkout_compare_and_export(tmp_path) -> None:
    workspace = ProjectWorkspace.create(tmp_path / "project.xsp", _source(tmp_path))
    workspace.create_branch("wide", checkout=True)
    wide = workspace.apply(
        ObjectMutation("Cube2", scale=Vector3(D("80"), D("50"), D("50"))),
        message="widen",
    ).revision

    workspace.checkout("main")
    assert workspace.status().current_branch == "main"
    assert workspace.status().head.parent_id is None
    differences = workspace.compare("main", "wide")
    assert [(item["section"], item.get("token_index")) for item in differences] == [
        ("Holon\\1", 0)
    ]

    destination = tmp_path / "restored.xxp"
    exported = workspace.export(destination)
    assert destination.read_bytes() == compile_cube()
    assert exported.revision_id == workspace.status().head.id
    with pytest.raises(WorkspaceError, match="overwrite"):
        workspace.export(destination)
    assert workspace.checkout(wide.id[:12]).id == wide.id
    assert workspace.status().current_branch is None


def test_distinct_prompts_remain_distinct_revisions_on_parallel_branches(tmp_path) -> None:
    workspace = ProjectWorkspace.create(tmp_path / "project.xsp", _source(tmp_path))
    workspace.create_branch("first", checkout=True)
    first = workspace.apply(
        ObjectMutation("Cube2", face_warp=D("0.25")),
        message="first interpretation",
        prompt="make it softer",
    ).revision
    workspace.checkout("main")
    workspace.create_branch("second", checkout=True)
    second = workspace.apply(
        ObjectMutation("Cube2", face_warp=D("0.25")),
        message="second interpretation",
        prompt="round the faces",
    ).revision

    assert first.id != second.id
    assert first.artifact_sha256 == second.artifact_sha256
    assert first.prompt == "make it softer"
    assert second.prompt == "round the faces"


def test_import_manual_edit_creates_revision_without_changing_input(tmp_path) -> None:
    workspace = ProjectWorkspace.create(tmp_path / "project.xsp", _source(tmp_path))
    manual = tmp_path / "manual.xxp"
    manual.write_bytes(
        compile_cube(CubeSpec(face_warp=D("0.25")))
    )
    before = manual.read_bytes()

    result = workspace.import_artifact(manual, message="manual XenoDream edit")

    assert result.created is True
    assert result.revision.operation == "manual-import"
    assert manual.read_bytes() == before
    assert len(workspace.history()) == 2


def test_row_operation_is_recorded_as_typed_revision(tmp_path) -> None:
    workspace = ProjectWorkspace.create(tmp_path / "project.xsp", _source(tmp_path))
    result = workspace.apply(
        CenteredRowMutation(D("20"), Vector3(D("10"), D("5"), D("0"))),
        message="place row",
    )

    assert result.revision.operation == "centered-row"
    assert result.revision.details["spacing"] == "20"
    assert result.revision.details["center"] == ["10", "5", "0"]


def test_rejects_invalid_workspace_and_constraints(tmp_path) -> None:
    with pytest.raises(WorkspaceError, match="not a project workspace"):
        ProjectWorkspace.open(tmp_path / "missing")
    with pytest.raises(WorkspaceError, match="positive"):
        FabricationConstraints(min_feature_mm=D("0"))
