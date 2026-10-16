from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).parents[1]
TEMPLATES = ROOT / "src" / "xenodream_xxp" / "templates" / "xdx-1.220"
SPEC = importlib.util.spec_from_file_location(
    "probe_metamorph_mesh",
    ROOT / "scripts" / "probe_metamorph_mesh.py",
)
assert SPEC is not None and SPEC.loader is not None
probe = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = probe
SPEC.loader.exec_module(probe)


def test_build_variant_changes_only_named_sphere_token() -> None:
    source = (TEMPLATES / "sphere_base.xxp").read_bytes()

    output, facts = probe.build_variant(source, 1, "Ovoid", "2.8")

    assert output != source
    assert facts["persisted"] == "2.80000"
    assert facts["diff"] == [
        {
            "kind": "value_token_changed",
            "section": "Holon\\1\\MM\\0",
            "section_occurrence": 0,
            "key": "Pars",
            "key_occurrence": 0,
            "token_index": 3,
            "before": "0.00000",
            "after": "2.80000",
        }
    ]


def test_build_variant_validates_native_numeric_domain_and_precision() -> None:
    source = (TEMPLATES / "sphere_base.xxp").read_bytes()

    with pytest.raises(probe.ProbeError, match="outside native range"):
        probe.build_variant(source, 1, "Warp", "101")
    with pytest.raises(probe.ProbeError, match="3-place precision"):
        probe.build_variant(source, 1, "Warp", "0.0001")


def test_build_variant_accepts_choice_name() -> None:
    source = (TEMPLATES / "cube_base.xxp").read_bytes()

    _, facts = probe.build_variant(source, 1, "Face Shape", "Cone")

    assert facts["persisted"] == "2"
    assert facts["diff"][0]["token_index"] == 1


def test_prepare_probe_writes_manifest_and_refuses_overwrite(tmp_path: Path) -> None:
    output = tmp_path / "probe"

    manifest = probe.prepare_probe(
        TEMPLATES / "sphere_base.xxp",
        output,
        1,
        "Warp",
        ["0", "0.13", "-0.13"],
    )

    assert [item["persisted"] for item in manifest["variants"]] == [
        "0.00000",
        "0.13000",
        "-0.13000",
    ]
    assert (output / "manifest.json").is_file()
    assert len(list(output.glob("variant-*.xxp"))) == 3
    with pytest.raises(probe.ProbeError, match="already exists"):
        probe.prepare_probe(
            TEMPLATES / "sphere_base.xxp", output, 1, "Warp", ["0"]
        )


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


def test_summarize_probe_reconciles_reports_by_source_hash(tmp_path: Path) -> None:
    output = tmp_path / "probe"
    manifest = probe.prepare_probe(
        TEMPLATES / "sphere_base.xxp", output, 1, "Warp", ["0", "0.13"]
    )
    reports = []
    for index, (variant, stl) in enumerate(
        zip(
            manifest["variants"],
            (_stl(100, 10.0, 500.0), _stl(120, 12.0, 550.0)),
            strict=True,
        )
    ):
        path = tmp_path / f"report-{index}.json"
        path.write_text(
            json.dumps(
                {
                    "outcome": "succeeded",
                    "input": {"source_sha256_before": variant["sha256"]},
                    "stl": stl,
                }
            ),
            encoding="utf-8",
        )
        reports.append(path)

    summary = probe.summarize_probe(output / "manifest.json", reports)

    assert summary["all_native_exports_succeeded"] is True
    assert summary["all_basic_topology_valid"] is True
    assert summary["measured_mesh_change"] is True
    assert summary["printable"] is False
    assert summary["runs"][1]["delta_from_baseline"]["triangle_count"] == 20
    assert summary["runs"][1]["delta_from_baseline"]["dimensions"] == [
        2.0,
        0.0,
        0.0,
    ]


def test_summarize_probe_uses_successful_repeated_baseline_only(tmp_path: Path) -> None:
    output = tmp_path / "probe"
    manifest = probe.prepare_probe(
        TEMPLATES / "sphere_base.xxp", output, 1, "Warp", ["0", "0.13"]
    )
    baseline_hash = manifest["variants"][0]["sha256"]
    mutation_hash = manifest["variants"][1]["sha256"]
    payloads = (
        {"outcome": "failed", "input": {"source_sha256_before": baseline_hash}},
        {
            "outcome": "succeeded",
            "input": {"source_sha256_before": baseline_hash},
            "stl": _stl(100, 10.0, 500.0),
        },
        {
            "outcome": "succeeded",
            "input": {"source_sha256_before": baseline_hash},
            "stl": _stl(100, 10.1, 500.1),
        },
        {
            "outcome": "succeeded",
            "input": {"source_sha256_before": mutation_hash},
            "stl": _stl(100, 10.05, 500.05),
        },
    )
    reports = []
    for index, payload in enumerate(payloads):
        path = tmp_path / f"report-{index}.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        reports.append(path)

    summary = probe.summarize_probe(output / "manifest.json", reports)

    assert summary["all_native_exports_succeeded"] is False
    assert summary["baseline_variation"] == {
        "triangle_count_span": 0,
        "absolute_volume_span": pytest.approx(0.1),
        "dimension_spans": [pytest.approx(0.1), 0.0, 0.0],
        "replicates": 2,
    }
    mutation = next(
        run for run in summary["runs"] if run["variant"]["index"] == 1
    )
    assert mutation["delta_from_baseline"]["dimensions"] == [
        pytest.approx(0.05),
        0.0,
        0.0,
    ]
    assert mutation["exceeds_observed_baseline_variation"] is False
