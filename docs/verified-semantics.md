# Verified format semantics

This registry separates persisted file-to-UI mappings from rendered geometry
effects. A mapping applies only to the tested version and context until another
experiment broadens its scope.

## Verified file-to-UI mappings

| Version | Context | Format location | UI meaning | Evidence | Status |
| --- | --- | --- | --- | --- | --- |
| 1.220 | `Holon\1`, `Type=1`, `Name=Sphere2` | `Transform` token 0 | X Scale | `experiments/scale-x/` | Verified write and readback: changing 50 to 25 changed only token 0, and the reopened Sphere2 panel displayed 25, 50, 50. |
| 1.220 | `Holon\1`, `Type=1`, `Name=Sphere2` | `Transform` token 1 | Y Scale | `experiments/scale-y/` | Verified write, readback, and preview: changing 50 to 25 changed token 1, and the reopened Sphere2 panel displayed 50, 25, 50. `SelectionSpots.0` also changed for an unknown reason. |
| 1.220 | `Holon\1`, `Type=1`, `Name=Sphere2` | `Transform` token 2 | Z Scale | `experiments/scale-z/` | Verified write, readback, and preview: changing 50 to 25 changed token 2, and the reopened Sphere2 panel displayed 50, 50, 25. `SelectionSpots.0` also changed for an unknown reason. |
| 1.220 | `Holon\1`, `Type=1`, `Name=Sphere2` | `Transform` token 9 | X Position | `experiments/position-x/` | Verified write and readback: changing 0 to 25 changed token 9, and the reopened Sphere2 panel displayed Position 25, 0, 0. `SelectionSpots.0` also changed for an unknown reason. |
| 1.220 | `Holon\1`, `Type=1`, `Name=Sphere2` | `Transform` token 10 | Y Position | `experiments/position-y/` | Verified write and readback: changing 0 to 25 changed token 10, and the reopened Sphere2 panel displayed Position 0, 25, 0. `SelectionSpots.0` also changed for an unknown reason. |
| 1.220 | `Holon\1`, `Type=1`, `Name=Sphere2` | `Transform` token 11 | Z Position | `experiments/position-z/` | Verified write and readback: changing 0 to 25 changed token 11, and the reopened Sphere2 panel displayed Position 0, 0, 25. `SelectionSpots.0` also changed for an unknown reason. |
| 1.220 | `Holon\1`, `Type=1`, `Name=Cube2` | `Transform` token 6 | X Rotation | `experiments/rotation-x/` | Verified clean write and readback: changing 0 to 30 changed only token 6, and the Cube2 panel displayed Rotation 30, 0, 0. |
| 1.220 | `Holon\1`, `Type=1`, `Name=Cube2` | `Transform` token 7 | Y Rotation | `experiments/rotation-y/` | Verified clean write and readback: changing 0 to 30 changed only token 7, and the selected Cube2 panel displayed Rotation 0, 30, 0. |
| 1.220 | `Holon\1`, `Type=1`, `Name=Cube2` | `Transform` token 8 | Z Rotation | `experiments/rotation-z/` | Verified clean write and readback: changing 0 to 30 changed only token 8, and the selected Cube2 panel displayed Rotation 0, 0, 30. |
| 1.220 | `Holon\0`, `Type=0`, `Name=Group1` | `Transform` token 7 | Y Rotation | `experiments/rotation-y-group/` | Verified clean write and readback: changing 0 to 30 changed only token 7, and the selected Group1 panel displayed Rotation 0, 30, 0. This does not verify the Cube2 child. |
| 1.220 | `Holon\0`, `Type=0`, `Name=Group1` | `Transform` token 8 | Z Rotation | `experiments/rotation-z-group/` | Verified clean write and readback: changing 0 to 30 changed only token 8, and the selected Group1 panel displayed Rotation 0, 0, 30. This does not verify the Cube2 child. |
| 1.220 | `Holon\0`, `Type=0`, `Name=Group1` | `GradDensity` | Color Density | `experiments/color-density-group/` | Verified clean write and readback: changing the UI control from 1.000 to 0.500 changed only this field. The rendering calculation remains undocumented. |
| 1.220 | `Holon\1`, `Type=1`, `Name=Cube2` | `GradDensity` | Color Density | `experiments/color-density/` | Verified clean write and readback: changing the UI control from 1.000 to 0.500 changed only this field. The rendering calculation remains undocumented. |
| 1.220 | `Holon\1\MM\0`, parent `Name=Cube2`, record `Style=5` | `Pars` token 0 | Cube Face Warp | `experiments/metamorph-face-warp/` | Verified clean write and readback: changing Face Warp from 0.00 to 0.25 changed only token 0. The deformation formula and other style codes remain undocumented. |
| 1.220 | generated `Holon\1`, `Type=1`, `Name=Cube2` | `Transform` tokens 0, 1, 2 | X, Y, Z Scale | `experiments/m3-generated-elongated-cube/` | Generated Scale 25, 50, 100 opened and rendered correctly. XenoDream resaved the project without byte changes. |

The first three transform tokens are now verified as X, Y, and Z Scale for the
tested sphere context.

Transform tokens 9 through 11 are now verified as X, Y, and Z Position at the
file and UI levels for the tested sphere context.

Transform token 6 is verified as X Rotation for the tested cube context.

Transform token 7 is independently verified as Y Rotation in the tested cube
and group contexts.

Transform token 8 is verified as Z Rotation for the tested group context. Its
meaning on a constructor holon is independently verified by the cube test.

Transform tokens 6 through 8 are now verified as X, Y, and Z Rotation for the
tested cube context.

`GradDensity` is independently verified as the Color Density field in the
tested cube and group contexts. Its rendering calculation remains
undocumented.

`Pars` token meanings depend on the metamorph context. Token 0 is verified as
Face Warp only for the tested Cube metamorph record with `Style=5`.

## Verified structure relationships

| Version | Observation | Evidence | Status |
| --- | --- | --- | --- |
| 1.220 | Adding empty Group3 changed `Header.NumHolons` from 2 to 3 and added `Holon\2` with `ID=2`, `GroupID=2`, `Type=0`, and `Name=Group3`. | `experiments/group-creation/` | Verified for the tested save. The two existing holons remained unchanged. |
| 1.220 | Cube2 has `GroupID=0` and appears under Group1, whose `ID=0`. Empty Group3 has `ID=2`, `GroupID=2`, and appears separately. | `experiments/group-creation/` | Supports child `GroupID` matching the containing group `ID`; broader hierarchy behavior remains provisional. |
| 1.220 | A project with Group1 and Cube2, Cube3, and Cube4 uses `NumHolons=4`; sibling IDs are 1, 2, and 3, each has `GroupID=0`, `Type=1`, and an adjacent `MM\0` block. | `experiments/three-cube-positions/` | Verified for this three-sibling save. Arbitrary counts and naming rules remain unproven. |

## Rendered geometry effects

| Version | Context | Format location | Effect | Evidence | Status |
| --- | --- | --- | --- | --- | --- |
| 1.220 | `Holon\1`, `Type=1`, `Name=Sphere2` | `Transform` token 0, changed from 50 to 25 | Reduces X Scale of the sphere | `experiments/scale-x/` | Verified after save, reopen, UI readback, and render observation. Selection changed only the white/yellow viewport highlight. |
| 1.220 | `Holon\1`, `Type=1`, `Name=Sphere2` | `Transform` token 1, changed from 50 to 25 | Reduces Y Scale of the sphere | `experiments/scale-y/` | Verified by the saved token, selected Sphere2 controls, and flattened preview geometry. |
| 1.220 | `Holon\1`, `Type=1`, `Name=Sphere2` | `Transform` token 2, changed from 50 to 25 | Reduces Z Scale of the sphere | `experiments/scale-z/` | Verified by the saved token, selected Sphere2 controls, and scaled preview geometry. |
| 1.220 | `Holon\1`, `Type=1`, `Name=Sphere2` | `Transform` token 9, changed from 0 to 25 | Moves the sphere along X | `experiments/position-x/` | Verified by the saved token, selected Sphere2 controls, and displaced preview geometry. |
| 1.220 | `Holon\1`, `Type=1`, `Name=Sphere2` | `Transform` token 10, changed from 0 to 25 | Moves the sphere along Y | `experiments/position-y/` | Verified by the saved token, selected Sphere2 controls, and displaced preview geometry. |
| 1.220 | `Holon\1`, `Type=1`, `Name=Sphere2` | `Transform` token 11, changed from 0 to 25 | Moves the sphere along Z | `experiments/position-z/` | File and UI mapping verified. Front-view preview is consistent with a depth change; no quantitative depth check was made. |
| 1.220 | `Holon\1`, `Type=1`, `Name=Cube2` | `Transform` token 6, changed from 0 to 30 | Rotates the cube around X | `experiments/rotation-x/` | Verified by the clean saved delta, selected Cube2 controls, and visibly rotated preview geometry. |
| 1.220 | `Holon\1`, `Type=1`, `Name=Cube2` | `Transform` token 7, changed from 0 to 30 | Rotates the cube around Y | `experiments/rotation-y/` | Verified by the clean saved delta, selected Cube2 controls, and visibly rotated preview geometry. |
| 1.220 | `Holon\1`, `Type=1`, `Name=Cube2` | `Transform` token 8, changed from 0 to 30 | Rotates the cube around Z | `experiments/rotation-z/` | Verified by the clean saved delta, selected Cube2 controls, and visibly rotated front-view geometry. |
| 1.220 | `Holon\0`, `Type=0`, `Name=Group1` | `Transform` token 7, changed from 0 to 30 | Rotates the group around Y | `experiments/rotation-y-group/` | File and UI mapping verified. The preview is consistent with a Y rotation, but no independent geometry measurement was made. |
| 1.220 | `Holon\0`, `Type=0`, `Name=Group1` | `Transform` token 8, changed from 0 to 30 | Rotates the group around Z | `experiments/rotation-z-group/` | Verified by the clean saved delta, selected Group1 controls, and visibly rotated front-view geometry. |
