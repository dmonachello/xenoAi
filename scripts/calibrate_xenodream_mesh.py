"""Summarize controlled XenoDream mesh-export calibration runs."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys


def _load_run(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("outcome") != "succeeded":
        raise ValueError(f"calibration run did not succeed: {path}")
    settings = payload.get("mesh_export_settings")
    stl = payload.get("stl")
    if not isinstance(settings, dict) or not isinstance(stl, dict):
        raise ValueError(f"calibration run lacks settings or STL data: {path}")
    requested = settings.get("requested")
    persisted = settings.get("persisted_after", requested)
    if not isinstance(requested, dict) or persisted != requested:
        raise ValueError(f"calibration settings were not verified: {path}")
    return {
        "report": str(path.resolve()),
        "report_sha256": sha256(path.read_bytes()).hexdigest(),
        "stl_max_dimension_mm": int(requested["stl_max_dimension_mm"]),
        "mesh_size_percent": int(requested["mesh_size_percent"]),
        "measured_max_dimension_mm": float(stl["max_dimension"]),
        "triangle_count": int(stl["triangle_count"]),
        "boundary_edges": int(stl["boundary_edges"]),
        "non_manifold_edges": int(stl["non_manifold_edges"]),
        "connected_components": int(stl["connected_components"]),
    }


def summarize(paths: list[Path]) -> dict[str, object]:
    runs = sorted(
        (_load_run(path) for path in paths),
        key=lambda run: (run["stl_max_dimension_mm"], run["mesh_size_percent"]),
    )
    if len(runs) < 2:
        raise ValueError("at least two successful reports are required")

    comparisons: list[dict[str, object]] = []
    for left_index, left in enumerate(runs):
        for right in runs[left_index + 1 :]:
            if left["mesh_size_percent"] == right["mesh_size_percent"]:
                requested_ratio = (
                    right["stl_max_dimension_mm"] / left["stl_max_dimension_mm"]
                )
                measured_ratio = (
                    right["measured_max_dimension_mm"]
                    / left["measured_max_dimension_mm"]
                )
                comparisons.append(
                    {
                        "kind": "physical_scale",
                        "left_report": left["report"],
                        "right_report": right["report"],
                        "requested_ratio": requested_ratio,
                        "measured_ratio": measured_ratio,
                        "relative_error": abs(measured_ratio - requested_ratio)
                        / requested_ratio,
                    }
                )
            if left["stl_max_dimension_mm"] == right["stl_max_dimension_mm"]:
                sampling_ratio = (
                    right["mesh_size_percent"] / left["mesh_size_percent"]
                )
                triangle_ratio = right["triangle_count"] / left["triangle_count"]
                expected_surface_ratio = sampling_ratio * sampling_ratio
                comparisons.append(
                    {
                        "kind": "mesh_resolution",
                        "left_report": left["report"],
                        "right_report": right["report"],
                        "sampling_ratio": sampling_ratio,
                        "triangle_ratio": triangle_ratio,
                        "expected_surface_ratio": expected_surface_ratio,
                        "relative_error": abs(
                            triangle_ratio - expected_surface_ratio
                        )
                        / expected_surface_ratio,
                    }
                )

    return {
        "schema": "xenodream-mesh-calibration/v1",
        "run_count": len(runs),
        "runs": runs,
        "comparisons": comparisons,
        "claims": {
            "coordinate_unit": "millimetre",
            "stl_max_dimension_controls_physical_scale": any(
                item["kind"] == "physical_scale"
                and item["relative_error"] <= 0.01
                for item in comparisons
            ),
            "mesh_size_controls_linear_sampling_resolution": any(
                item["kind"] == "mesh_resolution"
                and item["relative_error"] <= 0.02
                for item in comparisons
            ),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("reports", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = summarize(args.reports)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(str(error), file=sys.stderr)
        return 2
    print(json.dumps(result["claims"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
