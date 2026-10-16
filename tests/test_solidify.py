from __future__ import annotations

from decimal import Decimal as D
from hashlib import sha256
import json
from pathlib import Path
import struct

import pytest

from xenodream_xxp.mesh import inspect_binary_stl
from xenodream_xxp.cli import main
from xenodream_xxp.solidify import (
    SolidifyError,
    SolidifySettings,
    solidify_binary_stl,
)


def _cube_records(
    origin: tuple[float, float, float], size: float
) -> tuple[bytes, ...]:
    ox, oy, oz = origin
    vertices = (
        (ox, oy, oz),
        (ox + size, oy, oz),
        (ox + size, oy + size, oz),
        (ox, oy + size, oz),
        (ox, oy, oz + size),
        (ox + size, oy, oz + size),
        (ox + size, oy + size, oz + size),
        (ox, oy + size, oz + size),
    )
    faces = (
        (0, 2, 1), (0, 3, 2),
        (4, 5, 6), (4, 6, 7),
        (0, 1, 5), (0, 5, 4),
        (3, 7, 6), (3, 6, 2),
        (0, 4, 7), (0, 7, 3),
        (1, 2, 6), (1, 6, 5),
    )
    return tuple(
        struct.pack(
            "<12fH",
            0.0,
            0.0,
            0.0,
            *(value for index in face for value in vertices[index]),
            0,
        )
        for face in faces
    )


def _write_cubes(
    path: Path, origins: tuple[tuple[float, float, float], ...], size: float = 10.0
) -> None:
    records = tuple(
        record for origin in origins for record in _cube_records(origin, size)
    )
    path.write_bytes(
        b"cube".ljust(80, b"\0")
        + struct.pack("<I", len(records))
        + b"".join(records)
    )


def _write_cube(path: Path, size: float = 10.0) -> None:
    _write_cubes(path, ((0.0, 0.0, 0.0),), size)


def test_solidify_offsets_closed_mesh_and_preserves_source(tmp_path: Path) -> None:
    source = tmp_path / "cube.stl"
    output = tmp_path / "cube-solid.stl"
    _write_cube(source)
    source_hash = sha256(source.read_bytes()).hexdigest()

    report = solidify_binary_stl(
        source,
        output,
        SolidifySettings(amount_mm=D("2"), voxel_mm=D("1")),
    )

    assert sha256(source.read_bytes()).hexdigest() == source_hash
    assert report.native_model_changed is False
    assert report.printability_established is False
    assert report.occupied_voxels_after > report.occupied_voxels_before
    assert report.result.max_dimension > report.source.max_dimension
    assert abs(report.result.signed_volume) > abs(report.source.signed_volume)
    assert report.result.boundary_edges == 0
    assert report.result.non_manifold_edges == 0
    assert report.result.inconsistent_winding_edges == 0
    assert report.result.connected_components == 1
    assert report.result.signed_volume > 0
    assert inspect_binary_stl(output) == report.result


def test_solidify_can_merge_nearby_closed_components(tmp_path: Path) -> None:
    source = tmp_path / "two-cubes.stl"
    output = tmp_path / "joined.stl"
    _write_cubes(source, ((0.0, 0.0, 0.0), (12.0, 0.0, 0.0)))
    assert inspect_binary_stl(source).connected_components == 2

    report = solidify_binary_stl(
        source,
        output,
        SolidifySettings(amount_mm=D("2"), voxel_mm=D("1")),
    )

    assert report.result.connected_components == 1
    assert report.result.boundary_edges == 0
    assert report.result.non_manifold_edges == 0


def test_solidify_rejects_open_mesh_and_existing_output(tmp_path: Path) -> None:
    source = tmp_path / "open.stl"
    triangle = struct.pack(
        "<12fH",
        0.0, 0.0, 1.0,
        0.0, 0.0, 0.0,
        1.0, 0.0, 0.0,
        0.0, 1.0, 0.0,
        0,
    )
    source.write_bytes(b"open".ljust(80, b"\0") + struct.pack("<I", 1) + triangle)

    with pytest.raises(SolidifyError, match="not a closed solid"):
        solidify_binary_stl(
            source,
            tmp_path / "result.stl",
            SolidifySettings(amount_mm=D("1"), voxel_mm=D("1")),
        )

    cube = tmp_path / "cube.stl"
    existing = tmp_path / "existing.stl"
    _write_cube(cube)
    existing.write_bytes(b"keep")
    with pytest.raises(SolidifyError, match="refusing to overwrite"):
        solidify_binary_stl(
            cube,
            existing,
            SolidifySettings(amount_mm=D("1"), voxel_mm=D("1")),
        )
    assert existing.read_bytes() == b"keep"


def test_solidify_settings_reject_unsafe_values() -> None:
    with pytest.raises(SolidifyError, match="amount_mm must be finite and positive"):
        SolidifySettings(amount_mm=D("0"), voxel_mm=D("1"))
    with pytest.raises(SolidifyError, match="at least voxel_mm"):
        SolidifySettings(amount_mm=D("0.5"), voxel_mm=D("1"))
    with pytest.raises(SolidifyError, match="max_voxels must be positive"):
        SolidifySettings(amount_mm=D("1"), voxel_mm=D("1"), max_voxels=0)


def test_solidify_rejects_grid_over_limit(tmp_path: Path) -> None:
    source = tmp_path / "cube.stl"
    _write_cube(source)

    with pytest.raises(SolidifyError, match="voxel grid would contain"):
        solidify_binary_stl(
            source,
            tmp_path / "result.stl",
            SolidifySettings(
                amount_mm=D("1"), voxel_mm=D("1"), max_voxels=10
            ),
        )


def test_solidify_cli_writes_report_and_refuses_overwrite(
    tmp_path: Path, capsys
) -> None:
    source = tmp_path / "cube.stl"
    output = tmp_path / "cube-solid.stl"
    _write_cube(source)

    assert main(
        [
            "solidify-stl",
            str(source),
            str(output),
            "--amount-mm",
            "2",
            "--voxel-mm",
            "1",
        ]
    ) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["native_model_changed"] is False
    assert result["printability_established"] is False
    assert result["result"]["boundary_edges"] == 0

    assert main(
        [
            "solidify-stl",
            str(source),
            str(output),
            "--amount-mm",
            "2",
            "--voxel-mm",
            "1",
        ]
    ) == 2
    assert "refusing to overwrite" in capsys.readouterr().err
