# XenoDream metamorph evaluators and native mesh probes

## Result

Static analysis and isolated native exports now connect the recovered Sphere
and Cube parameter descriptors to evaluated three-dimensional geometry.

The class records for Sphere and Cube contain operation-specific setup and
field-evaluation routines. Sphere setup at `0x5bea08` reads all twelve stored
parameter slots. Cube setup at `0x5c0784` reads all nine stored parameter
slots. Their corresponding evaluators at `0x5be17c` and `0x5bff60` consume
point coordinates and parameter-derived state while calculating the operation
field. This confirms that the indexed descriptors recovered in R027 are not
only UI metadata: every stored slot is part of the native evaluator input.

The exact formulas and parameter interactions are not yet recovered. The
static result authorizes controlled probes, not unrestricted mutation.

## Cross-validation

Relationship: **CONFIRMS + EXTENDS**.

- It confirms R027's persisted parameter counts and indexes: the Sphere setup
  reads slots 0 through 11, while the Cube setup reads slots 0 through 8.
- It extends R027 by locating constructor-specific setup and point-field
  evaluation code.
- It confirms the user-observed Sphere Ovoid setting through a controlled
  native export. Changing only `Holon\1\MM\0.Pars` token 3 from `0.00000` to
  `2.80000` changed the mesh from approximately 95.9 x 95.9 x 95.9 mm to
  39.9 x 95.0 x 39.9 mm.
- No contradiction with accepted XDX files, the descriptor registry, or the
  previous Face Warp experiment was found.

## Controlled native probes

`scripts/probe_metamorph_mesh.py` prepares one-token variants and refuses any
unintended structural difference. It accepts only a descriptor name or index
from the hash-pinned XDX 1.220 registry, validates the native range and
precision, preserves the existing token spelling, and verifies an exact parser
round trip. Its summarizer reconciles each variant by SHA-256 with an isolated
native-export report.

At 100 mm maximum size and 25 percent mesh size:

| Probe | Dimensions (mm) | Triangles | Volume | Components | Boundary / non-manifold edges |
| --- | --- | ---: | ---: | ---: | ---: |
| Sphere baseline A | 95.895 x 95.905 x 95.884 | 21,662 | 461,614.010 | 1 | 0 / 0 |
| Sphere baseline B | 95.895 x 95.905 x 95.898 | 21,662 | 461,614.042 | 1 | 0 / 0 |
| Warp +5 | 95.891 x 95.881 x 95.898 | 21,686 | 462,012.339 | 1 | 0 / 0 |
| Warp -5 | 95.891 x 95.903 x 95.891 | 21,686 | 462,014.189 | 1 | 0 / 0 |
| Ovoid +2.8 | 39.884 x 95.011 x 39.880 | 20,832 | 79,187.581 | 1 | 0 / 0 |

The repeated baseline varied by zero triangles, 0.0315 volume units, and at
most 0.0137 mm in one dimension. Both Warp results and the Ovoid result exceed
that observed variation. Ovoid provides the first strong automated evidence
that a newly recovered Sphere token drives the expected kind of procedural
shape change.

## Scope and implications

These exports establish native acceptance, evaluation into 3D geometry, and
the reported basic mesh predicates for these specific samples. They do not
establish self-intersection freedom, minimum wall thickness, overhang safety,
process tolerances, or fabrication suitability. `printable` therefore remains
false.

The generator should next add an evidence-gated metamorph mutation layer that
uses the recovered descriptor domains, while continuing to require native
mesh evaluation and geometry scoring for proposed mutations. Broader creative
search should start with Sphere Ovoid and other parameters that produce large,
connected changes, then combine them only after isolated and interaction
probes establish useful envelopes.

