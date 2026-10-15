# X-scale experiment 001

## Provenance

The user supplied both files in `output/` on 2026-10-15. They were copied into
this directory without modification. `SHA256SUMS` records their hashes.

On 2026-10-15, the user initially confirmed the requested controls, then
corrected the application result. The X Scale UI edit was from 50 to 25, but
the saved variant rendered as before when reopened. A screenshot after reopen
showed `Group1` selected with Scale values `100, 100, 100`. It did not show the
child `Sphere2` values.

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
`Holon\1.Transform`, from `50.00000` to `25.00000`. This is strong evidence
that the UI writes X Scale to that token for the tested holon. It does not yet
prove that XenoDream applies that token to the rendered sphere after reopening.

```text
Holon.Transform token 0 = displayed X Scale
```

That mapping is not yet generalized to other versions, holon types, groups, or
metamorph transforms.

## Experiment outcome

Inconclusive. The wire-field correlation is verified, but the geometry effect
is not. The screenshot shows the parent group's transform, so it cannot tell us
whether `Sphere2` read back as `25, 50, 50` or reset to `50, 50, 50`.

The next check must select `Sphere2` after separately reopening each file and
record its three Scale values. That distinguishes a retained-but-inactive
parameter from a value that XenoDream ignores or resets while loading.
