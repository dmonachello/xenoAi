# Verified format semantics

This registry contains mappings backed by controlled UI experiments and an
XenoDream reopen/render check. A mapping applies only to the tested program
version and context until another experiment broadens its scope.

| Version | Context | Format location | UI meaning | Evidence | Status |
| --- | --- | --- | --- | --- | --- |
| 1.220 | `Holon\1`, `Type=1`, `Name=Sphere2` | `Transform` token 0 | X Scale | `experiments/scale-x/` | Verified: 50 to 25, only two corresponding bytes changed, both files reopened and rendered correctly |

No transform-token mapping has yet been verified for groups, iterators,
metamorph transforms, or XenoDream X 1.007.
