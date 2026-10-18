# M27: bounded Sphere composition

`project add-sphere` appends `Sphere3` only to the verified flat
`Group1, Cube2` XDX 1.220 family.

```powershell
xenosculpt project add-sphere .\sculpture.xsp `
  --position 75 0 0 `
  --message "add right sphere"
```

The operation preserves admitted Cube transform, color-density, and Face Warp
edits. It inserts the exact Sphere block from the hash-pinned native-accepted
Cube/Sphere template, changes `Header.NumHolons`, and replaces only the new
Sphere position tokens. A reverse structural audit must reconstruct the entire
source byte-for-byte.

The command does not support Sphere-first scenes, repeated Spheres, adding a
Sphere after two Cubes, custom identities, grouping, duplication, removal,
reordering, or reparenting. Those operations need separate native evidence.

The result always requires fresh native validation and is not a fabrication
suitability claim. Use the managed profiles at one explicit physical maximum:

```powershell
xenosculpt project validate .\sculpture.xsp --profile preview --stl-max-dimension-mm 120
xenosculpt project validate .\sculpture.xsp --profile review --stl-max-dimension-mm 120
```

Separated objects can evaluate successfully in XenoDream while the shared
basic mesh predicate reports false because it requires one connected component.
Inspect `outcome`, `native_model_valid`, `evaluates_to_3d`, topology counters,
and `connected_components` separately. Fabrication suitability remains false.
