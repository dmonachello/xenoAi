# M16 Cylinder metamorph campaign design

## Caller usage

The experiment plan names a generated constructor source and the exact recovered
parameters to test:

```json
{
  "schema": "xenosculpt-metamorph-sweep-plan/v3",
  "operation": "Cylinder",
  "source": {"kind": "generated", "constructor": "Cylinder"},
  "holon": 1,
  "baseline_replicates": 2,
  "cases": [
    {
      "id": "length-half",
      "parameter": "Length",
      "value": "0.5",
      "source": "REA descriptor R034"
    }
  ]
}
```

The existing runner remains the only command needed:

```powershell
python scripts/sweep_metamorph_mesh.py `
  experiments/metamorph-sweeps/cylinder-isolated-v1.json `
  output/cylinder-isolated-v1
```

It generates the baseline with `compile_cylinder()`, produces one-token native
variants through the recovered descriptor registry, runs each file in an
isolated XenoDream process, and writes one resumable summary.

## Candidate A: generated sources in the generic runner

Add schema v3 and a private `_source()` resolver to
`scripts/sweep_metamorph_mesh.py`:

```python
def _source(plan_path: Path, source: str | dict[str, str]) -> Source:
    ...

@dataclass(frozen=True)
class Source:
    data: bytes
    identity: dict[str, str]
```

String sources retain the existing file behavior. The only initial generated
source is the exact `Cylinder` constructor. The manifest records its compiler
profile and hash. `load_plan()` accepts Sphere or Cylinder and later verifies
that the selected holon's registry operation matches the plan operation.

This keeps experiment lifecycle policy in one runner and keeps native record
construction in the generator. It adds no product mutation permission.

## Candidate B: a dedicated Cylinder campaign script

Create `scripts/sweep_cylinder_mesh.py`. It would call `compile_cylinder()`,
write a temporary source, then invoke `run_sweep()` with a generated plan.

This avoids changing the established plan schema, but it duplicates plan
creation and makes the generic runner depend on a temporary file whose identity
is hidden from the checked-in experiment. Torus and Pipe would each need
another wrapper. I reject this candidate.

## Selected design

Use candidate A. The public experiment command stays unchanged, and the plan
states whether its source is a retained file or a generated constructor. The
runner records the generated compiler profile so later binary or compiler
changes invalidate resume state by hash.

The first campaign remains isolated rather than combinatorial. Numeric controls
get low and high useful probes. Choice controls get every non-default choice.
One small interaction phase follows only when an isolated choice needs a
companion value, such as bevel end selection with nonzero bevel magnitude.

## Boundaries

- Descriptor ranges permit input. They do not prove useful geometry.
- A successful STL export proves native evaluation, not printability.
- The current basic mesh predicate checks closure, winding, components, and
  degeneracy. It does not detect self-intersections or minimum wall thickness.
- No Cylinder parameter becomes a normal workspace mutation until its exact
  vector has native and mesh evidence.
- The experiment runner remains sequential because XenoDream shares user-level
  settings and has no supported headless interface.

## Verification

- Unit tests cover generated-source plan validation, deterministic source
  identity, operation mismatch rejection, resume invalidation, and one-token
  Cylinder diffs.
- The native campaign requires two baseline exports and all planned cases.
- Every promoted profile must evaluate successfully, have one component, zero
  boundary and non-manifold edges, consistent winding, no degenerate triangles,
  and nonzero volume.
- Reports must continue to mark `printable` false until thickness,
  self-intersection, and process-specific checks exist.
