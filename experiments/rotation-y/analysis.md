# Cube Y-rotation experiment 010

## Provenance

The user supplied `cube_y_rotation2.xxp` in `output/` on 2026-10-15 after
starting from `cube_base.xxp`. Both files were copied here without
modification. `SHA256SUMS` records their hashes.

The supplied screenshot shows `Cube2` selected. The Active Holon name is
`Cube2`, and its controls display Rotation values `0, 30, 0`.

## Static comparison

The files differ in exactly one token:

```text
section: Holon\1
key: Transform
token index: 7
base: 0.00000
variant: 30.00000
```

No other key, value, ordering, or line-ending change was found. The variant is
one byte longer because `30.00000` has one more character than `0.00000`.

Both files declare XenoDream X 1.220. `Holon\1` has `Type=1` and
`Name=Cube2`.

## Experiment outcome

Verified in the tested context. `Holon\1.Transform` token 7 stores Y Rotation
for this `Cube2` holon in XenoDream X 1.220. The clean saved delta, selected
controls, and preview geometry agree on the change from 0 to 30 degrees.
