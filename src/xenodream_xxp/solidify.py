"""Create a thicker fabrication mesh while retaining the native XDX source."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import math
from pathlib import Path
import struct

from .mesh import StlReport, inspect_binary_stl


class SolidifyError(ValueError):
    """A mesh cannot be solidified without violating a stated invariant."""


@dataclass(frozen=True, slots=True)
class SolidifySettings:
    amount_mm: Decimal
    voxel_mm: Decimal
    max_voxels: int = 30_000_000

    def __post_init__(self) -> None:
        for name in ("amount_mm", "voxel_mm"):
            value = getattr(self, name)
            if not isinstance(value, Decimal):
                raise TypeError(f"{name} must be Decimal")
            if not value.is_finite() or value <= 0:
                raise SolidifyError(f"{name} must be finite and positive")
        if self.amount_mm < self.voxel_mm:
            raise SolidifyError("amount_mm must be at least voxel_mm")
        if isinstance(self.max_voxels, bool) or not isinstance(self.max_voxels, int):
            raise TypeError("max_voxels must be an integer")
        if self.max_voxels <= 0:
            raise SolidifyError("max_voxels must be positive")


@dataclass(frozen=True, slots=True)
class SolidifyReport:
    source: StlReport
    result: StlReport
    amount_mm: Decimal
    voxel_mm: Decimal
    grid_shape: tuple[int, int, int]
    occupied_voxels_before: int
    occupied_voxels_after: int
    native_model_changed: bool = False
    printability_established: bool = False


def _require_closed_mesh(report: StlReport) -> None:
    failures = []
    if report.degenerate_triangles:
        failures.append("degenerate triangles")
    if report.boundary_edges:
        failures.append("boundary edges")
    if report.non_manifold_edges:
        failures.append("non-manifold edges")
    if report.inconsistent_winding_edges:
        failures.append("inconsistent winding")
    if report.signed_volume == 0:
        failures.append("zero signed volume")
    if failures:
        raise SolidifyError("source mesh is not a closed solid: " + ", ".join(failures))


def _read_triangles(path: Path):
    try:
        import numpy as np
    except ImportError as error:  # pragma: no cover - packaging/runtime boundary
        raise SolidifyError("solidification requires the fabrication dependencies") from error

    data = path.read_bytes()
    triangle_count = struct.unpack_from("<I", data, 80)[0]
    triangles = np.empty((triangle_count, 3, 3), dtype=np.float64)
    offset = 84
    for index in range(triangle_count):
        values = struct.unpack_from("<12fH", data, offset)
        triangles[index] = np.asarray(values[3:12], dtype=np.float64).reshape(3, 3)
        offset += 50
    return triangles


def _grid_bounds(triangles, settings: SolidifySettings):
    import numpy as np

    pitch = float(settings.voxel_mm)
    amount = float(settings.amount_mm)
    margin = amount + pitch * 2
    minimum = triangles.min(axis=(0, 1)) - margin
    maximum = triangles.max(axis=(0, 1)) + margin
    shape = tuple(int(math.ceil((maximum[i] - minimum[i]) / pitch)) + 1 for i in range(3))
    voxel_count = math.prod(shape)
    if voxel_count > settings.max_voxels:
        raise SolidifyError(
            f"voxel grid would contain {voxel_count:,} cells, above the "
            f"{settings.max_voxels:,} limit; increase --voxel-mm"
        )
    return np.asarray(minimum, dtype=np.float64), shape


def _projected_index_range(
    low: float, high: float, origin: float, pitch: float, count: int
) -> tuple[int, int] | None:
    first = max(0, math.ceil((low - origin) / pitch - 0.5))
    last = min(count - 1, math.floor((high - origin) / pitch - 0.5))
    return None if first > last else (first, last)


def _voxelize_closed_mesh(triangles, origin, shape, pitch: float):
    import numpy as np

    nx, ny, nz = shape
    crossings: list[list[float]] = [[] for _ in range(ny * nz)]
    epsilon = 1e-10

    for triangle in triangles:
        x0, y0, z0 = triangle[0]
        x1, y1, z1 = triangle[1]
        x2, y2, z2 = triangle[2]
        denominator = (y1 - y2) * (z0 - z2) + (z2 - z1) * (y0 - y2)
        if abs(denominator) <= epsilon:
            continue
        y_range = _projected_index_range(
            min(y0, y1, y2), max(y0, y1, y2), origin[1], pitch, ny
        )
        z_range = _projected_index_range(
            min(z0, z1, z2), max(z0, z1, z2), origin[2], pitch, nz
        )
        if y_range is None or z_range is None:
            continue
        y_indices = np.arange(y_range[0], y_range[1] + 1)
        z_indices = np.arange(z_range[0], z_range[1] + 1)
        yy, zz = np.meshgrid(
            origin[1] + (y_indices + 0.5) * pitch,
            origin[2] + (z_indices + 0.5) * pitch,
            indexing="ij",
        )
        first = ((y1 - y2) * (zz - z2) + (z2 - z1) * (yy - y2)) / denominator
        second = ((y2 - y0) * (zz - z2) + (z0 - z2) * (yy - y2)) / denominator
        third = 1.0 - first - second
        inside = (first >= -epsilon) & (second >= -epsilon) & (third >= -epsilon)
        rows, columns = np.nonzero(inside)
        for row, column in zip(rows.tolist(), columns.tolist()):
            y_index = int(y_indices[row])
            z_index = int(z_indices[column])
            x = float(
                first[row, column] * x0
                + second[row, column] * x1
                + third[row, column] * x2
            )
            crossings[y_index * nz + z_index].append(x)

    occupied = np.zeros(shape, dtype=bool)
    merge_tolerance = pitch * 1e-6
    odd_rows = 0
    for flat_index, values in enumerate(crossings):
        if not values:
            continue
        values.sort()
        unique = [values[0]]
        for value in values[1:]:
            if abs(value - unique[-1]) > merge_tolerance:
                unique.append(value)
        if len(unique) % 2:
            odd_rows += 1
            continue
        y_index, z_index = divmod(flat_index, nz)
        for low, high in zip(unique[0::2], unique[1::2]):
            first = max(0, math.ceil((low - origin[0]) / pitch - 0.5))
            last = min(nx - 1, math.floor((high - origin[0]) / pitch - 0.5))
            if first <= last:
                occupied[first : last + 1, y_index, z_index] = True
    if odd_rows:
        raise SolidifyError(
            f"voxelization encountered {odd_rows} ambiguous scan rows; "
            "try a different --voxel-mm"
        )
    if not occupied.any():
        raise SolidifyError("voxelization produced an empty solid")
    return occupied


def _write_binary_stl(path: Path, vertices, faces) -> None:
    import numpy as np

    a = vertices[faces[:, 0]]
    b = vertices[faces[:, 1]]
    c = vertices[faces[:, 2]]
    signed_volume = float(np.einsum("ij,ij->i", a, np.cross(b, c)).sum() / 6.0)
    if signed_volume < 0:
        faces = faces[:, [0, 2, 1]]
    header = b"xenosculpt solidified mesh".ljust(80, b"\0")
    with path.open("wb") as output:
        output.write(header)
        output.write(struct.pack("<I", len(faces)))
        for face in faces:
            a, b, c = vertices[face]
            normal = np.cross(b - a, c - a)
            length = float(np.linalg.norm(normal))
            if length:
                normal = normal / length
            values = (*normal.tolist(), *a.tolist(), *b.tolist(), *c.tolist(), 0)
            output.write(struct.pack("<12fH", *values))


def solidify_binary_stl(
    source: Path, destination: Path, settings: SolidifySettings
) -> SolidifyReport:
    """Offset a closed binary STL outward and validate the derived mesh."""

    try:
        import numpy as np
        from scipy.ndimage import distance_transform_edt
        from skimage.measure import marching_cubes
    except ImportError as error:  # pragma: no cover - packaging/runtime boundary
        raise SolidifyError(
            "solidification requires numpy, scipy, and scikit-image; "
            "install xenodream-xxp[fabrication]"
        ) from error

    if not isinstance(source, Path) or not isinstance(destination, Path):
        raise TypeError("source and destination must be Path values")
    if not isinstance(settings, SolidifySettings):
        raise TypeError("settings must be SolidifySettings")
    if source.resolve() == destination.resolve():
        raise SolidifyError("source and destination must differ")
    if destination.exists():
        raise SolidifyError(f"refusing to overwrite: {destination} already exists")

    source_report = inspect_binary_stl(source)
    _require_closed_mesh(source_report)
    triangles = _read_triangles(source)
    origin, shape = _grid_bounds(triangles, settings)
    pitch = float(settings.voxel_mm)
    occupied = _voxelize_closed_mesh(triangles, origin, shape, pitch)
    before = int(np.count_nonzero(occupied))
    distances = distance_transform_edt(~occupied, sampling=pitch)
    expanded = occupied | (distances <= float(settings.amount_mm) + 1e-12)
    after = int(np.count_nonzero(expanded))

    padded = np.pad(expanded.astype(np.uint8), 1)
    vertices, faces, _, _ = marching_cubes(
        padded,
        level=0.5,
        spacing=(pitch, pitch, pitch),
        allow_degenerate=False,
        method="lewiner",
    )
    vertices += origin - pitch * 0.5
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        _write_binary_stl(destination, vertices, faces)
        result_report = inspect_binary_stl(destination)
        _require_closed_mesh(result_report)
    except Exception:
        if destination.exists():
            destination.unlink()
        raise

    if after <= before:
        destination.unlink()
        raise SolidifyError("solidification did not add occupied volume")
    return SolidifyReport(
        source=source_report,
        result=result_report,
        amount_mm=settings.amount_mm,
        voxel_mm=settings.voxel_mm,
        grid_shape=shape,
        occupied_voxels_before=before,
        occupied_voxels_after=after,
    )
