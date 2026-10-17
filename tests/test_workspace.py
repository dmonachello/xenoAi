from __future__ import annotations

from decimal import Decimal as D
from dataclasses import asdict
from pathlib import Path
import json
import sqlite3
import struct

import pytest

import xenodream_xxp.mutation as mutation_module
from xenodream_xxp.composition import AddCube
from xenodream_xxp.generator import (
    CubeSpec,
    TemplateMismatchError,
    Vector3,
    compile_cube,
    compile_cylinder,
    compile_sphere,
    compile_three_cubes,
)
from xenodream_xxp.fabrication import (
    CheckCode,
    CheckStatus,
    FabricationVerdict,
)
from xenodream_xxp.mutation import (
    CenteredRowMutation,
    CylinderMetamorphMutation,
    MutationError,
    ObjectMutation,
    SeededVariation,
    SphereMetamorphMutation,
)
from xenodream_xxp.workspace import (
    FabricationConstraints,
    ProjectWorkspace,
    WorkspaceError,
)
from xenodream_xxp.mesh import inspect_binary_stl
from xenodream_xxp.native_export import MeshExportSettings
from xenodream_xxp.planning import (
    HeadBinding,
    MutationPlan,
    PlannerIdentity,
    PlanningError,
    plan_prompt,
    plan_provenance_to_dict,
)


def _source(tmp_path: Path) -> Path:
    path = tmp_path / "source.xxp"
    path.write_bytes(compile_cube())
    return path


def _closed_tetrahedron(path: Path) -> None:
    origin = (0.0, 0.0, 0.0)
    x = (1.0, 0.0, 0.0)
    y = (0.0, 1.0, 0.0)
    z = (0.0, 0.0, 1.0)

    def triangle(a, b, c):
        return struct.pack("<12fH", 0.0, 0.0, 1.0, *a, *b, *c, 0)

    triangles = (
        triangle(origin, y, x),
        triangle(origin, x, z),
        triangle(origin, z, y),
        triangle(x, y, z),
    )
    path.write_bytes(
        b"validation".ljust(80, b"\0")
        + struct.pack("<I", len(triangles))
        + b"".join(triangles)
    )


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


def test_describe_binds_scene_to_selected_revision_without_moving_head(tmp_path) -> None:
    workspace = ProjectWorkspace.create(tmp_path / "project.xsp", _source(tmp_path))
    initial = workspace.status().head
    changed = workspace.apply(
        ObjectMutation("Cube2", position=Vector3(D("25"), D("0"), D("0"))),
        message="move cube",
    ).revision

    scene = workspace.describe(initial.id)

    assert scene.binding.revision_id == initial.id
    assert scene.binding.artifact_sha256 == initial.artifact_sha256
    assert scene.nodes[1].transform is not None
    assert scene.nodes[1].transform.position.x == D("0.00000")
    assert workspace.status().head.id == changed.id


def test_describe_rejects_a_corrupted_content_addressed_artifact(tmp_path) -> None:
    workspace = ProjectWorkspace.create(tmp_path / "project.xsp", _source(tmp_path))
    Path(workspace.status().artifact_path).write_bytes(b"corrupted")

    with pytest.raises(WorkspaceError, match="artifact failed hash verification"):
        workspace.describe()


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


def test_add_cube_creates_a_revision_and_the_new_cube_is_editable(tmp_path) -> None:
    workspace = ProjectWorkspace.create(tmp_path / "project.xsp", _source(tmp_path))

    added = workspace.apply(
        AddCube(position=Vector3(D("75"), D("0"), D("0"))),
        message="add cube",
    )

    assert added.created is True
    assert added.revision.operation == "add-cube-v1"
    assert added.revision.details["position"] == ["75", "0", "0"]
    assert added.mutation is not None
    assert added.mutation.added is not None
    assert added.mutation.added.name == "Cube3"
    moved = workspace.apply(
        ObjectMutation("Cube3", position=Vector3(D("100"), D("0"), D("0"))),
        message="move added cube",
    )
    assert moved.created is True
    assert workspace.describe().nodes[-1].transform is not None
    assert workspace.describe().nodes[-1].transform.position.x == D("100.00000")


def test_rejected_add_cube_does_not_change_head_database_or_artifacts(tmp_path) -> None:
    source = tmp_path / "three-cubes.xxp"
    source.write_bytes(compile_three_cubes())
    workspace = ProjectWorkspace.create(tmp_path / "project.xsp", source)
    before_head = workspace.status().head
    before_artifacts = {path.name for path in workspace.artifacts.iterdir()}
    with sqlite3.connect(workspace.database) as connection:
        before_revisions = connection.execute(
            "SELECT COUNT(*) FROM revisions"
        ).fetchone()[0]

    with pytest.raises(MutationError, match="one or two"):
        workspace.apply(
            AddCube(position=Vector3(D("100"), D("0"), D("0"))),
            message="unsupported fourth cube",
        )

    assert workspace.status().head == before_head
    assert {path.name for path in workspace.artifacts.iterdir()} == before_artifacts
    with sqlite3.connect(workspace.database) as connection:
        after_revisions = connection.execute(
            "SELECT COUNT(*) FROM revisions"
        ).fetchone()[0]
    assert after_revisions == before_revisions


def test_add_cube_template_mismatch_is_atomic_mutation_error(
    tmp_path, monkeypatch
) -> None:
    workspace = ProjectWorkspace.create(tmp_path / "project.xsp", _source(tmp_path))
    before_head = workspace.status().head
    before_history = workspace.history()
    before_artifacts = {path.name for path in workspace.artifacts.iterdir()}

    def reject_template(data, operation):
        raise TemplateMismatchError("template resource digest mismatch")

    monkeypatch.setattr(mutation_module, "append_cube", reject_template)

    with pytest.raises(MutationError, match="template resource digest mismatch"):
        workspace.apply(
            AddCube(position=Vector3(D("75"), D("0"), D("0"))),
            message="cannot use mismatched template",
        )

    assert workspace.status().head == before_head
    assert workspace.history() == before_history
    assert {path.name for path in workspace.artifacts.iterdir()} == before_artifacts


def test_apply_plan_binds_head_and_records_planner_provenance(tmp_path) -> None:
    planned_workspace = ProjectWorkspace.create(
        tmp_path / "planned.xsp", _source(tmp_path)
    )
    explicit_source = tmp_path / "explicit-source.xxp"
    explicit_source.write_bytes(compile_cube())
    explicit_workspace = ProjectWorkspace.create(
        tmp_path / "explicit.xsp", explicit_source
    )
    initial = planned_workspace.status().head
    prompt = "set object Cube2 position to 25 0 0"
    plan = plan_prompt(prompt, base=HeadBinding.from_revision(initial))

    planned = planned_workspace.apply_plan(plan, message="planned move")
    explicit = explicit_workspace.apply(
        ObjectMutation("Cube2", position=Vector3(D("25"), D("0"), D("0"))),
        message="explicit move",
    )

    assert planned.created is True
    assert planned.revision.artifact_sha256 == explicit.revision.artifact_sha256
    assert planned.revision.prompt == prompt
    assert planned.revision.details["planning"] == plan_provenance_to_dict(plan)

    repeated_plan = plan_prompt(
        prompt,
        base=HeadBinding.from_revision(planned_workspace.status().head),
    )
    repeated = planned_workspace.apply_plan(repeated_plan, message="planned repeat")
    assert repeated.created is False
    assert len(planned_workspace.history()) == 2


def test_apply_plan_rejects_forged_controlled_english_provenance(tmp_path) -> None:
    workspace = ProjectWorkspace.create(tmp_path / "forged.xsp", _source(tmp_path))
    initial = workspace.status().head
    forged = MutationPlan(
        prompt="make it prettier",
        rule="set-position-v1",
        base=HeadBinding.from_revision(initial),
        operation=ObjectMutation(
            "Cube2", position=Vector3(D("25"), D("0"), D("0"))
        ),
        planner=PlannerIdentity("xenosculpt-controlled-english", "1"),
    )

    with pytest.raises(PlanningError):
        workspace.apply_plan(forged, message="forged")

    assert workspace.status().head.id == initial.id


def test_apply_plan_records_a_distinct_planner_identity(tmp_path) -> None:
    workspace = ProjectWorkspace.create(tmp_path / "other-planner.xsp", _source(tmp_path))
    initial = workspace.status().head
    plan = MutationPlan(
        prompt="structured input",
        rule="test-position-v2",
        base=HeadBinding.from_revision(initial),
        operation=ObjectMutation(
            "Cube2", position=Vector3(D("25"), D("0"), D("0"))
        ),
        planner=PlannerIdentity("test-planner", "2"),
    )

    applied = workspace.apply_plan(plan, message="other planner")

    assert applied.revision.details["planning"] == plan_provenance_to_dict(plan)


def test_apply_plan_rejects_stale_head_without_moving_current_head(tmp_path) -> None:
    workspace = ProjectWorkspace.create(tmp_path / "stale.xsp", _source(tmp_path))
    initial = workspace.status().head
    stale_plan = plan_prompt(
        "set object Cube2 position to 25 0 0",
        base=HeadBinding.from_revision(initial),
    )
    intervening = workspace.apply(
        ObjectMutation("Cube2", face_warp=D("0.25")),
        message="intervening change",
    )

    with pytest.raises(WorkspaceError, match="different HEAD"):
        workspace.apply_plan(stale_plan, message="stale planned move")

    assert workspace.status().head.id == intervening.revision.id
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


def test_seeded_variation_records_reproducibility_details(tmp_path) -> None:
    workspace = ProjectWorkspace.create(tmp_path / "project.xsp", _source(tmp_path))

    result = workspace.apply(
        SeededVariation(seed=17, strength=D("0.5")),
        message="seeded variation",
    )

    assert result.created is True
    assert result.revision.operation == "seeded-variation-v1"
    assert result.revision.details == {
        "type": "seeded-variation-v1",
        "seed": 17,
        "strength": "0.5",
    }


def test_sphere_metamorph_profile_records_evidence_and_validation_gate(
    tmp_path,
) -> None:
    source = tmp_path / "sphere.xxp"
    source.write_bytes(compile_sphere())
    workspace = ProjectWorkspace.create(tmp_path / "sphere.xsp", source)

    result = workspace.apply(
        SphereMetamorphMutation("Sphere2", "cushion-core"),
        message="measured cushion form",
    )

    assert result.created is True
    assert result.mutation is not None
    assert result.mutation.native_validation_required is True
    assert result.revision.operation == "sphere-metamorph-profile-v1"
    assert result.revision.details == {
        "type": "sphere-metamorph-profile-v1",
        "object_name": "Sphere2",
        "profile": "cushion-core",
        "evidence": ["R031", "E096"],
        "native_validation_required": True,
        "fabrication_suitable": False,
    }


def test_cylinder_metamorph_profile_records_evidence_and_validation_gate(
    tmp_path,
) -> None:
    source = tmp_path / "cylinder.xxp"
    source.write_bytes(compile_cylinder())
    workspace = ProjectWorkspace.create(tmp_path / "cylinder.xsp", source)

    result = workspace.apply(
        CylinderMetamorphMutation("Cylinder2", "bevel-25-back"),
        message="measured back bevel",
    )

    assert result.created is True
    assert result.mutation is not None
    assert result.mutation.native_validation_required is True
    assert result.revision.operation == "cylinder-metamorph-profile-v1"
    assert result.revision.details == {
        "type": "cylinder-metamorph-profile-v1",
        "object_name": "Cylinder2",
        "profile": "bevel-25-back",
        "evidence": ["R036"],
        "native_validation_required": True,
        "fabrication_suitable": False,
    }

    repeated = workspace.apply(
        CylinderMetamorphMutation("Cylinder2", "bevel-25-back"),
        message="same measured back bevel",
    )
    assert repeated.created is False
    assert repeated.revision.id == result.revision.id


def test_native_validation_attaches_mesh_without_changing_head(
    tmp_path, monkeypatch
) -> None:
    workspace = ProjectWorkspace.create(tmp_path / "project.xsp", _source(tmp_path))
    initial = workspace.status().head
    executable = tmp_path / "XenoDreamX.exe"
    executable.write_bytes(b"test executable")
    calls = 0

    def fake_run_export(
        executable_path,
        source,
        run_directory,
        report_path,
        timeout_seconds,
        poll_seconds,
        settings,
    ):
        nonlocal calls
        calls += 1
        mesh_directory = run_directory / "mesh"
        mesh_directory.mkdir(parents=True)
        mesh = mesh_directory / "model.stl"
        _closed_tetrahedron(mesh)
        report = {
            "schema": "xenodream-batch-stl/v2",
            "outcome": "succeeded",
            "stl": asdict(inspect_binary_stl(mesh)),
            "cleanup_confirmed": True,
        }
        report_path.write_text(json.dumps(report), encoding="utf-8")
        return report

    monkeypatch.setattr("xenodream_xxp.workspace.run_export", fake_run_export)
    settings = MeshExportSettings(stl_max_dimension_mm=120, mesh_size_percent=60)

    first = workspace.validate_native(executable=executable, settings=settings)
    second = workspace.validate_native(executable=executable, settings=settings)

    assert calls == 1
    assert first == second
    assert first.revision_id == initial.id
    assert first.native_model_valid is True
    assert first.evaluates_to_3d is True
    assert first.basic_mesh_valid is True
    assert first.fabrication_suitable is False
    assert first.mesh_path is not None and Path(first.mesh_path).is_file()
    assert workspace.status().head == initial
    assert workspace.status().latest_validation == first
    assert _source(tmp_path).read_bytes() == compile_cube()


def test_fabrication_assessment_is_cached_and_does_not_change_head(
    tmp_path, monkeypatch
) -> None:
    workspace = ProjectWorkspace.create(
        tmp_path / "assessed.xsp",
        _source(tmp_path),
        FabricationConstraints(
            process="FDM",
            build_volume_mm=Vector3(D("2"), D("2"), D("2")),
            min_feature_mm=D("0.8"),
        ),
    )
    initial = workspace.status().head
    executable = tmp_path / "XenoDreamX.exe"
    executable.write_bytes(b"test executable")

    def fake_run_export(
        executable_path,
        source,
        run_directory,
        report_path,
        timeout_seconds,
        poll_seconds,
        settings,
    ):
        mesh_directory = run_directory / "mesh"
        mesh_directory.mkdir(parents=True)
        mesh = mesh_directory / "model.stl"
        _closed_tetrahedron(mesh)
        report = {
            "schema": "xenodream-batch-stl/v2",
            "outcome": "succeeded",
            "stl": asdict(inspect_binary_stl(mesh)),
            "cleanup_confirmed": True,
        }
        report_path.write_text(json.dumps(report), encoding="utf-8")
        return report

    monkeypatch.setattr("xenodream_xxp.workspace.run_export", fake_run_export)
    validation = workspace.validate_native(executable=executable)

    first = workspace.assess_fabrication()
    second = workspace.assess_fabrication(validation_id=validation.id)

    assert first == second
    assert first.revision_id == initial.id
    assert first.artifact_sha256 == initial.artifact_sha256
    assert first.validation_id == validation.id
    assert first.mesh_sha256 == validation.mesh_sha256
    assert first.verdict is FabricationVerdict.INCOMPLETE
    assert first.fabrication_suitable is False
    by_code = {item.code: item for item in first.checks}
    assert by_code[CheckCode.BUILD_VOLUME].status is CheckStatus.PASS
    assert by_code[CheckCode.SELF_INTERSECTIONS].status is CheckStatus.NOT_EVALUATED
    status = workspace.status()
    assert status.head == initial
    assert status.latest_fabrication_assessment == first
    with sqlite3.connect(workspace.database) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM fabrication_assessments"
        ).fetchone()[0] == 1


def test_fabrication_assessment_rejects_cached_provenance_tampering(
    tmp_path, monkeypatch
) -> None:
    workspace = ProjectWorkspace.create(tmp_path / "tampered.xsp", _source(tmp_path))
    executable = tmp_path / "XenoDreamX.exe"
    executable.write_bytes(b"test executable")

    def fake_run_export(
        executable_path,
        source,
        run_directory,
        report_path,
        timeout_seconds,
        poll_seconds,
        settings,
    ):
        mesh_directory = run_directory / "mesh"
        mesh_directory.mkdir(parents=True)
        mesh = mesh_directory / "model.stl"
        _closed_tetrahedron(mesh)
        report = {
            "schema": "xenodream-batch-stl/v2",
            "outcome": "succeeded",
            "stl": asdict(inspect_binary_stl(mesh)),
            "cleanup_confirmed": True,
        }
        report_path.write_text(json.dumps(report), encoding="utf-8")
        return report

    monkeypatch.setattr("xenodream_xxp.workspace.run_export", fake_run_export)
    workspace.validate_native(executable=executable)
    workspace.assess_fabrication()

    with sqlite3.connect(workspace.database) as connection:
        raw = connection.execute(
            "SELECT result_json FROM fabrication_assessments"
        ).fetchone()[0]
        payload = json.loads(raw)
        payload["revision_id"] = "f" * 64
        connection.execute(
            "UPDATE fabrication_assessments SET result_json = ?",
            (json.dumps(payload),),
        )

    with pytest.raises(WorkspaceError, match="provenance"):
        workspace.assess_fabrication()


def test_fabrication_assessment_rejects_corrupted_retained_mesh(
    tmp_path, monkeypatch
) -> None:
    workspace = ProjectWorkspace.create(tmp_path / "corrupt.xsp", _source(tmp_path))
    executable = tmp_path / "XenoDreamX.exe"
    executable.write_bytes(b"test executable")

    def fake_run_export(
        executable_path,
        source,
        run_directory,
        report_path,
        timeout_seconds,
        poll_seconds,
        settings,
    ):
        mesh_directory = run_directory / "mesh"
        mesh_directory.mkdir(parents=True)
        mesh = mesh_directory / "model.stl"
        _closed_tetrahedron(mesh)
        report = {
            "schema": "xenodream-batch-stl/v2",
            "outcome": "succeeded",
            "stl": asdict(inspect_binary_stl(mesh)),
            "cleanup_confirmed": True,
        }
        report_path.write_text(json.dumps(report), encoding="utf-8")
        return report

    monkeypatch.setattr("xenodream_xxp.workspace.run_export", fake_run_export)
    validation = workspace.validate_native(executable=executable)
    assert validation.mesh_path is not None
    Path(validation.mesh_path).write_bytes(b"corrupted")

    with pytest.raises(WorkspaceError, match="mesh failed hash verification"):
        workspace.assess_fabrication(validation_id=validation.id)


def test_open_migrates_schema_one_workspace(tmp_path) -> None:
    workspace = ProjectWorkspace.create(tmp_path / "project.xsp", _source(tmp_path))
    with sqlite3.connect(workspace.database) as connection:
        connection.execute("DROP TABLE fabrication_assessments")
        connection.execute("DROP TABLE validations")
        connection.execute(
            "UPDATE metadata SET value = '1' WHERE key = 'schema_version'"
        )
        connection.commit()

    reopened = ProjectWorkspace.open(workspace.root)

    assert reopened.status().latest_validation is None
    with sqlite3.connect(workspace.database) as connection:
        assert connection.execute(
            "SELECT value FROM metadata WHERE key = 'schema_version'"
        ).fetchone()[0] == "3"
        assert connection.execute(
            "SELECT COUNT(*) FROM fabrication_assessments"
        ).fetchone()[0] == 0


def test_rejects_invalid_workspace_and_constraints(tmp_path) -> None:
    with pytest.raises(WorkspaceError, match="not a project workspace"):
        ProjectWorkspace.open(tmp_path / "missing")
    with pytest.raises(WorkspaceError, match="positive"):
        FabricationConstraints(min_feature_mm=D("0"))
