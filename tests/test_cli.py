from __future__ import annotations

import json
from pathlib import Path

from xenodream_xxp.cli import main
from xenodream_xxp.diffing import diff_documents
from xenodream_xxp.document import parse_bytes
from xenodream_xxp.generator import COMPILER_PROFILE, THREE_CUBE_COMPILER_PROFILE


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
