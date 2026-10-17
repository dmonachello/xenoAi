# M16 Cylinder metamorph sweep

## Purpose

This campaign measures the seven recovered Cylinder controls through native
XenoDream evaluation and STL inspection. It does not rely on a manually created
Cylinder project. The sweep runner calls `compile_cylinder()` for its baseline,
records the compiler profile and native hash, and changes only one persisted
`Pars` token per case.

The checked-in plan is
`experiments/metamorph-sweeps/cylinder-isolated-v1.json`. It contains two
baseline runs and eight cases selected from the executable descriptors and the
installed Cylinder presets:

- Length 3
- Arc 180
- Closed Ends None and Back
- Wedge Yes
- Spherical Yes
- Bevel Edges 2
- Bevel Back

Repeated values for one parameter are permitted only by sweep schema v3. Older
Sphere plans retain their duplicate-parameter rejection.

## Automated checks

Before XenoDream starts, the runner verifies the generated baseline operation,
XDX version, recovered descriptor schema, parameter domain, fixed-point
precision, one-token diff, and exact parser round trip. It writes a manifest
before execution and can resume after an interruption. An orphaned attempt
directory consumes its attempt number instead of being reused.

For every successful native export, the summary records triangle count,
dimensions, volume, connected components, boundary edges, non-manifold edges,
winding errors, and degenerate triangles. It compares each case with repeated
baseline measurements. The campaign never labels a result printable.

## Result

The 10 percent discovery sweep completed both baselines and seven of eight
mutation cases. Each completed case succeeded on its first attempt and produced
one connected mesh with zero detected boundary edges, non-manifold edges,
winding conflicts, or degenerate triangles. `Arc=180` remained active until the
120-second limit and produced no STL.

The two baselines each had 3,962 triangles and identical dimensions. Their
absolute-volume span was 0.1132 mm3. The stable baseline makes the larger case
deltas measurable at this discovery detail.

| Case | Impact | Triangle delta | Volume delta (mm3) | Dimensions (mm) |
| --- | ---: | ---: | ---: | --- |
| Length 3 | 1.008284 | -8 | -46,742.321 | 77.000 x 77.000 x 115.093 |
| Closed Ends None | 0.971018 | +506 | -565,727.660 | 113.790 x 113.790 x 57.307 |
| Closed Ends Back | 0.956727 | +2,152 | -557,401.625 | 113.790 x 113.790 x 57.308 |
| Wedge Yes | 0.321980 | +1,076 | -187,589.475 | 113.790 x 113.790 x 57.307 |
| Spherical Yes | 0.156352 | -30 | -91,092.583 | 114.200 x 114.188 x 51.528 |
| Bevel Edges 2 | 0.000390 | 0 | -227.186 | 113.790 x 113.790 x 57.309 |
| Bevel Back | 0.000001 | 0 | +0.402 | 113.790 x 113.790 x 57.309 |

`Bevel Back` was nearly inert because the baseline bevel amount was zero. M17
tests the selector with a nonzero amount. The large Closed Ends volume changes
still passed the current edge predicates, but those predicates do not establish
self-intersection freedom or usable wall thickness.

The compact evidence record is
`evidence/runtime/m16-cylinder-isolated-sweep-summary.json`.

## Reproduction

Run the campaign from a normal PowerShell session at the repository root:

```powershell
python scripts\sweep_metamorph_mesh.py `
  experiments\metamorph-sweeps\cylinder-isolated-v1.json `
  output\cylinder-isolated-preview-v1 `
  --attempts 1 `
  --timeout-seconds 120 `
  --stl-max-dimension-mm 120 `
  --mesh-size-percent 10
```

No manual XenoDream interaction is expected. The application may appear while
each case runs. Do not edit or save the model during the campaign.

## Validation level

The completed cases establish native acceptance, measurable geometry effects,
and the current basic mesh predicates at 10 percent detail. The sweep does not
establish self-intersection freedom, local thickness, support requirements,
tolerances, or fabrication suitability. `Arc=180` remains unresolved. Every
result therefore keeps `printable` false.
