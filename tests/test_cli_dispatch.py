from __future__ import annotations

import json
from pathlib import Path

from xenosculpt.cli import main


FIXTURE = Path(__file__).parent / "fixtures" / "comfyui" / "empty-image-api.json"


def test_top_level_dispatches_comfyui_without_changing_legacy_cli(tmp_path, capsys) -> None:
    root = tmp_path / "image.csp"
    assert main(["comfyui", "init", str(root), str(FIXTURE)]) == 0
    created = json.loads(capsys.readouterr().out)
    assert created["application_id"] == "comfyui"

    assert main(["comfyui", "set-input", str(root), "1", "width", "--value-json", "96"]) == 0
    changed = json.loads(capsys.readouterr().out)
    assert changed["created"] is True

    assert main(["project", "status", str(root)]) == 2
    assert "application identity" in capsys.readouterr().err


def test_top_level_help_lists_both_application_surfaces(capsys) -> None:
    assert main(["--help"]) == 0
    output = capsys.readouterr().out
    assert "comfyui" in output
    assert "XenoDream" in output


def test_top_level_help_lists_moi_surface(capsys) -> None:
    assert main(["--help"]) == 0
    output = capsys.readouterr().out
    assert "moi" in output


def test_cli_rejects_link_shaped_literal_without_advancing_head(tmp_path, capsys) -> None:
    root = tmp_path / "image.csp"
    assert main(["comfyui", "init", str(root), str(FIXTURE)]) == 0
    initial = json.loads(capsys.readouterr().out)["head"]["id"]

    assert main(["comfyui", "set-input", str(root), "2", "images", "--value-json", '["99",0]']) == 2
    assert "link-shaped" in capsys.readouterr().err
    assert main(["comfyui", "status", str(root)]) == 0
    assert json.loads(capsys.readouterr().out)["head"]["id"] == initial
