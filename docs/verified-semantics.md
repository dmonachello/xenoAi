# Verified format semantics

This registry separates persisted file-to-UI mappings from rendered geometry
effects. A mapping applies only to the tested version and context until another
experiment broadens its scope.

## Verified file-to-UI mappings

| Version | Context | Format location | UI meaning | Evidence | Status |
| --- | --- | --- | --- | --- | --- |
| 1.220 | `Holon\1`, `Type=1`, `Name=Sphere2` | `Transform` token 0 | X Scale | `experiments/scale-x/` | Verified write and readback: changing 50 to 25 changed only token 0, and the reopened Sphere2 panel displayed 25, 50, 50. |

The screenshot also aligns tokens 1 and 2 with displayed Y Scale and Z Scale,
both at 50, but no controlled edit has isolated those tokens yet.

## Rendered geometry effects

No transform-token effect has yet been verified by a before-and-after render.
