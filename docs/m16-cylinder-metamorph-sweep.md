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

## Current execution boundary

The current Codex filesystem sandbox blocks writes to
`Documents\XenoDreamX`. XenoDream always writes its batch STL there before the
runner moves it into the experiment directory. Automated diagnostic runs
therefore reached XenoDream batch evaluation but stopped at the protected file
write. Source hashes remained unchanged and the runner cleaned up every owned
process. This is an environment restriction, not native model rejection.

Run the campaign once from a normal PowerShell session at the repository root:

```powershell
python scripts\sweep_metamorph_mesh.py `
  experiments\metamorph-sweeps\cylinder-isolated-v1.json `
  output\cylinder-isolated-user-v1 `
  --attempts 2 `
  --timeout-seconds 180 `
  --stl-max-dimension-mm 120 `
  --mesh-size-percent 40
```

No manual XenoDream interaction is expected. The application may appear while
each case runs. Do not edit or save the model during the campaign.

## Acceptance requirements

The command must exit with code 0. The final
`output\cylinder-isolated-user-v1\summary.json` must report:

- `complete: true`
- empty `missing_jobs` and `missing_controls`
- two successful baseline reports
- one successful report for each of the eight cases
- unchanged native source hashes in every report
- cleanup confirmation for every owned XenoDream process

`all_basic_topology_valid` is not an acceptance requirement for this
investigation. `Closed Ends=None`, partial arcs, or other controls may produce
open geometry. Those failures are measurements used to exclude unsafe profiles.
No result becomes a normal mutation profile until its report shows useful
geometric change and the required topology checks pass.
