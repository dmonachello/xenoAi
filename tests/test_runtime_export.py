from __future__ import annotations

import importlib.util
from pathlib import Path
import struct
import sys

import pytest


ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location(
    "run_xenodream_batch_stl",
    ROOT / "scripts" / "run_xenodream_batch_stl.py",
)
assert SPEC is not None and SPEC.loader is not None
runtime_export = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runtime_export
SPEC.loader.exec_module(runtime_export)


def _triangle_record(
    a: tuple[float, float, float] = (0.0, 0.0, 0.0),
    b: tuple[float, float, float] = (1.0, 0.0, 0.0),
    c: tuple[float, float, float] = (0.0, 1.0, 0.0),
) -> bytes:
    values = (
        0.0, 0.0, 1.0,
        *a,
        *b,
        *c,
        0,
    )
    return struct.pack("<12fH", *values)


def test_inspect_binary_stl_reports_structure_and_bounds(tmp_path: Path) -> None:
    path = tmp_path / "triangle.stl"
    path.write_bytes(
        b"test".ljust(80, b"\0")
        + struct.pack("<I", 1)
        + _triangle_record()
    )

    result = runtime_export.inspect_binary_stl(path)

    assert result.triangle_count == 1
    assert result.bytes == 134
    assert result.bounds_min == (0.0, 0.0, 0.0)
    assert result.bounds_max == (1.0, 1.0, 0.0)
    assert result.degenerate_triangles == 0
    assert result.boundary_edges == 3
    assert result.non_manifold_edges == 0
    assert result.inconsistent_winding_edges == 0
    assert result.connected_components == 1
    assert result.signed_volume == 0.0


def test_inspect_binary_stl_reports_closed_tetrahedron(tmp_path: Path) -> None:
    path = tmp_path / "tetrahedron.stl"
    origin = (0.0, 0.0, 0.0)
    x = (1.0, 0.0, 0.0)
    y = (0.0, 1.0, 0.0)
    z = (0.0, 0.0, 1.0)
    triangles = (
        _triangle_record(origin, y, x),
        _triangle_record(origin, x, z),
        _triangle_record(origin, z, y),
        _triangle_record(x, y, z),
    )
    path.write_bytes(
        b"test".ljust(80, b"\0")
        + struct.pack("<I", len(triangles))
        + b"".join(triangles)
    )

    result = runtime_export.inspect_binary_stl(path)

    assert result.boundary_edges == 0
    assert result.non_manifold_edges == 0
    assert result.inconsistent_winding_edges == 0
    assert result.connected_components == 1
    assert result.signed_volume == pytest.approx(1 / 6)


@pytest.mark.parametrize(
    "data, message",
    [
        (b"short", "84-byte header"),
        (b"x" * 80 + struct.pack("<I", 0), "zero triangles"),
        (
            b"x" * 80 + struct.pack("<I", 2) + _triangle_record(),
            "length mismatch",
        ),
    ],
)
def test_inspect_binary_stl_rejects_invalid_structure(
    tmp_path: Path, data: bytes, message: str
) -> None:
    path = tmp_path / "invalid.stl"
    path.write_bytes(data)

    with pytest.raises(ValueError, match=message):
        runtime_export.inspect_binary_stl(path)


def test_classify_timeout_uses_recent_cpu_or_output_activity() -> None:
    stalled = [
        {"elapsed_seconds": 0, "cpu_seconds": 1, "status_text": "Generating", "outputs": []},
        {"elapsed_seconds": 60, "cpu_seconds": 1, "status_text": "Generating", "outputs": []},
    ]
    active = [
        {"elapsed_seconds": 0, "cpu_seconds": 1, "status_text": "Generating", "outputs": []},
        {"elapsed_seconds": 60, "cpu_seconds": 2, "status_text": "Generating", "outputs": []},
    ]

    assert runtime_export.classify_timeout(stalled) == "timed_out_stalled"
    assert runtime_export.classify_timeout(active) == "timed_out_active"
