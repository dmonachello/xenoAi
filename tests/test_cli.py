from __future__ import annotations

import json
from pathlib import Path
import struct

from xenodream_xxp.cli import main
from xenodream_xxp.diffing import diff_documents
from xenodream_xxp.document import parse_bytes
from xenodream_xxp.generator import (
    COMPILER_PROFILE,
    CUBE_SPHERE_COMPILER_PROFILE,
    SPHERE_COMPILER_PROFILE,
    THREE_CUBE_COMPILER_PROFILE,
    TWO_CUBE_COMPILER_PROFILE,
)


SAMPLE = (
    Path(__file__).parents[1]
    / "samples"
    / "originals"
    / "20061109Sirps08.xxp"
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
    for command in ("generate-sphere", "generate-cube-sphere"):
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
