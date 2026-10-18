from __future__ import annotations

from contextlib import contextmanager
from hashlib import sha256
import json
from dataclasses import asdict
from pathlib import Path
import struct

from xenodream_xxp.cli import main
from xenodream_xxp.diffing import diff_documents
from xenodream_xxp.document import parse_bytes
from xenodream_xxp.generator import (
    COMPILER_PROFILE,
    CUBE_SPHERE_COMPILER_PROFILE,
    CYLINDER_COMPILER_PROFILE,
    SPHERE_COMPILER_PROFILE,
    THREE_CUBE_COMPILER_PROFILE,
    TWO_CUBE_COMPILER_PROFILE,
    compile_cube,
    compile_sphere,
    compile_cylinder,
)
from xenodream_xxp.validation import (
    ResolvedValidationRequest,
    XenoDreamInstallation,
    validation_profile,
)
from xenodream_xxp.mesh import inspect_binary_stl
from xenodream_xxp.native_export import MeshExportSettings
from xenodream_xxp.workspace import ProjectWorkspace


SAMPLE = (
    Path(__file__).parents[1]
    / "samples"
    / "originals"
    / "20061109Sirps08.xxp"
)


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


def test_inspect_prints_json(capsys) -> None:
    assert main(["inspect", str(SAMPLE)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["header"]["Program"] == ["XDX"]


def test_inspect_metamorphs_prints_evidence_scoped_stack(capsys) -> None:
    sample = (
        Path(__file__).parents[1]
        / "src"
        / "xenodream_xxp"
        / "templates"
        / "xdx-1.220"
        / "cube_base.xxp"
    )

    assert main(["inspect-metamorphs", str(sample)]) == 0

    report = json.loads(capsys.readouterr().out)
    assert report["metamorph_count"] == 1
    assert report["metamorphs"][0]["operation"]["name"] == "Cube"
    assert report["metamorphs"][0]["parameters"][0]["name"] == "Face Warp"


def test_roundtrip_writes_identical_file(tmp_path, capsys) -> None:
    output = tmp_path / "copy.xxp"

    assert main(["roundtrip", str(SAMPLE), str(output)]) == 0

    result = json.loads(capsys.readouterr().out)
    assert result["byte_identical"] is True
    assert output.read_bytes() == SAMPLE.read_bytes()


def test_roundtrip_refuses_to_overwrite(tmp_path, capsys) -> None:
    output = tmp_path / "existing.xxp"
    output.write_bytes(b"keep")

    assert main(["roundtrip", str(SAMPLE), str(output)]) == 2
    assert output.read_bytes() == b"keep"
    assert "already exists" in capsys.readouterr().err


def test_diff_exit_codes_and_json(tmp_path, capsys) -> None:
    same = tmp_path / "same.xxp"
    changed = tmp_path / "changed.xxp"
    same.write_bytes(SAMPLE.read_bytes())
    changed.write_bytes(SAMPLE.read_bytes().replace(b"Author=dirk monteny", b"Author=test", 1))

    assert main(["diff", str(SAMPLE), str(same)]) == 0
    assert json.loads(capsys.readouterr().out)["differences"] == []

    assert main(["diff", str(SAMPLE), str(changed)]) == 1
    differences = json.loads(capsys.readouterr().out)["differences"]
    assert differences[0]["section"] == "Header"
    assert differences[0]["key"] == "Author"


def test_validate_stl_reports_boundary_mesh_without_claiming_printability(
    tmp_path, capsys
) -> None:
    path = tmp_path / "triangle.stl"
    triangle = struct.pack(
        "<12fH",
        0, 0, 1,
        0, 0, 0,
        1, 0, 0,
        0, 1, 0,
        0,
    )
    path.write_bytes(b"test".ljust(80, b"\0") + struct.pack("<I", 1) + triangle)

    assert main(["validate-stl", str(path)]) == 1
    result = json.loads(capsys.readouterr().out)
    assert result["basic_mesh_valid"] is False
    assert result["boundary_edges"] == 3
    assert result["printability_established"] is False


def test_generate_cube_writes_verified_default(tmp_path, capsys) -> None:
    output = tmp_path / "generated.xxp"
    baseline = (
        Path(__file__).parents[1]
        / "experiments"
        / "group-creation"
        / "cube_base.xxp"
    )

    assert main(["generate-cube", str(output)]) == 0

    result = json.loads(capsys.readouterr().out)
    assert result["compiler_profile"] == COMPILER_PROFILE
    assert output.read_bytes() == baseline.read_bytes()


def test_generate_cube_refuses_to_overwrite(tmp_path, capsys) -> None:
    output = tmp_path / "existing.xxp"
    output.write_bytes(b"keep")

    assert main(["generate-cube", str(output)]) == 2
    assert output.read_bytes() == b"keep"
    assert "already exists" in capsys.readouterr().err


def test_generate_cube_applies_verified_cli_controls(tmp_path, capsys) -> None:
    output = tmp_path / "changed.xxp"
    baseline = (
        Path(__file__).parents[1]
        / "experiments"
        / "group-creation"
        / "cube_base.xxp"
    )

    assert main(
        [
            "generate-cube",
            str(output),
            "--scale",
            "25",
            "50",
            "50",
            "--face-warp",
            "0.25",
        ]
    ) == 0
    capsys.readouterr()

    differences = diff_documents(
        parse_bytes(baseline.read_bytes()), parse_bytes(output.read_bytes())
    )
    assert [
        (item["section"], item["key"], item.get("token_index"))
        for item in differences
    ] == [
        ("Holon\\1", "Transform", 0),
        ("Holon\\1\\MM\\0", "Pars", 0),
    ]


def test_generate_three_cubes_writes_verified_reference(tmp_path, capsys) -> None:
    output = tmp_path / "three.xxp"
    reference = (
        Path(__file__).parents[1]
        / "experiments"
        / "three-cube-positions"
        / "3_cube_positions.xxp"
    )

    assert main(["generate-three-cubes", str(output)]) == 0

    result = json.loads(capsys.readouterr().out)
    assert result["compiler_profile"] == THREE_CUBE_COMPILER_PROFILE
    assert result["cube_count"] == 3
    assert output.read_bytes() == reference.read_bytes()


def test_generate_three_cubes_maps_positions_in_order(tmp_path, capsys) -> None:
    output = tmp_path / "positioned.xxp"

    assert main(
        [
            "generate-three-cubes",
            str(output),
            "--position", "-100", "0", "0",
            "--position", "0", "25", "0",
            "--position", "100", "0", "-25",
        ]
    ) == 0
    capsys.readouterr()

    data = output.read_bytes()
    assert b"-100.00000 0.00000 0.00000 " in data
    assert b"0.00000 25.00000 0.00000 " in data
    assert b"100.00000 0.00000 -25.00000 " in data


def test_generate_three_cubes_rejects_wrong_position_count(tmp_path, capsys) -> None:
    output = tmp_path / "invalid.xxp"

    assert main(
        ["generate-three-cubes", str(output), "--position", "0", "0", "0"]
    ) == 2
    assert not output.exists()
    assert "exactly 3 times" in capsys.readouterr().err


def test_generate_three_cubes_refuses_to_overwrite(tmp_path, capsys) -> None:
    output = tmp_path / "existing.xxp"
    output.write_bytes(b"keep")

    assert main(["generate-three-cubes", str(output)]) == 2
    assert output.read_bytes() == b"keep"
    assert "already exists" in capsys.readouterr().err


def test_generate_two_cubes_writes_verified_reference(tmp_path, capsys) -> None:
    output = tmp_path / "two.xxp"
    reference = (
        Path(__file__).parents[1]
        / "experiments"
        / "two-cube-positions"
        / "two_cubesV2.xxp"
    )

    assert main(["generate-two-cubes", str(output)]) == 0

    result = json.loads(capsys.readouterr().out)
    assert result["compiler_profile"] == TWO_CUBE_COMPILER_PROFILE
    assert result["cube_count"] == 2
    assert output.read_bytes() == reference.read_bytes()


def test_generate_two_cubes_maps_positions_and_rejects_wrong_count(
    tmp_path, capsys
) -> None:
    output = tmp_path / "wide.xxp"
    assert main(
        [
            "generate-two-cubes",
            str(output),
            "--position", "-100", "0", "0",
            "--position", "100", "0", "0",
        ]
    ) == 0
    capsys.readouterr()
    assert b"-100.00000 0.00000 0.00000 " in output.read_bytes()
    assert b"100.00000 0.00000 0.00000 " in output.read_bytes()

    invalid = tmp_path / "invalid.xxp"
    assert main(
        ["generate-two-cubes", str(invalid), "--position", "0", "0", "0"]
    ) == 2
    assert not invalid.exists()
    assert "exactly 2 times" in capsys.readouterr().err


def test_generate_two_cubes_refuses_to_overwrite(tmp_path, capsys) -> None:
    output = tmp_path / "existing-two.xxp"
    output.write_bytes(b"keep")

    assert main(["generate-two-cubes", str(output)]) == 2
    assert output.read_bytes() == b"keep"
    assert "already exists" in capsys.readouterr().err


def test_generate_sphere_writes_verified_reference(tmp_path, capsys) -> None:
    output = tmp_path / "sphere.xxp"
    reference = (
        Path(__file__).parents[1]
        / "experiments"
        / "m4-generated-sphere"
        / "m4_generated_sphere_resaved.xxp"
    )

    assert main(["generate-sphere", str(output)]) == 0

    result = json.loads(capsys.readouterr().out)
    assert result["compiler_profile"] == SPHERE_COMPILER_PROFILE
    assert output.read_bytes() == reference.read_bytes()


def test_generate_cylinder_writes_native_accepted_default(tmp_path, capsys) -> None:
    output = tmp_path / "cylinder.xxp"

    assert main(["generate-cylinder", str(output)]) == 0

    result = json.loads(capsys.readouterr().out)
    assert result["compiler_profile"] == CYLINDER_COMPILER_PROFILE
    assert result["native_validation_required"] is True
    assert result["fabrication_suitable"] is False
    assert output.read_bytes() == compile_cylinder()


def test_generate_cube_sphere_writes_controlled_reference(tmp_path, capsys) -> None:
    output = tmp_path / "cube-sphere.xxp"
    reference = (
        Path(__file__).parents[1]
        / "experiments"
        / "cube-sphere"
        / "cube_sphere.xxp"
    )

    assert main(["generate-cube-sphere", str(output)]) == 0

    result = json.loads(capsys.readouterr().out)
    assert result["compiler_profile"] == CUBE_SPHERE_COMPILER_PROFILE
    assert output.read_bytes() == reference.read_bytes()


def test_new_generator_commands_refuse_to_overwrite(tmp_path, capsys) -> None:
    for command in (
        "generate-sphere",
        "generate-cylinder",
        "generate-cube-sphere",
    ):
        output = tmp_path / f"{command}.xxp"
        output.write_bytes(b"keep")

        assert main([command, str(output)]) == 2
        assert output.read_bytes() == b"keep"
        assert "already exists" in capsys.readouterr().err


def test_generate_row_writes_accepted_cube_sphere_profile(tmp_path, capsys) -> None:
    output = tmp_path / "row.xxp"
    reference = (
        Path(__file__).parents[1]
        / "experiments"
        / "cube-sphere"
        / "cube_sphere.xxp"
    )

    assert main(
        [
            "generate-row",
            str(output),
            "cube",
            "sphere",
            "--spacing",
            "100",
        ]
    ) == 0

    result = json.loads(capsys.readouterr().out)
    assert result["recipe"] == "centered-x-row"
    assert result["objects"] == ["cube", "sphere"]
    assert result["spacing"] == "100"
    assert output.read_bytes() == reference.read_bytes()


def test_generate_row_applies_center_and_rejects_unsupported_sequence(
    tmp_path, capsys
) -> None:
    centered = tmp_path / "centered.xxp"
    assert main(
        [
            "generate-row",
            str(centered),
            "cube",
            "cube",
            "--spacing",
            "80",
            "--center",
            "20",
            "10",
            "-5",
        ]
    ) == 0
    capsys.readouterr()
    data = centered.read_bytes()
    assert b"-20.00000 10.00000 -5.00000 " in data
    assert b"60.00000 10.00000 -5.00000 " in data

    unsupported = tmp_path / "unsupported.xxp"
    assert main(
        [
            "generate-row",
            str(unsupported),
            "sphere",
            "cube",
            "--spacing",
            "100",
        ]
    ) == 2
    assert not unsupported.exists()
    assert "supported object sequences" in capsys.readouterr().err


def test_generate_row_refuses_to_overwrite(tmp_path, capsys) -> None:
    output = tmp_path / "existing-row.xxp"
    output.write_bytes(b"keep")

    assert main(
        ["generate-row", str(output), "cube", "--spacing", "100"]
    ) == 2
    assert output.read_bytes() == b"keep"
    assert "already exists" in capsys.readouterr().err


def test_project_cli_assesses_a_validated_revision_without_claiming_printability(
    tmp_path, capsys, monkeypatch
) -> None:
    source = tmp_path / "source.xxp"
    workspace_path = tmp_path / "sculpture.xsp"
    executable = tmp_path / "XenoDreamX.exe"
    source.write_bytes(compile_cube())
    executable.write_bytes(b"test executable")

    assert main(
        [
            "project", "init", str(workspace_path), str(source),
            "--process", "FDM",
            "--build-volume", "2", "2", "2",
            "--min-feature-mm", "0.8",
        ]
    ) == 0
    capsys.readouterr()

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
    assert main(
        [
            "project", "validate", str(workspace_path),
            "--executable", str(executable),
        ]
    ) == 0
    validation = json.loads(capsys.readouterr().out)
    head_before = ProjectWorkspace.open(workspace_path).status().head.id

    assert main(["project", "assess", str(workspace_path)]) == 1
    result = json.loads(capsys.readouterr().out)

    assert result["validation_id"] == validation["id"]
    assert result["verdict"] == "incomplete"
    assert result["fabrication_suitable"] is False
    checks = {item["code"]: item for item in result["checks"]}
    assert checks["basic-mesh"]["status"] == "pass"
    assert checks["build-volume"]["status"] == "pass"
    assert checks["self-intersections"]["status"] == "not_evaluated"
    assert ProjectWorkspace.open(workspace_path).status().head.id == head_before


def test_project_cli_uses_named_validation_profile_without_raw_overrides(
    tmp_path, capsys, monkeypatch
) -> None:
    source = tmp_path / "source.xxp"
    workspace_path = tmp_path / "profile.xsp"
    executable = tmp_path / "XenoDreamX.exe"
    source.write_bytes(compile_cube())
    executable.write_bytes(b"test executable")
    executable_sha = sha256(executable.read_bytes()).hexdigest()
    assert main(["project", "init", str(workspace_path), str(source)]) == 0
    capsys.readouterr()

    def fake_run_export(
        executable_path,
        source_path,
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

    @contextmanager
    def fake_session(installation):
        yield

    monkeypatch.setattr("xenodream_xxp.workspace.run_export", fake_run_export)
    monkeypatch.setattr(
        "xenodream_xxp.workspace.resolve_profile_request",
        lambda profile, stl_max_dimension_mm, executable: ResolvedValidationRequest(
            settings=MeshExportSettings(
                stl_max_dimension_mm, validation_profile(profile).mesh_size_percent
            ),
            timeout_seconds=validation_profile(profile).timeout_seconds,
            poll_seconds=validation_profile(profile).poll_seconds,
            profile=validation_profile(profile),
            installation=XenoDreamInstallation(
                str(executable), "1.22.0.0", executable_sha
            ),
        ),
    )
    monkeypatch.setattr(
        "xenodream_xxp.workspace.ensure_no_xenodream_sessions", lambda: None
    )

    @contextmanager
    def fake_pin(_installation):
        yield executable

    monkeypatch.setattr("xenodream_xxp.workspace.pinned_executable", fake_pin)
    monkeypatch.setattr(
        "xenodream_xxp.workspace.managed_validation_session", fake_session
    )

    assert main(
        [
            "project",
            "validate",
            str(workspace_path),
            "--profile",
            "preview",
            "--stl-max-dimension-mm",
            "120",
            "--executable",
            str(executable),
        ]
    ) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["settings"]["profile"]["name"] == "preview"
    assert result["settings"]["settings"] == {
        "mesh_size_percent": 10,
        "stl_max_dimension_mm": 120,
    }

    assert main(
        [
            "project",
            "validate",
            str(workspace_path),
            "--profile",
            "preview",
            "--stl-max-dimension-mm",
            "120",
            "--mesh-size-percent",
            "20",
        ]
    ) == 2
    assert "cannot be used with --profile" in capsys.readouterr().err


def test_project_cli_creates_mutates_branches_and_exports(tmp_path, capsys) -> None:
    source = tmp_path / "source.xxp"
    workspace = tmp_path / "sculpture.xsp"
    source.write_bytes(
        (
            Path(__file__).parents[1]
            / "experiments"
            / "group-creation"
            / "cube_base.xxp"
        ).read_bytes()
    )

    assert main(
        [
            "project", "init", str(workspace), str(source),
            "--process", "FDM",
            "--build-volume", "220", "220", "250",
            "--min-feature-mm", "1.2",
        ]
    ) == 0
    created = json.loads(capsys.readouterr().out)
    assert created["current_branch"] == "main"
    assert list(created["branches"]) == ["main"]
    assert created["constraints"]["process"] == "FDM"

    assert main(
        [
            "project", "mutate", str(workspace),
            "--object", "Cube2",
            "--scale", "25", "50", "100",
            "--message", "elongate cube",
            "--prompt", "make it taller",
        ]
    ) == 0
    mutation = json.loads(capsys.readouterr().out)
    assert mutation["created"] is True
    assert mutation["revision"]["prompt"] == "make it taller"
    mutated_sha = mutation["revision"]["artifact_sha256"]

    assert main(
        ["project", "branch", str(workspace), "alternate", "--checkout"]
    ) == 0
    capsys.readouterr()
    assert main(
        [
            "project", "mutate", str(workspace),
            "--object", "Cube2", "--face-warp", "0.25",
            "--message", "warp faces",
        ]
    ) == 0
    capsys.readouterr()

    assert main(["project", "compare", str(workspace), "main", "alternate"]) == 1
    comparison = json.loads(capsys.readouterr().out)
    assert comparison["differences"][0]["section"] == "Holon\\1\\MM\\0"

    assert main(["project", "checkout", str(workspace), "main"]) == 0
    capsys.readouterr()
    output = tmp_path / "active.xxp"
    assert main(["project", "export", str(workspace), str(output)]) == 0
    exported = json.loads(capsys.readouterr().out)
    assert exported["sha256"] == mutated_sha
    assert b"25.00000 50.00000 100.00000" in output.read_bytes()


def test_project_cli_describes_a_revision_bound_partial_scene(
    tmp_path, capsys
) -> None:
    source = tmp_path / "source.xxp"
    workspace = tmp_path / "sculpture.xsp"
    source.write_bytes(compile_cube().replace(b"NumHolons=2", b"NumHolons=3"))
    assert main(["project", "init", str(workspace), str(source)]) == 0
    capsys.readouterr()

    assert main(["project", "describe", str(workspace), "--ref", "HEAD"]) == 0
    result = json.loads(capsys.readouterr().out)

    assert list(result) == [
        "schema",
        "binding",
        "xdx_version",
        "declared_holon_count",
        "nodes",
        "diagnostics",
    ]
    assert result["binding"]["revision_id"]
    assert result["nodes"][1]["constructor"] == "Cube"
    assert result["diagnostics"][0]["code"] == "holon-count-mismatch"


def test_project_cli_adds_a_cube_and_reports_structural_result(
    tmp_path, capsys
) -> None:
    source = tmp_path / "source.xxp"
    workspace = tmp_path / "sculpture.xsp"
    source.write_bytes(compile_cube())
    assert main(["project", "init", str(workspace), str(source)]) == 0
    capsys.readouterr()

    assert main(
        [
            "project", "add-cube", str(workspace),
            "--position", "75", "0", "0",
            "--message", "add right cube",
        ]
    ) == 0
    result = json.loads(capsys.readouterr().out)

    assert result["created"] is True
    assert result["revision"]["operation"] == "add-cube-v1"
    assert result["added"] == {
        "id": 2,
        "holon_index": 2,
        "name": "Cube3",
        "group_id": 0,
        "constructor": "Cube",
    }
    assert result["structural_changes"] == [
        {
            "kind": "section_added",
            "section": "Holon\\2",
            "section_occurrence": 0,
            "record_count": 30,
        },
        {
            "kind": "section_added",
            "section": "Holon\\2\\MM\\0",
            "section_occurrence": 0,
            "record_count": 9,
        },
    ]
    assert result["differences"]
    assert result["native_validation_required"] is True
    assert result["fabrication_suitable"] is False


def test_project_cli_adds_a_sphere_and_reports_structural_result(
    tmp_path, capsys
) -> None:
    source = tmp_path / "sphere-source.xxp"
    workspace = tmp_path / "sphere-sculpture.xsp"
    source.write_bytes(compile_cube())
    assert main(["project", "init", str(workspace), str(source)]) == 0
    capsys.readouterr()

    assert main(
        [
            "project", "add-sphere", str(workspace),
            "--position", "75", "0", "0",
            "--message", "add right sphere",
        ]
    ) == 0
    result = json.loads(capsys.readouterr().out)

    assert result["revision"]["operation"] == "add-sphere-v1"
    assert result["added"]["name"] == "Sphere3"
    assert result["added"]["constructor"] == "Sphere"
    assert [item["section"] for item in result["structural_changes"]] == [
        "Holon\\2", "Holon\\2\\MM\\0"
    ]
    assert result["native_validation_required"] is True
    assert result["fabrication_suitable"] is False


def test_project_cli_creates_seeded_variation(tmp_path, capsys) -> None:
    source = tmp_path / "source.xxp"
    workspace = tmp_path / "sculpture.xsp"
    source.write_bytes(
        (
            Path(__file__).parents[1]
            / "experiments"
            / "group-creation"
            / "cube_base.xxp"
        ).read_bytes()
    )
    assert main(["project", "init", str(workspace), str(source)]) == 0
    capsys.readouterr()

    assert main(
        [
            "project", "evolve", str(workspace),
            "--seed", "17", "--strength", "0.5",
            "--message", "seeded variation",
        ]
    ) == 0
    result = json.loads(capsys.readouterr().out)

    assert result["created"] is True
    assert result["revision"]["operation"] == "seeded-variation-v1"
    assert result["revision"]["details"]["seed"] == 17
    assert result["revision"]["details"]["strength"] == "0.5"
    assert result["differences"]


def test_project_cli_applies_measured_sphere_metamorph_profile(
    tmp_path, capsys
) -> None:
    source = tmp_path / "sphere.xxp"
    workspace = tmp_path / "sphere.xsp"
    source.write_bytes(compile_sphere())
    assert main(["project", "init", str(workspace), str(source)]) == 0
    capsys.readouterr()

    assert main(
        [
            "project", "metamorph", str(workspace),
            "--object", "Sphere2",
            "--profile", "cushion-core",
            "--message", "measured cushion form",
        ]
    ) == 0
    result = json.loads(capsys.readouterr().out)

    assert result["created"] is True
    assert result["native_validation_required"] is True
    assert result["fabrication_suitable"] is False
    assert result["revision"]["operation"] == "sphere-metamorph-profile-v1"
    assert result["revision"]["details"]["evidence"] == ["R031", "E096"]
    assert [item["token_index"] for item in result["differences"]] == [8, 9, 10, 11]


def test_project_cli_applies_measured_cylinder_metamorph_profile(
    tmp_path, capsys
) -> None:
    source = tmp_path / "cylinder.xxp"
    workspace = tmp_path / "cylinder.xsp"
    source.write_bytes(compile_cylinder())
    assert main(["project", "init", str(workspace), str(source)]) == 0
    capsys.readouterr()

    assert main(
        [
            "project", "metamorph", str(workspace),
            "--operation", "Cylinder",
            "--object", "Cylinder2",
            "--profile", "bevel-25-front",
            "--message", "measured front bevel",
        ]
    ) == 0
    result = json.loads(capsys.readouterr().out)

    assert result["created"] is True
    assert result["native_validation_required"] is True
    assert result["fabrication_suitable"] is False
    assert result["revision"]["operation"] == "cylinder-metamorph-profile-v1"
    assert result["revision"]["details"]["evidence"] == ["R036"]
    assert [item["token_index"] for item in result["differences"]] == [5, 6]


def test_project_cli_rejects_cross_operation_profiles_without_moving_head(
    tmp_path, capsys
) -> None:
    sphere_source = tmp_path / "sphere.xxp"
    sphere_workspace = tmp_path / "sphere.xsp"
    sphere_source.write_bytes(compile_sphere())
    assert main(["project", "init", str(sphere_workspace), str(sphere_source)]) == 0
    capsys.readouterr()
    sphere_head = ProjectWorkspace.open(sphere_workspace).status().head.id

    assert main(
        [
            "project", "metamorph", str(sphere_workspace),
            "--object", "Sphere2",
            "--profile", "length-three",
            "--message", "wrong operation",
        ]
    ) == 2
    assert "unknown Sphere metamorph profile" in capsys.readouterr().err
    assert ProjectWorkspace.open(sphere_workspace).status().head.id == sphere_head

    cylinder_source = tmp_path / "cylinder.xxp"
    cylinder_workspace = tmp_path / "cylinder.xsp"
    cylinder_source.write_bytes(compile_cylinder())
    assert main(
        ["project", "init", str(cylinder_workspace), str(cylinder_source)]
    ) == 0
    capsys.readouterr()
    cylinder_head = ProjectWorkspace.open(cylinder_workspace).status().head.id

    assert main(
        [
            "project", "metamorph", str(cylinder_workspace),
            "--operation", "Cylinder",
            "--object", "Cylinder2",
            "--profile", "cushion-core",
            "--message", "wrong operation",
        ]
    ) == 2
    assert "unknown Cylinder metamorph profile" in capsys.readouterr().err
    assert ProjectWorkspace.open(cylinder_workspace).status().head.id == cylinder_head


def test_project_cli_plans_and_applies_one_controlled_language_operation(
    tmp_path, capsys
) -> None:
    source = tmp_path / "prompt-source.xxp"
    workspace = tmp_path / "prompt.xsp"
    source.write_bytes(compile_cylinder())
    assert main(["project", "init", str(workspace), str(source)]) == 0
    capsys.readouterr()

    prompt = "apply Cylinder profile bevel-25-front to object Cylinder2"
    assert main(
        [
            "project", "prompt", str(workspace), prompt,
            "--message", "planned front bevel",
        ]
    ) == 0
    result = json.loads(capsys.readouterr().out)

    assert result["created"] is True
    assert result["plan"]["schema"] == "xenosculpt-operation-plan/v1"
    assert result["plan"]["rule"] == "apply-cylinder-profile-v1"
    assert result["plan"]["prompt"] == prompt
    assert result["plan"]["operation"]["profile"] == "bevel-25-front"
    assert result["revision"]["operation"] == "cylinder-metamorph-profile-v1"
    assert result["revision"]["prompt"] == prompt
    assert result["revision"]["details"]["planning"]["planner"] == {
        "name": "xenosculpt-controlled-english",
        "version": "1",
    }
    assert [item["token_index"] for item in result["differences"]] == [5, 6]


def test_project_cli_rejects_vague_prompt_without_moving_head(
    tmp_path, capsys
) -> None:
    source = tmp_path / "vague-source.xxp"
    workspace = tmp_path / "vague.xsp"
    source.write_bytes(compile_cube())
    assert main(["project", "init", str(workspace), str(source)]) == 0
    capsys.readouterr()
    head = ProjectWorkspace.open(workspace).status().head.id

    assert main(
        [
            "project", "prompt", str(workspace), "make it more organic",
            "--message", "vague request",
        ]
    ) == 2

    assert "supported absolute operation" in capsys.readouterr().err
    assert ProjectWorkspace.open(workspace).status().head.id == head


def test_project_cli_import_and_log(tmp_path, capsys) -> None:
    source = tmp_path / "source.xxp"
    workspace = tmp_path / "sculpture.xsp"
    source.write_bytes(
        (
            Path(__file__).parents[1]
            / "experiments"
            / "group-creation"
            / "cube_base.xxp"
        ).read_bytes()
    )
    assert main(["project", "init", str(workspace), str(source)]) == 0
    capsys.readouterr()

    manual = tmp_path / "manual.xxp"
    manual.write_bytes(source.read_bytes().replace(b"GradDensity=1.000", b"GradDensity=0.500"))
    assert main(
        [
            "project", "import", str(workspace), str(manual),
            "--message", "manual edit",
        ]
    ) == 0
    imported = json.loads(capsys.readouterr().out)
    assert imported["created"] is True

    assert main(["project", "log", str(workspace)]) == 0
    history = json.loads(capsys.readouterr().out)
    assert [item["operation"] for item in history] == ["manual-import", "init"]
