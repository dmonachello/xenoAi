# Bounded Group3 membership

XenoSculpt can place `Cube2` into the exact `Group3` family created by
`project add-empty-group`. This is a closed XDX 1.220 operation, not a general
reparenting API.

```powershell
xenosculpt project group-cube2 sculpture.xsp `
  --profile stretch-x-20 --message "group and stretch Cube2"
```

Two measured profiles are available:

- `grouped` sets `Cube2.GroupID=2` and the Group3 scale to `50 50 50`.
- `stretch-x-20` sets `Cube2.GroupID=2` and the Group3 scale to `60 50 50`.

The writer admits only the exact `Group1`, `Cube2`, `Group3` scene. It changes
the Cube's literal `GroupID` plus the three group-scale tokens and audits every
other record byte. Repeating the same profile is a no-op revision.

Native evidence separates membership from coincidence. A 100/100/100 Group3
scale did not change the ungrouped Cube mesh. With `GroupID=2`, the `grouped`
and `stretch-x-20` profiles both evaluated successfully; the X-stretch changed
the measured dimensions from approximately 121.8 mm on every axis to
122.85 × 102.53 × 102.53 mm. A 100/50/50 grouped trial remained actively
computing through the preview timeout, so it is deliberately not exposed.

This command does not support arbitrary names, multiple children, nested
groups, ungrouping, moving between groups, or free-form group transforms. It
requires fresh native validation and never claims fabrication suitability.
