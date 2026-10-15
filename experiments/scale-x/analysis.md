# X-scale experiment 001

## Provenance

The user supplied both files in `output/` on 2026-10-15. They were copied into
this directory without modification. `SHA256SUMS` records their hashes.

On 2026-10-15, the user initially confirmed the requested controls, then
corrected the application result. The first screenshot after reopen showed
`Group1` selected with Scale values `100, 100, 100`. A second screenshot with
`Sphere2` selected showed Scale values `25, 50, 50`. This confirms that the
saved token persisted and appeared in the intended child holon's X Scale UI.

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

The pair proves that the save operation changed only token 0 of
`Holon\1.Transform`, from `50.00000` to `25.00000`. The selected-child
screenshot proves that XenoDream 1.220 reads that token back as `Sphere2` X
Scale. It does not yet prove that the reopened render changed shape.

```text
Holon.Transform token 0 = displayed X Scale
```

That mapping is not yet generalized to other versions, holon types, groups, or
metamorph transforms.

## Experiment outcome

Partially verified. The first three `Holon\1.Transform` tokens match the
displayed `Sphere2` Scale triplet in this observed file. The controlled change
verifies token 0 as persisted X Scale 25 after reopening. Tokens 1 and 2 remain
candidates for Y and Z Scale. The rendered geometry effect remains open because
the user previously reported that the variant looked unchanged.
