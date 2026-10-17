# Fabrication assessments

`project assess` evaluates retained mesh evidence without changing the native
project or workspace `HEAD`. Each assessment identifies one revision, one
successful native validation, one STL hash, and one policy version.

## Run an assessment

Validate the active revision first:

```powershell
xxp project validate output/cylinder.xsp `
  --stl-max-dimension-mm 120 --mesh-size-percent 10
```

Then assess the retained mesh:

```powershell
xxp project assess output/cylinder.xsp
```

By default, the command uses the latest successful mesh-bearing validation for
`HEAD`. Use `--ref` to select another revision or branch. Use `--validation` to
select an exact validation for that revision:

```powershell
xxp project assess output/cylinder.xsp `
  --ref main `
  --validation 9ad033cc093e62917b011c7dba9a603b2f11532e57374955f2468cae86d47146
```

The command verifies the retained STL hash before it uses or creates a cached
assessment. Repeated requests with the same policy, revision, validation,
mesh, and constraints return the same assessment.
The workspace also recomputes cached assessment identities when it reads them.
It rejects cached results whose provenance disagrees with the database row.

## Read the result

The `workspace-constraints` version 1 policy reports five checks:

| Check | Current behavior |
| --- | --- |
| `basic-mesh` | Evaluates the existing topology predicate. |
| `build-volume` | Compares measured STL dimensions with each configured axis in the exported orientation. |
| `self-intersections` | Returns `not_evaluated`. No exact analyzer exists. |
| `minimum-feature` | Returns `not_evaluated` when configured. The constraint does not yet define a measurable thickness property. |
| `process` | Returns `not_evaluated` when configured. The stored value is a label, not a typed process profile. |

Each check has one of these statuses:

- `pass`: The implemented check passed.
- `fail`: The implemented check failed.
- `not_evaluated`: The policy requires evidence that XenoSculpt cannot measure.
- `not_applicable`: The optional workspace constraint is not configured.

One failed check produces the `fail` verdict. If no check fails and at least
one check is `not_evaluated`, the verdict is `incomplete`. Only a complete set
of passing required checks can produce `pass` and
`fabrication_suitable: true`.

Policy version 1 always reports `incomplete` or `fail`. It freezes the five
checks and the statuses they can produce. The exact self-intersection check is
required and remains `not_evaluated`. A future analyzer must use a new policy
version, which gives it a separate cache identity. Exit code `1` therefore
means the assessment correctly blocked fabrication approval.

## Build-volume scope

The build-volume check uses `StlReport.dimensions`, not the maximum dimension
requested from the XenoDream exporter. It permits translation inside the build
volume, but it does not search for a better rotation, pack multiple objects, or
rescale the mesh.

Passing this check means only that the exported orientation fits the recorded
axis limits. It does not establish minimum wall thickness, supportability,
tolerances, process compatibility, or successful fabrication.

## Retained evidence

Workspace schema version 3 stores assessments separately from native
validations. This separation keeps the original XenoDream observation intact
when a policy changes. Opening an older version 1 or version 2 workspace adds
the assessment table without changing revisions, validations, meshes, or
`HEAD`.

The packaged M20 smoke test assessed the user's retained 3,942-triangle bevel
mesh from a copied external workspace. `basic-mesh` passed,
`self-intersections` remained `not_evaluated`, the verdict was `incomplete`,
and `HEAD` did not change. The executable SHA-256 was
`1abddae8240f32d8de5bcc1d96c727dbe618706e20f37aa1f4c81675f2ac8ee6`.
