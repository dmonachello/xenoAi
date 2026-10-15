# Y-scale experiment 002

## Provenance

The user supplied `sphere_y_scale.xxp` in `output/` on 2026-10-15 after
starting from `sphere_base.xxp` and changing the selected `Sphere2` Y Scale
from 50 to 25. Both files were copied here without modification. `SHA256SUMS`
records their hashes.

The supplied screenshot shows XenoDream X with `Sphere2` selected, Scale values
`50, 25, 50`, and the preview geometry flattened on the changed axis.

## Static comparison

Both files declare `Program=XDX`, `Progversion=1.220`, and `NumHolons=2`. Each
has 194 CRLF-terminated records, 15 sections, and 164 key/value records.

Two fields differ:

```text
section: Holon\1
key: Transform
token index: 1
base: 50.00000
variant: 25.00000

section: SelectionSpots
key: 0
base: 3 25 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25
variant: 3 1 1
```

The variant is 3,400 bytes, 65 bytes shorter than the 3,465-byte base because
the `SelectionSpots.0` value is shorter. Its meaning and reason for changing
are not established by this experiment.

## Experiment outcome

Verified in the tested context. For the `Sphere2` holon in XenoDream X 1.220,
`Holon\1.Transform` token 1 stores Y Scale. The controlled UI value, saved
token, reopened UI value, and preview geometry all agree on the change from 50
to 25.

The unrelated `SelectionSpots.0` delta means the pair is not a strict
single-field diff. It does not obscure the Y Scale mapping because the transform
token changed independently and matches the displayed control exactly.
