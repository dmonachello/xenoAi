# Cube Color Density experiment 013

## Provenance

The user supplied `cube_color_density2.xxp` in `output/` on 2026-10-15 after
starting from `cube_base.xxp`. Both files were copied here without
modification. `SHA256SUMS` records their hashes.

The supplied screenshot shows `Cube2` selected. The Active Holon name is
`Cube2`, and its Color Density control displays `0.5`.

## Static comparison

The files differ in exactly one value:

```text
section: Holon\1
key: GradDensity
base: 1.000
variant: 0.500
```

No other key, value, ordering, or line-ending change was found.

Both files declare XenoDream X 1.220. `Holon\1` has `Type=1` and
`Name=Cube2`.

## Experiment outcome

Verified at the file and UI levels for the tested cube. `Holon\1` field
`GradDensity` stores the value displayed by the Cube2 Color Density control.
The experiment does not establish the field's rendering calculation.
