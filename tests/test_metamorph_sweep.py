from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location(
    "sweep_metamorph_mesh", SCRIPTS / "sweep_metamorph_mesh.py"
)
assert SPEC is not None and SPEC.loader is not None
sweep = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = sweep
SPEC.loader.exec_module(sweep)


def _plan(tmp_path: Path) -> Path:
    source = ROOT / "src/xenodream_xxp/templates/xdx-1.220/sphere_base.xxp"
    path = tmp_path / "plan.json"
    path.write_text(
        json.dumps(
            {
                "schema": sweep.SCHEMA,
                "operation": "Sphere",
                "source": str(source),
                "holon": 1,
                "baseline_replicates": 2,
                "cases": [
                    {
                        "id": "ovoid-positive",
                        "parameter": "Ovoid",
                        "value": "2.8",
                        "source": "controlled test",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def _interaction_plan(tmp_path: Path) -> Path:
    source = ROOT / "src/xenodream_xxp/templates/xdx-1.220/sphere_base.xxp"
    path = tmp_path / "interaction-plan.json"
    path.write_text(
        json.dumps(
            {
                "schema": sweep.SCHEMA_V2,
                "operation": "Sphere",
                "source": str(source),
                "holon": 1,
                "baseline_replicates": 2,
                "cases": [
                    {
                        "id": "shear-control",
                        "compare_to": "baseline",
                        "source": "test control",
                        "mutations": [{"parameter": "Shear", "value": "8"}],
                    },
                    {
                        "id": "shear-biased",
                        "compare_to": "shear-control",
                        "source": "test interaction",
                        "mutations": [
                            {"parameter": "Shear", "value": "8"},
                            {"parameter": "Shear Bias", "value": "100"},
                        ],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def _mesh(source: Path, changed: bool) -> dict[str, object]:
    return {
        "sha256": f"mesh-{source.stem}",
        "triangle_count": 120 if changed else 100,
        "dimensions": [8.0, 10.0, 8.0] if changed else [10.0, 10.0, 10.0],
        "signed_volume": 400.0 if changed else 500.0,
        "connected_components": 1,
        "boundary_edges": 0,
        "non_manifold_edges": 0,
        "degenerate_triangles": 0,
        "inconsistent_winding_edges": 0,
    }


def _stl(triangles: int, x: float, volume: float) -> dict[str, object]:
    return {
        "triangle_count": triangles,
        "dimensions": [x, 10.0, 10.0],
        "signed_volume": volume,
        "connected_components": 1,
        "boundary_edges": 0,
        "non_manifold_edges": 0,
        "degenerate_triangles": 0,
        "inconsistent_winding_edges": 0,
    }


def test_run_sweep_prepares_resumes_and_ranks_cases(tmp_path: Path) -> None:
    calls: list[str] = []

    def fake_exporter(
        executable, source, run_directory, report_path, timeout, poll, settings
    ):
        del executable, timeout, poll, settings
        calls.append(run_directory.parent.name)
        report = {
            "outcome": "succeeded",
            "input": {
                "source_sha256_before": sweep._digest(source.read_bytes())
            },
            "stl": _mesh(source, "ovoid" in source.stem),
        }
        sweep._write_json(report_path, report)
        return report

    plan = _plan(tmp_path)
    output = tmp_path / "sweep"
    first = sweep.run_sweep(plan, output, exporter=fake_exporter)
    second = sweep.run_sweep(plan, output, exporter=fake_exporter)

    assert calls == ["baseline-1", "baseline-2", "ovoid-positive"]
    assert first == second
    assert first["complete"] is True
    assert first["baseline_variation"]["replicates"] == 2
    assert first["ranked_results"][0]["parameter"] == "Ovoid"
    assert first["ranked_results"][0]["impact_score"] == pytest.approx(0.2)
    assert first["ranked_results"][0]["changes_exceeding_observed_baseline"] == [
        "triangle_count",
        "absolute_volume",
        "dimensions",
    ]
    assert first["execution"] == [
        {"id": "baseline-1", "attempts": 1, "outcomes": ["succeeded"]},
        {"id": "baseline-2", "attempts": 1, "outcomes": ["succeeded"]},
        {"id": "ovoid-positive", "attempts": 1, "outcomes": ["succeeded"]},
    ]
    assert first["all_basic_topology_valid"] is True
    assert first["printable"] is False


def test_plan_rejects_duplicate_parameters_and_changed_resume(tmp_path: Path) -> None:
    plan = _plan(tmp_path)
    value = json.loads(plan.read_text(encoding="utf-8"))
    value["cases"].append(
        {
            "id": "ovoid-second",
            "parameter": "ovoid",
            "value": "1",
            "source": "test",
        }
    )
    plan.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(sweep.SweepError, match="duplicate parameter"):
        sweep.load_plan(plan)

    clean = _plan(tmp_path)
    output = tmp_path / "resume"
    sweep.prepare_sweep(clean, output, sweep.MeshExportSettings(100, 25))
    changed = json.loads(clean.read_text(encoding="utf-8"))
    changed["cases"][0]["value"] = "3"
    clean.write_text(json.dumps(changed), encoding="utf-8")
    with pytest.raises(sweep.SweepError, match="different sweep plan"):
        sweep.prepare_sweep(clean, output, sweep.MeshExportSettings(100, 25))


def test_interaction_plan_builds_cumulative_diff_and_named_comparison(
    tmp_path: Path,
) -> None:
    plan = _interaction_plan(tmp_path)
    output = tmp_path / "interactions"

    def fake_exporter(
        executable, source, run_directory, report_path, timeout, poll, settings
    ):
        del executable, timeout, poll, settings
        if source.stem == "shear-biased":
            mesh = _stl(130, 12.0, 600.0)
        else:
            mesh = _stl(100, 10.0, 500.0)
        report = {
            "outcome": "succeeded",
            "input": {
                "source_sha256_before": sweep._digest(source.read_bytes())
            },
            "stl": {"sha256": f"mesh-{source.stem}", **mesh},
        }
        sweep._write_json(report_path, report)
        return report

    summary = sweep.run_sweep(plan, output, exporter=fake_exporter)
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    biased = next(job for job in manifest["jobs"] if job["id"] == "shear-biased")
    result = next(item for item in summary["ranked_results"] if item["id"] == "shear-biased")

    assert biased["compare_to"] == "shear-control"
    assert [item["token_index"] for item in biased["diff"]] == [6, 7]
    assert [item["parameter"] for item in biased["mutations"]] == [
        "Shear",
        "Shear Bias",
    ]
    assert result["compare_to"] == "shear-control"
    assert result["delta"]["triangle_count"] == 30
    assert result["delta"]["dimensions"] == [2.0, 0.0, 0.0]
    assert result["delta"]["absolute_volume"] == 100.0


def test_interaction_plan_rejects_forward_controls_and_repeated_mutations(
    tmp_path: Path,
) -> None:
    plan = _interaction_plan(tmp_path)
    value = json.loads(plan.read_text(encoding="utf-8"))
    value["cases"][0]["compare_to"] = "shear-biased"
    plan.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(sweep.SweepError, match="baseline or an earlier case"):
        sweep.load_plan(plan)

    plan = _interaction_plan(tmp_path)
    value = json.loads(plan.read_text(encoding="utf-8"))
    value["cases"][1]["mutations"].append(
        {"parameter": "shear", "value": "4"}
    )
    plan.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(sweep.SweepError, match="repeats parameter"):
        sweep.load_plan(plan)

    plan = _interaction_plan(tmp_path)
    value = json.loads(plan.read_text(encoding="utf-8"))
    value["cases"][0]["id"] = "baseline"
    plan.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(sweep.SweepError, match="reserved"):
        sweep.load_plan(plan)
