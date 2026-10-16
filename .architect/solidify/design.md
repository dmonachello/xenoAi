# Physical solidification design

Date: 2026-10-16

## Caller experience

```powershell
xenosculpt solidify-stl input.stl output-solid.stl `
  --amount-mm 1.0 --voxel-mm 0.5
```

The command retains the editable `.xxp` as the procedural source and creates a
derived fabrication mesh. It reports the requested outward offset, voxel
resolution, source and result hashes, volume change, component count, and the
same closed-manifold checks used by `validate-stl`.

`amount-mm` means geometric material added normal to the sampled solid. Nearby
components separated by less than approximately twice that amount may merge.
It does not mean slicer infill, wall count, or a guaranteed minimum feature
size. `voxel-mm` is explicit because it bounds both fidelity and memory use.

## Why this layer

XenoDream's `Density` field is the UI's **Relative Density** value. Static
analysis confirms that the UI handler stores a double-valued per-holon field,
but controlled exports at -0.5, 0, and +0.5 produced the same bounds, triangle
count, component count, and effectively the same volume. A repeated baseline
showed comparable run-to-run surface variation. This field therefore cannot be
presented as physical solidification.

The Mesh Export **Shell size** control belongs to simplification. Its embedded
help states that simplification removes excluded pieces starting with the
smallest. It is not a wall-thickening operation.

An STL is only a boundary surface. A slicer decides infill and shell count. A
geometric solidify control must instead offset the occupied volume and then
reconstruct a new closed surface. That is a fabrication derivative, not a
native XenoDream edit. Keeping those artifacts separate preserves native
editability and prevents a repaired mesh from being mistaken for the source
model.

## Public types

```python
@dataclass(frozen=True, slots=True)
class SolidifySettings:
    amount_mm: Decimal
    voxel_mm: Decimal
    max_voxels: int = 30_000_000

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

def solidify_binary_stl(
    source: Path,
    destination: Path,
    settings: SolidifySettings,
) -> SolidifyReport: ...
```

## Runtime flow

1. Require a finite, closed input mesh without degenerate, boundary,
   non-manifold, or inconsistent-winding edges.
2. Voxelize the closed surface by parity ray casting at the caller-selected
   physical resolution.
3. Apply a Euclidean outward offset using a distance transform.
4. Pad the volume and reconstruct its 0.5 isosurface with marching cubes.
5. Write binary STL without altering the source.
6. Reinspect the result and reject it unless it is closed, edge-manifold,
   consistently wound, non-degenerate, and has nonzero volume.

The first version may accept multiple closed input components because the
operation is specifically useful for merging nearby parts. Its report must not
claim that a surviving disconnected component is supported or printable.

## Module ownership

- `solidify.py`: settings, voxelization, offset, isosurface reconstruction,
  binary-STL writing, and validation.
- `mesh.py`: unchanged source-of-truth inspection for binary STL.
- `cli.py`: argument parsing, no-overwrite boundary, and JSON report.
- `workspace.py`: unchanged in this increment. Later revisions may attach a
  derived mesh report to a native revision without storing the mesh as native
  model state.

## Alternatives considered

### Map a `solidify` slider to Relative Density

Rejected. The static field mapping is real, but the controlled geometry test
does not show useful thickening. This would be a semantic guess.

### Inflate every native object scale and contract positions

Rejected as the primary operation. It can increase overlap in some scenes but
does not thicken features within one object, depends on composition, and can
be cancelled by maximum-dimension export scaling.

### Store only a solidity preference in workspace metadata

Deferred. A preference that changes no model or mesh would invite false claims.
Process-specific infill and wall controls belong in a later slicer profile.

### Modify the existing STL in place

Rejected. Source preservation and side-by-side validation are required.

## Limits and failure modes

- Fidelity is bounded by `voxel-mm`; details near that size may disappear.
- The outward offset changes overall dimensions. A later command may fit the
  result to the build volume, but solidification itself must not silently scale.
- Solidification can merge intended gaps and cavities.
- Passing edge-manifold checks does not establish self-intersection freedom,
  minimum thickness, supportability, or fabrication suitability.
- The scientific Python backend is optional and must fail clearly when absent.
- Grid allocation is checked before allocation to prevent accidental memory
  exhaustion.

## Red-flag screen

- No boolean feature flag or mode branch is added to the native compiler.
- No XenoDream field is assigned an undocumented meaning.
- Source and destination are distinct and overwrite is refused.
- Physical units are explicit at the API boundary.
- The result type records both source and derived mesh evidence.
- Validation is a postcondition, not an optimistic label.
