# Autonomous XenoDream completion sequence

## Usage first

```powershell
# Add the second structurally authorized constructor.
xenosculpt project add-sphere sculpture.xsp `
  --position 45 0 0 `
  --message "add Sphere3"

# See only additions the exact HEAD artifact admits.
xenosculpt project additions sculpture.xsp

# Preview then atomically apply a bounded recipe.
xenosculpt project prompt sculpture.xsp `
  "add Sphere at 45 0 0; apply Sphere profile cushion-core to object Sphere3" `
  --message "add and shape Sphere3" `
  --dry-run
xenosculpt project prompt sculpture.xsp `
  "add Sphere at 45 0 0; apply Sphere profile cushion-core to object Sphere3" `
  --message "add and shape Sphere3"

xenosculpt project validate sculpture.xsp --profile preview --stl-max-dimension-mm 120
xenosculpt project validate sculpture.xsp --profile review --stl-max-dimension-mm 120
xenosculpt project assess sculpture.xsp
```

The sequence ends before physical fabrication. It never turns missing native-file
knowledge or missing fabrication evidence into a success claim.

## Decision

Three independent candidates agreed that the next safe structural operation is
the exact `Group1, Cube2 -> Group1, Cube2, Sphere3` transition. The accepted
Cube/Sphere template, byte-identical XenoDream resave, existing Sphere mutation
support, and M25 reversible span audit make this substantially stronger than
duplicate, removal, grouping, reordering, or a new constructor.

The adopted sequence is:

1. **M27:** exact Sphere append plus packaged native proof.
2. **M28:** revision-bound addition capabilities and pure dry-run.
3. **M29:** two-to-five-step controlled recipes applied as one revision, plus
   fabrication analysis only where a versioned oracle proves the analyzer.
4. **Stop:** M30 physical fabrication, process selection, repair, and any
   unsupported XDX transition require human or new native evidence.

## M27: exact Sphere append

Add a closed `AddSphere(position)` operation in `xenodream_xxp.composition`.
Admission is limited to the same canonical flat one-Cube family used by M25.
The writer selects the existing hash-pinned `(CubeSpec, SphereSpec)` template,
inserts its exact 39-record target span, changes only `Header.NumHolons` and the
requested Sphere position tokens, then proves:

- exact parser round trip;
- complete target-span equality;
- reverse removal reconstructs every source byte;
- prior records are unchanged except the authorized count field;
- the resulting scene is exactly `Group1, Cube2, Sphere3`;
- Sphere3 is verified and advertises scale, position, and Sphere-profile edits.

```python
@dataclass(frozen=True, slots=True)
class AddSphere:
    position: Vector3

@dataclass(frozen=True, slots=True)
class AddedSphere:
    id: int
    holon_index: int
    name: str
    group_id: int
    constructor: Literal["Sphere"] = "Sphere"

def append_sphere(data: bytes, operation: AddSphere) -> CompositionRewrite: ...
```

The CLI mirrors `add-cube`. Rejection is atomic. Production admission does not
accept Sphere-first, repeated Sphere, two-Cube-to-Sphere, custom identity,
arbitrary groups, or unsupported XDX versions.

Acceptance requires pure tests, exact canonical equality, workspace failure
atomicity, an exact-tree package, and fresh preview/review validation of a
non-default preserved Cube plus separated Sphere. Native acceptance is distinct
from one-component mesh validity and fabrication suitability.

## M28: discoverable capabilities and dry-run

Whole-scene addition offers are a separate revision-bound report; M24 scene JSON
v1 remains stable. The report calls the same admission functions as the writers,
so every offered action must apply and every rejected action has a stable blocker.

```python
@dataclass(frozen=True, slots=True)
class AdditionOffer:
    operation: Literal["add-cube-v1", "add-sphere-v1"]
    constructor: Literal["Cube", "Sphere"]
    allocated_name: str
    allocated_id: int
    holon_index: int
    group_id: int

def addition_capabilities(data: bytes, binding: SceneBinding) -> AdditionCapabilities: ...
```

The controlled planner gains only exact `add Cube at X Y Z` and
`add Sphere at X Y Z` rules. Old prompt serialization and revision IDs remain
unchanged. `--dry-run` parses, binds, and evaluates against verified artifact
bytes but creates no file, database row, validation, assessment, branch, or HEAD
change. Applying from the same base must produce the previewed artifact hash.

## M29: atomic controlled recipes

Text containing semicolons contains two to five non-empty clauses. Every clause
must independently match an existing deterministic rule. Newlines, empty
clauses, pronouns, relative values, implicit targets, conditions, loops, and
free-form model output are rejected.

```python
@dataclass(frozen=True, slots=True)
class PlannedStep:
    rule: str
    operation: VerifiedOperation

@dataclass(frozen=True, slots=True)
class OperationSequencePlan:
    prompt: str
    base: HeadBinding
    steps: tuple[PlannedStep, ...]
    planner: PlannerIdentity
    schema: Literal["xenosculpt-operation-sequence-plan/v1"]
```

One pure evaluator applies all operations to transient bytes. Each step passes
the existing operation-specific audits. Workspace code checks the exact bound
HEAD, evaluates, then records one final artifact and one revision through the
existing expected-parent transaction. A failed step publishes nothing.
Revision details retain ordered rule/operation data and per-step input/output
hashes. Intermediate artifacts are never branch targets.

Fabrication work in this milestone is conservative. A new policy version is
allowed only after generated STL fixtures establish analyzer behavior for
self-intersections, adjacency, degeneracy, scaling, and limits. Analyzer name,
version, definition hash, tolerance, timeout, triangle limit, mesh hash,
validation ID, revision ID, and artifact hash belong to assessment identity.
Timeout, ambiguity, unsupported topology, or missing process semantics yield
`not_evaluated` and therefore `incomplete`, never pass. Minimum feature,
overhang, tolerance, support, and process checks remain unevaluated until each
has an explicit metric and oracle.

## Ownership

```text
xenodream_xxp/composition.py  exact append profiles and full byte audits
xenodream_xxp/planning.py     deterministic one-step and sequence plans
xenodream_xxp/adapter.py      pure in-memory operation/sequence evaluation
xenodream_xxp/workspace.py    revision binding and one atomic commit
xenodream_xxp/fabrication.py  XenoDream mesh-policy versions
xenodream_xxp/cli.py          syntax and stable JSON projection
xenosculpt/core/              unchanged revision/artifact mechanics
xenosculpt/mesh.py            app-neutral measured STL facts only
```

No Holon, XDX constructor, planner rule, native validation profile, or
fabrication policy enters the shared core. ComfyUI and MoI storage/execution
remain unchanged.

## Verifiable sequence

Each unit begins with a failing boundary/regression test and ends with focused
tests, the full suite, `scripts/verify_reference.py`, architecture isolation,
and `git diff --check`.

1. M27 pure writer and adversarial admission.
2. M27 mutation/workspace/CLI integration and atomic rejection.
3. M27 exact-tree package plus native preview/review; cross-app offline gates
   and a fresh MoI check. ComfyUI live runs only when its pinned server exists.
4. M28 offer/writer parity and revision-bound JSON.
5. M28 pure dry-run and exact preview/apply hash parity.
6. M29 pure sequence evaluator and failure-at-every-step tests.
7. M29 atomic workspace commit, stale-HEAD refusal, CLI/package/native proof.
8. Fabrication oracle experiment; ship only checks that meet its stop gate.
9. Final hostile review by an independent model, exact-tree rebuild, retained
   evidence reconciliation, commits, and push.

## Hard stops

The autonomous run blocks an individual capability, without guessing, when:

- native save/resave or packaged validation produces unexplained state;
- reverse byte reconstruction fails;
- an advertised action is rejected by its writer;
- dry-run changes durable state or differs from apply;
- sequence failure can publish partial state;
- a new constructor lacks a minimal XDX 1.220 native-created profile;
- an analyzer has unsafe false negatives or unnamed tolerance semantics;
- physical process, material, orientation, repair, or fabrication-result input
  is required.

Blocked capabilities are documented as unsupported; they do not block safe,
independent milestones.

## Alternatives rejected

- **General mutable scene/serializer:** evidence does not cover arbitrary
  groups, iterators, references, constructor stacks, or identity allocation.
- **Generic `add --constructor`:** two admitted additions do not justify an
  open constructor string.
- **Duplicate/remove/group/reorder first:** native identity/reference behavior
  is incomplete and copying opaque state is unsafe.
- **RoundCube/Torus/Pipe/Cog/SpiralShell from descriptors alone:** descriptor
  labels establish read semantics, not native construction bytes.
- **One revision per recipe step:** exposes partial failure and makes retry
  non-idempotent.
- **Automatic validation in commit:** UI/runtime failure has different semantics
  from a durable offline edit.
- **Fabrication pass from partial checks:** confuses mesh evidence with process
  suitability.

## Red-flag audit

- Deep modules hide templates, locators, allocation, audits, provenance, and
  rollback.
- Application facts do not leak into core or other adapters.
- Callers do not coordinate parse/mutate/audit/commit stages.
- Workspace methods add binding and transaction value; they are not pass-throughs.
- Separate plan types exclude invalid optional states.
- Shared XenoDream runtime state remains serialized by the M26 boundary.
- The public vocabulary remains closed and evidence-derived.

## Attention

Human input is intentionally deferred until M30 or until a blocked capability
requires a new native UI experiment. The main risks are XDX identity allocation,
opaque-reference updates, false-negative geometry analysis, and mistaking native
evaluation for printability. Each is represented by a stop gate above.
