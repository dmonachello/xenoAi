# M7 seeded variation acceptance

Date: 2026-10-16

## Native project

The packaged `xenosculpt.exe` initialized a workspace from the accepted
Cube/Sphere row, applied `SeededVariation(seed=17, strength=0.5)`, and exported
`output/evolved_seed17.xxp`.

- native project SHA-256:
  `337cfc77944756e3167f4e5ba65ea9db395cc5820fdad47b09705c313e3aa446`
- size: 4,126 bytes
- operation recorded: `seeded-variation-v1`
- changed fields: Cube/Sphere transforms and Cube Face Warp only

Repeating the operation from the same bytes is covered by the deterministic
unit test. The structural diff gate rejects changes outside the verified
physical-form field set.

## Automated XenoDream evaluation

The supervised runner opened a disposable copy in XenoDream X 1.220 and
exported binary STL at 250 mm maximum dimension and 25 percent mesh size.
The process was job-owned and cleanup completed.

- outcome: succeeded
- elapsed time: 20.479 seconds
- triangles: 22,272
- measured dimensions: 239.835 × 146.081 × 158.745 mm
- connected components: 1
- boundary edges: 0
- non-manifold edges: 0
- inconsistent winding edges: 0
- degenerate triangles: 0
- signed volume: positive and nonzero
- STL SHA-256:
  `586215d5c597db2509b083cb9ef383fd0a1cd871c83a0546505b21350a67aae3`

The complete machine report is
`evidence/runtime/evolve-seed17-validation.json`.

This establishes native structural acceptance, successful 3D evaluation, and
basic closed edge-manifold mesh validity for this variation. It does not yet
establish self-intersection freedom, minimum feature thickness, support needs,
process tolerances, or fabrication suitability.
