# X-position experiment 004

## Provenance

The user supplied `sphere_x_position.xxp` in `output/` on 2026-10-15 after
being asked to start from `sphere_base.xxp` and change only the selected
`Sphere2` X Position from 0 to 25. Both files were copied here without
modification. `SHA256SUMS` records their hashes.

No screenshot or explicit reopen/render result accompanied this file.

## Static comparison

The variant has the same 194 CRLF-terminated records, 15 sections, and 164
key/value records as the base. Two fields differ:

```text
section: Holon\1
key: Transform
token index: 9
base: 0.00000
variant: 25.00000

section: SelectionSpots
key: 0
base: 3 25 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25
variant: 3 1 1
```

The variant is 3,401 bytes, 64 bytes shorter than the 3,465-byte base. The
longer transform token adds one byte while the shorter selection-spots value
removes 65 bytes.

## Experiment outcome

The controlled-save correlation supports `Holon\1.Transform` token 9 as X
Position for this `Sphere2` holon in XenoDream X 1.220. Application readback
and rendered movement remain unverified.

`SelectionSpots.0` changed to the same value found in the Y-scale and Z-scale
experiments. Its meaning remains unknown.
