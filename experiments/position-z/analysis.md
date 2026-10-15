# Z-position experiment 006

## Provenance

The user supplied `sphere_z_position.xxp` in `output/` on 2026-10-15 after
starting from `sphere_base.xxp` and changing the selected `Sphere2` Z Position
from 0 to 25. Both files were copied here without modification. `SHA256SUMS`
records their hashes.

The supplied screenshot shows XenoDream X with `Sphere2` selected and Position
values `0, 0, 25`. In Front view, Z is a depth-axis change rather than a simple
lateral displacement.

## Static comparison

The variant has the same 194 CRLF-terminated records, 15 sections, and 164
key/value records as the base. Two fields differ:

```text
section: Holon\1
key: Transform
token index: 11
base: 0.00000
variant: 25.00000

section: SelectionSpots
key: 0
base: 3 25 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25
variant: 3 1 1
```

The variant is 3,401 bytes, 64 bytes shorter than the 3,465-byte base.

## Experiment outcome

Verified at the file and UI levels. `Holon\1.Transform` token 11 stores Z
Position for this `Sphere2` holon in XenoDream X 1.220. The saved token and
reopened Position controls agree on the change from 0 to 25. The preview is
consistent with the depth-axis change, but this experiment did not measure
screen-space size or camera distance.

`SelectionSpots.0` again changed to `3 1 1`. Its meaning remains unknown.
