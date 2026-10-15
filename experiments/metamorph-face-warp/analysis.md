# Cube Face Warp experiment 014

## Provenance

The user supplied `cube_face_warp.xxp` in `output/` on 2026-10-15 after
starting from `cube_base.xxp`. Both files were copied here without
modification. `SHA256SUMS` records their hashes.

The supplied screenshot shows `Cube2` selected. The Active Holon name is
`Cube2`, the active metamorph is `Cube`, and its Face Warp control displays
`0.25`.

## Static comparison

The files differ in exactly one token:

```text
section: Holon\1\MM\0
key: Pars
token index: 0
base: 0.0000
variant: 0.2500
```

No other key, value, ordering, or line-ending change was found. The
metamorph record also contains `Style=5`; this experiment does not establish a
universal meaning for that numeric code.

Both files declare XenoDream X 1.220. Parent section `Holon\1` has `Type=1`
and `Name=Cube2`.

## Experiment outcome

Verified at the file and UI levels for the tested Cube metamorph.
`Holon\1\MM\0.Pars` token 0 stores the value displayed by the Face Warp
control. The sample does not establish the deformation formula or the token's
meaning for other metamorph styles.
