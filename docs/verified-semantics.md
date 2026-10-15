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

The first three transform tokens are now verified as X, Y, and Z Scale for the
tested sphere context.

Transform tokens 9 through 11 are now verified as X, Y, and Z Position at the
file and UI levels for the tested sphere context.

Transform token 6 is verified as X Rotation for the tested cube context.

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
