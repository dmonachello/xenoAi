from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location(
    "inventory_xdx_corpus", ROOT / "scripts" / "inventory_xdx_corpus.py"
)
assert SPEC is not None and SPEC.loader is not None
inventory_xdx_corpus = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(inventory_xdx_corpus)


def test_inventory_preserves_projects_and_checks_declared_counts(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    project = (
        b"[Header]\r\nProgversion=1.220\r\nNumHolons=1\r\n"
        b"[Holon\\0]\r\nID=0\r\nType=1\r\nName=Sphere\r\n"
        b"[Holon\\0\\MM\\0]\r\nStyle=1\r\nNumPars=2\r\nPars=0 1 \r\n"
    )
    (corpus / "sample.xxp").write_bytes(project)
    presets = tmp_path / "XDXSystem.xmm"
    presets.write_bytes(b"[Sphere]\r\nDefault=2 0 1\r\n")

    result = inventory_xdx_corpus.build_inventory(corpus, presets)

    assert result["corpus"]["project_count"] == 1
    assert result["corpus"]["versions"] == {"1.220": 1}
    assert result["corpus"]["source"] == "corpus"
    assert result["corpus"]["all_roundtrip_exact"] is True
    assert result["corpus"]["all_num_holons_match"] is True
    assert result["corpus"]["all_num_pars_match"] is True
    assert result["corpus"]["type1_mm0_name_style_candidates"] == [
        {"name": "Sphere", "style": "1", "count": 1}
    ]
    assert result["presets"]["rows_with_count_mismatch"] == 0
    assert result["presets"]["file"] == "XDXSystem.xmm"


def test_inventory_reports_invariant_failures_without_rejecting_source(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "mismatch.xxp").write_bytes(
        b"[Header]\nNumHolons=2\n[Holon\\0]\nType=1\n"
        b"[Holon\\0\\MM\\0]\nNumPars=3\nPars=0 1\n"
    )
    presets = tmp_path / "XDXSystem.xmm"
    presets.write_bytes(b"[Cube]\nDefault=3 0 1\n")

    result = inventory_xdx_corpus.build_inventory(corpus, presets)

    assert result["corpus"]["all_roundtrip_exact"] is True
    assert result["corpus"]["all_num_holons_match"] is False
    assert result["corpus"]["all_num_pars_match"] is False
    assert result["presets"]["rows_with_count_mismatch"] == 1
