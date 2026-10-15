# Verified format semantics

This registry contains mappings backed by controlled UI experiments and an
XenoDream reopen/render check. No mappings currently meet that bar.

## Inconclusive candidates

| Version | Context | Format location | Candidate UI meaning | Evidence | Status |
| --- | --- | --- | --- | --- | --- |
| 1.220 | `Holon\1`, `Type=1`, `Name=Sphere2` | `Transform` token 0 | X Scale | `experiments/scale-x/` | The UI save changed 50 to 25 at this token, but the reopened file rendered as before. Child-holon readback values have not been observed. |

No transform-token mapping has yet been verified for rendered geometry.
