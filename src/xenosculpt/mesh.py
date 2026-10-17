"""Application-neutral inspection of binary STL meshes."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from hashlib import sha256
import math
from pathlib import Path
import struct


@dataclass(frozen=True, slots=True)
class StlReport:
    path: str
    bytes: int
    sha256: str
    triangle_count: int
    bounds_min: tuple[float, float, float]
    bounds_max: tuple[float, float, float]
    dimensions: tuple[float, float, float]
    max_dimension: float
    degenerate_triangles: int
    boundary_edges: int
    non_manifold_edges: int
    inconsistent_winding_edges: int
    connected_components: int
    signed_volume: float


def basic_mesh_valid(report: StlReport) -> bool:
    return all((report.triangle_count > 0, report.degenerate_triangles == 0,
                report.boundary_edges == 0, report.non_manifold_edges == 0,
                report.inconsistent_winding_edges == 0,
                report.connected_components == 1, report.signed_volume != 0))


def inspect_binary_stl(path: Path) -> StlReport:
    data = path.read_bytes()
    if len(data) < 84:
        raise ValueError("binary STL is shorter than its 84-byte header")
    triangle_count = struct.unpack_from("<I", data, 80)[0]
    if triangle_count == 0:
        raise ValueError("binary STL contains zero triangles")
    expected = 84 + 50 * triangle_count
    if len(data) != expected:
        raise ValueError(f"binary STL length mismatch: expected {expected}, found {len(data)}")
    minimum = [math.inf] * 3
    maximum = [-math.inf] * 3
    degenerate = 0
    edge_counts: Counter = Counter()
    edge_directions: Counter = Counter()
    parent: dict[tuple[float, float, float], tuple[float, float, float]] = {}
    signed_volume = 0.0

    def find(vertex):
        parent.setdefault(vertex, vertex)
        root = vertex
        while parent[root] != root:
            root = parent[root]
        while parent[vertex] != vertex:
            next_vertex = parent[vertex]
            parent[vertex] = root
            vertex = next_vertex
        return root

    def union(first, second):
        first_root, second_root = find(first), find(second)
        if first_root != second_root:
            parent[second_root] = first_root

    offset = 84
    for _ in range(triangle_count):
        values = struct.unpack_from("<12fH", data, offset)
        coordinates = values[3:12]
        if not all(math.isfinite(value) for value in coordinates):
            raise ValueError("binary STL contains a non-finite vertex coordinate")
        vertices = tuple(tuple(coordinates[i:i + 3]) for i in range(0, 9, 3))
        for vertex in vertices:
            for axis, value in enumerate(vertex):
                minimum[axis] = min(minimum[axis], value)
                maximum[axis] = max(maximum[axis], value)
        a, b, c = vertices
        ab = tuple(b[i] - a[i] for i in range(3))
        ac = tuple(c[i] - a[i] for i in range(3))
        cross = (ab[1] * ac[2] - ab[2] * ac[1], ab[2] * ac[0] - ab[0] * ac[2], ab[0] * ac[1] - ab[1] * ac[0])
        if sum(value * value for value in cross) == 0.0:
            degenerate += 1
        signed_volume += (a[0] * (b[1] * c[2] - b[2] * c[1]) + a[1] * (b[2] * c[0] - b[0] * c[2]) + a[2] * (b[0] * c[1] - b[1] * c[0])) / 6.0
        union(a, b)
        union(b, c)
        for start, end in ((a, b), (b, c), (c, a)):
            edge = (start, end) if start < end else (end, start)
            edge_counts[edge] += 1
            edge_directions[edge] += 1 if start < end else -1
        offset += 50
    dimensions = tuple(maximum[i] - minimum[i] for i in range(3))
    return StlReport(str(path.resolve()), len(data), sha256(data).hexdigest(), triangle_count,
                     tuple(minimum), tuple(maximum), dimensions, max(dimensions), degenerate,
                     sum(v == 1 for v in edge_counts.values()), sum(v > 2 for v in edge_counts.values()),
                     sum(edge_counts[e] == 2 and abs(v) == 2 for e, v in edge_directions.items()),
                     len({find(vertex) for vertex in parent}), signed_volume)
