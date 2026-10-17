# Add Cubes to a bounded XenoDream composition

Use `project add-cube` to append one Cube to the two exact XDX 1.220 scene
shapes that XenoSculpt can currently compose safely. The operation creates a
normal workspace revision; it does not edit the source artifact in place.

## Start from an admitted project

The active revision must contain a flat `Group1` with either:

- `Cube2`; or
- `Cube2` followed by `Cube3`.

The project must retain the canonical XDX 1.220 record sequence, IDs, names,
group references, and one adjacent `MM\0` constructor section per Cube.
Previously verified edits to Cube scale, rotation, position, gradient density,
or face warp are admitted. Extra nodes, extra or reordered sections, changed
unverified fields, malformed records, and a scene that already contains three
Cubes are rejected before a revision is written.

Create a workspace from the one-Cube generator when you need a known starting
point:

```powershell
xenosculpt generate-cube .\sculpture.xxp
xenosculpt project init .\sculpture.xsp .\sculpture.xxp
```

## Add a Cube

Pass an exact position with at most five decimal places:

```powershell
xenosculpt project add-cube .\sculpture.xsp `
  --position 75 0 0 `
  --message "add the right cube"
```

The one-to-two transition allocates `Holon\2`, `ID=2`, and `Name=Cube3`.
The two-to-three transition allocates `Holon\3`, `ID=3`, and `Name=Cube4`.
Both additions use `GroupID=0` and the verified Cube constructor. Names, IDs,
group placement, and constructor settings are not configurable.

The result reports the allocated identity, ordinary key-level `differences`,
and two `structural_changes`: one for the added Holon section and one for its
adjacent `MM\0` section. The record counts partition the complete inserted
span. XenoSculpt changes `Header.NumHolons` and preserves every other
pre-existing record byte.

## Inspect and validate the revision

Describe the active revision before opening it in XenoDream:

```powershell
xenosculpt project describe .\sculpture.xsp
```

Then run the native validation workflow at a low discovery density:

```powershell
xenosculpt project validate .\sculpture.xsp `
  --stl-max-dimension-mm 120 `
  --mesh-size-percent 10 `
  --timeout-seconds 180
```

An added Cube is marked `native_validation_required=true` and
`fabrication_suitable=false` until external validation establishes more. The
validator writes the requested maximum dimension and mesh density to
XenoDream's shared preferences. Those values persist after validation and are
not restored, so close other XenoDream windows before the run.

Separated Cubes currently make `project validate` exit with status 1 because
`basic_mesh_valid` requires exactly one connected component. Do not treat that
exit status alone as a native-load failure. In the validation JSON,
`outcome="succeeded"`, `native_model_valid=true`, and `evaluates_to_3d=true`
establish that XenoDream accepted and evaluated the native model. A false
`basic_mesh_valid` still prevents a fabrication-suitability claim.

Export the active native project when the result is acceptable:

```powershell
xenosculpt project export .\sculpture.xsp .\sculpture-with-cube.xxp
```

This command does not support Sphere addition, duplication, deletion,
reordering, group creation, reparenting, custom identities, or a fourth Cube.

## Retained native evidence

The packaged M25 command was tested from a non-default Cube2 revision. It
added a separated Cube3, and XenoDream X 1.220 loaded and evaluated the exact
revision at 120 mm and 10% mesh detail. The retained 3,578-triangle STL had two
expected disconnected components and no boundary, non-manifold, inconsistent-
winding, or degenerate-triangle errors. The current basic mesh predicate is
false because it deliberately requires one connected component. This result
establishes native evaluation of the bounded append; it does not establish
fabrication suitability. See
[`m25-add-cube-native-validation.json`](../evidence/runtime/m25-add-cube-native-validation.json).
