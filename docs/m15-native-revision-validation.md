# M15 native revision validation

## Outcome

`project validate` connects the existing revision workflow to the supervised
XenoDream X batch exporter. Validation is evidence about a revision, not a
model edit, so it neither creates a revision nor advances HEAD.

The workspace schema is version 2. Version 1 workspaces migrate transactionally
when opened. Each record identifies the revision, native executable hash,
export settings, complete runner report, and optional content-addressed STL.
Successful identical requests reuse their prior record and mesh.

## Acceptance

The first real command evaluated revision
`20f5c2f894c9af0c0504617b4eb2d2baa6fa7ef9cf290039ed4aad3c0f9896af`
from `output/my_sculpture.xsp`. XenoDream X 1.220 exported 89,156 triangles.
Independent inspection found one connected component, no boundary,
non-manifold, inconsistent-winding, or degenerate edges or triangles, and
nonzero signed volume. The native source and disposable copy retained SHA-256
`680beef3070184284151755f39e3dddf919dfe02d6a5f552399b0d662cd03616`.

This establishes native acceptance, 3D evaluation, and the current basic mesh
predicate for that revision. It does not establish minimum thickness,
self-intersection freedom, overhang suitability, tolerances, or successful
fabrication.
