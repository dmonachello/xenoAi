# X-scale experiment 001

## Provenance

The user supplied both files in `output/` on 2026-10-15. They were copied into
this directory without modification. `SHA256SUMS` records their hashes.

The filenames imply a base sphere and an X-scale variant. The user has not yet
confirmed the exact displayed values, whether any other UI action occurred, or
whether both saved files reopened and rendered successfully. Those facts remain
open.

## Static comparison

Both files have these observed properties:

- 3,465 bytes and 194 CRLF-terminated records.
- Header `Program=XDX`, `Progversion=1.220`, and `NumHolons=2`.
- 15 sections and 164 key/value records.
- `Holon\0` has `ID=0`, `GroupID=0`, `Type=0`, and `Name=Group1`.
- `Holon\1` has `ID=1`, `GroupID=0`, `Type=1`, and `Name=Sphere2`.

The files differ at only two adjacent byte offsets because one fixed-width
numeric token changed:

```text
section: Holon\1
key: Transform
token index: 0
base: 50.00000
variant: 25.00000
byte offsets changed: 756 and 757
```

Every other byte matches. The unchanged serializer round-trips both files
byte-for-byte.

## Finding

The pair proves that this save operation changed only token 0 of
`Holon\1.Transform`, from `50.00000` to `25.00000`. If the user confirms that
the only UI edit was changing X Scale from 50 to 25, the pair establishes a
direct mapping for XenoDream X 1.220:

```text
Holon.Transform token 0 = displayed X Scale
```

That mapping is not yet generalized to other versions, holon types, groups, or
metamorph transforms.

## Required confirmation

1. Was X Scale the only setting changed?
2. Were the displayed values exactly 50 and 25?
3. Did both files reopen without warnings and render with the expected X-axis
   size difference?
