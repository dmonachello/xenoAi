from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location(
    "calibrate_xenodream_mesh",
    ROOT / "scripts" / "calibrate_xenodream_mesh.py",
)
assert SPEC is not None and SPEC.loader is not None
calibration = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = calibration
SPEC.loader.exec_module(calibration)


def _report(
    path: Path, *, dimension: int, percent: int, measured: float, triangles: int
) -> Path:
    payload = {
        "outcome": "succeeded",
        "mesh_export_settings": {
            "requested": {
                "stl_max_dimension_mm": dimension,
                "mesh_size_percent": percent,
            },
            "persisted_after": {
                "stl_max_dimension_mm": dimension,
                "mesh_size_percent": percent,
            },
        },
        "stl": {
            "max_dimension": measured,
            "triangle_count": triangles,
            "boundary_edges": 0,
            "non_manifold_edges": 0,
            "connected_components": 1,
        },
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_summarize_recovers_scale_and_resolution_relationships(tmp_path: Path) -> None:
    reports = [
        _report(tmp_path / "small.json", dimension=125, percent=50, measured=120, triangles=100),
        _report(tmp_path / "base.json", dimension=250, percent=50, measured=240, triangles=100),
        _report(tmp_path / "coarse.json", dimension=250, percent=25, measured=240, triangles=25),
    ]

    result = calibration.summarize(reports)

    assert result["claims"] == {
        "coordinate_unit": "millimetre",
        "stl_max_dimension_controls_physical_scale": True,
        "mesh_size_controls_linear_sampling_resolution": True,
    }


def test_summarize_rejects_unverified_settings(tmp_path: Path) -> None:
    report = _report(
        tmp_path / "bad.json", dimension=250, percent=50, measured=240, triangles=100
    )
    payload = json.loads(report.read_text(encoding="utf-8"))
    payload["mesh_export_settings"]["persisted_after"]["mesh_size_percent"] = 25
    report.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="not verified"):
        calibration.summarize([report, report])
