# Group Color Density experiment 012

## Provenance

The user supplied `cube_color_density.xxp` in `output/` on 2026-10-15 after
starting from `cube_base.xxp`. Both files were copied here without
modification. `SHA256SUMS` records their hashes.

The filename refers to the cube, but the supplied screenshot shows `Group1`
selected. The Active Holon name is `Group1`, and its Color Density control
displays `0.5`.

## Static comparison

The files differ in exactly one value:

```text
section: Holon\0
key: GradDensity
base: 1.000
variant: 0.500
```

No field in `Holon\1`, the `Cube2` child, changed. No other key, value,
ordering, or line-ending change was found.

Both files declare XenoDream X 1.220. `Holon\0` has `Type=0` and
`Name=Group1`.

## Experiment outcome

Verified at the file and UI levels for the tested group. `Holon\0` field
`GradDensity` stores the value displayed by the Group1 Color Density control.
The experiment does not establish the field's rendering calculation or its
scope on constructor holons.
