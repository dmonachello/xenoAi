# XenoDream scene descriptions

`project describe` reports the XenoDream scene stored in one workspace
revision. The command is read-only. It verifies the artifact hash before it
parses the `.xxp` bytes.

## Command

```powershell
xxp project describe WORKSPACE [--ref REF]
```

`REF` defaults to `HEAD`. You can supply a branch name or a revision ID. The
command resolves the ref without checking it out.

The `xenosculpt project describe` command uses the same implementation.

## Output

The command writes one `xenosculpt-xenodream-scene/v1` JSON object. The object
contains these fields:

- `binding`: The resolved revision ID and artifact SHA-256.
- `xdx_version`: The format version from `Header.Progversion`.
- `declared_holon_count`: The saved `Header.NumHolons` value.
- `nodes`: Holon sections in physical file order.
- `diagnostics`: Structural facts that prevent or limit interpretation.

Each node keeps separate values for the persisted `ID`, the numeric
`Holon\N` suffix, the repeated-section occurrence, and the physical ordinal.
The saved `GroupID` is reported as `group_id`. XenoSculpt does not treat every
saved group reference as a proven parent relationship.

Known transform values use decimal strings. Metamorph parameters retain their
native token text. Unknown type codes, styles, and parameters remain in the
description where the parser can associate them with a node.

## Edit capabilities

`allowed_operations` lists operations supported by the exact node record. The
current capability IDs are:

- `set-scale-v1`
- `set-rotation-v1`
- `set-position-v1`
- `set-color-density-v1`
- `set-face-warp-v1`
- `apply-sphere-profile-v1`
- `apply-cylinder-profile-v1`

These strings are stable capability IDs. They are not proof that XenoDream has
evaluated the current revision. Use `project validate` to attach native mesh
evidence.

`write_blockers` lists structural issues found on a node. An issue can block
one operation without blocking an independent operation. Treat
`allowed_operations` as the authority. For example, a duplicate name blocks
all name-targeted writes. An unsupported constructor stays visible but has no
write capability.

Only exact XDX 1.220 record shapes receive write capabilities. Older project
versions remain available for inspection but do not receive XDX 1.220 write
permissions.

## Mutation behavior

The mutation engine uses the same constructor recognition as the scene
description. A supported Cube or Sphere can be edited when an unrelated,
unsupported Type 1 node exists in the same project. The mutation changes only
the authorized target fields. Scene-wide row and seeded-variation operations
still require every affected object to use a supported record shape.

The command does not add, delete, duplicate, reorder, or reparent nodes. Those
operations require more evidence about XDX identity allocation and section
ordering.
