from __future__ import annotations

import json
from pathlib import Path

from xenodream_xxp.cli import main


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

