# X-rotation experiment 007

## Provenance

The user supplied `cube_base.xxp` and `cube_x_rotation.xxp` in `output/` on
2026-10-15. The variant changed the selected `Cube2` X Rotation from 0 to 30.
Both files were copied here without modification. `SHA256SUMS` records their
hashes.

The supplied screenshot shows XenoDream X with `Cube2` selected, Rotation
values `30, 0, 0`, and visibly rotated cube geometry.

## Static comparison

The files differ in exactly one token:

```text
section: Holon\1
key: Transform
token index: 6
base: 0.00000
variant: 30.00000
```

No other key, value, ordering, or line-ending change was found. The variant is
one byte longer because `30.00000` has one more character than `0.00000`.

Both files declare XenoDream X 1.220 and contain a `Holon\1` with `Type=1` and
`Name=Cube2`.

## Experiment outcome

Verified in the tested context. `Holon\1.Transform` token 6 stores X Rotation
for this `Cube2` holon in XenoDream X 1.220. The saved token, selected controls,
and preview geometry all agree on the change from 0 to 30 degrees.
