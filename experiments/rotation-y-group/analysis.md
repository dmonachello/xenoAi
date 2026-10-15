# Group Y-rotation experiment 008

## Provenance

The user supplied `cube_y_rotation.xxp` in `output/` on 2026-10-15 after
starting from `cube_base.xxp`. Both files were copied here without
modification. `SHA256SUMS` records their hashes.

The filename refers to the cube, but the supplied screenshot shows `Group1`
selected. Its controls display Rotation values `0, 30, 0`. The cube child is
not selected.

## Static comparison

The files differ in exactly one token:

```text
section: Holon\0
key: Transform
token index: 7
base: 0.00000
variant: 30.00000
```

No token in `Holon\1`, the `Cube2` child, changed. No other key, value,
ordering, or line-ending change was found. The variant is one byte longer
because `30.00000` has one more character than `0.00000`.

Both files declare XenoDream X 1.220. `Holon\0` has `Type=0` and
`Name=Group1`.

## Experiment outcome

Verified for the tested group context. `Holon\0.Transform` token 7 stores Y
Rotation for `Group1` in this XenoDream X 1.220 file. The clean file delta and
the selected group controls agree.

This sample does not verify Y Rotation on the `Cube2` child. That requires a
new save with `Cube2` selected before changing the control.
