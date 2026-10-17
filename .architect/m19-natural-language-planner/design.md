# M19 deterministic natural-language planner

## Problem

The repository can execute a small set of evidence-gated typed operations, but
users must select each operation through command flags. The first prompt layer
must translate text into one existing `VerifiedOperation` without inventing
values, writing XDX bytes, or adding a model dependency. It must also bind the
interpretation to the workspace revision that the user described.

## Usage

Apply one exact prompt:

```powershell
xenosculpt project prompt sculpture.xsp `
  "apply Cylinder profile bevel-25-front to object Cylinder2" `
  --message "apply measured front bevel"
```

The response includes both the plan and the ordinary revision result:

```json
{
  "plan": {
    "schema": "xenosculpt-operation-plan/v1",
    "planner": {
      "name": "xenosculpt-controlled-english",
      "version": "1"
    },
    "rule": "apply-cylinder-profile-v1",
    "prompt": "apply Cylinder profile bevel-25-front to object Cylinder2",
    "base": {
      "revision_id": "...",
      "artifact_sha256": "..."
    },
    "operation": {
      "type": "cylinder-metamorph-profile-v1",
      "object_name": "Cylinder2",
      "profile": "bevel-25-front",
      "evidence": ["R036"],
      "native_validation_required": true,
      "fabrication_suitable": false
    }
  },
  "created": true,
  "revision": {},
  "differences": []
}
```

The Python API separates interpretation from execution:

```python
status = workspace.status()
plan = plan_prompt(
    "set object Cube2 position to 25 0 0",
    base=HeadBinding.from_revision(status.head),
)
result = workspace.apply_plan(plan, message="move Cube2")
```

Vague, relative, qualitative, or compound prompts fail without changing the
workspace:

```text
make it prettier
move Cube2 a little left
set Cube2 scale to 50 50 100 and rotate it
```

## Controlled language

Version 1 accepts these complete forms:

```text
set object <name> scale to <x> <y> <z>
set object <name> rotation to <x> <y> <z>
set object <name> position to <x> <y> <z>
set object <name> color density to <value>
set object <name> face warp to <value>
place objects in a centered row with spacing <value>
place objects in a centered row with spacing <value> centered at <x> <y> <z>
evolve with seed <integer>
evolve with seed <integer> and strength <value>
apply Sphere profile <profile> to object <name>
apply Cylinder profile <profile> to object <name>
```

Keywords are ASCII case-insensitive. Object and profile names retain their
case. Identifiers contain letters, digits, dots, underscores, or hyphens.
Numbers use signed base-10 notation without units or exponents. Full-string
matching rejects trailing prose and additional operations.

## Shape

Add `src/xenodream_xxp/planning.py`:

```python
PLAN_SCHEMA = "xenosculpt-operation-plan/v1"

class PlanningError(ValueError): ...

@dataclass(frozen=True, slots=True)
class PlannerIdentity:
    name: str
    version: str

@dataclass(frozen=True, slots=True)
class HeadBinding:
    revision_id: str
    artifact_sha256: str

@dataclass(frozen=True, slots=True)
class MutationPlan:
    prompt: str
    rule: str
    base: HeadBinding
    operation: VerifiedOperation
    planner: PlannerIdentity = CONTROLLED_ENGLISH_PLANNER
    schema: str = PLAN_SCHEMA

def plan_prompt(prompt: str, *, base: HeadBinding) -> MutationPlan: ...
def mutation_plan_to_dict(plan: MutationPlan) -> dict[str, object]: ...
```

`MutationPlan.operation` contains one union member, so a multi-operation plan
cannot be constructed. The parser is pure. It reads no workspace, file,
environment variable, model, network resource, clock, or random source.

Move the existing operation metadata mapping from `workspace.py` to one
`verified_operation_details()` function in `mutation.py`. Both revision storage
and plan display derive from that function. This removes a second operation
serialization rule, per model-the-domain.

Add this workspace method:

```python
def apply_plan(self, plan: MutationPlan, *, message: str) -> ApplyResult: ...
```

`apply_plan()` checks both the revision ID and artifact SHA-256 before mutation.
It calls the existing byte mutation path with `plan.operation`, stores the raw
prompt in `Revision.prompt`, and adds this nested record to the ordinary
operation details:

```json
{
  "planning": {
    "schema": "xenosculpt-operation-plan/v1",
    "planner": {
      "name": "xenosculpt-controlled-english",
      "version": "1"
    },
    "rule": "apply-cylinder-profile-v1",
    "base_artifact_sha256": "..."
  }
}
```

The existing transactional parent check remains the final race guard. A stale
plan fails instead of being reparsed against a new revision.

No-op plans create no revision, matching current workspace behavior. The CLI
still returns the complete plan for immediate inspection. A separate attempt
log would add retention and privacy policy that this milestone does not need.

## Module map

- `planning.py` owns controlled language, planner identity, the typed plan, and
  plan display.
- `mutation.py` remains the operation and byte-authorization authority. It also
  owns the single normalized operation description.
- `workspace.py` owns HEAD binding, revision provenance, and execution.
- `cli.py` adds `project prompt` and performs no language parsing itself.
- Existing explicit commands and Python APIs remain unchanged.

The implementation uses only the Python standard library. The packaged
executable needs no new resource, credential, network permission, or hidden
import.

## Synthesis decision

Candidate C supplied the base because its immutable, HEAD-bound plan preserves
the boundary needed by a future untrusted planner. Candidate A supplied the
direct `project prompt` command and the smallest useful grammar. Candidate B's
saved plan files, canonical hashes, and prompt recompilation were rejected for
this milestone. They add a second wire protocol before a second plan producer
exists.

The selected design does not expose a generic model-output decoder. A future
model integration can parse untrusted structured output into the same
`MutationPlan`, but that boundary should be designed with the provider and
provenance requirements in hand.

## Tradeoffs accepted

- We accept command-like English in exchange for deterministic interpretation.
- We accept exact absolute values in exchange for avoiding guessed arithmetic.
- We accept immediate application in exchange for one small caller-facing
  command. The returned plan remains inspectable.
- We accept no durable no-op record in exchange for keeping revisions tied to
  state transitions.
- We accept one operation per prompt in exchange for atomic existing revision
  semantics.
- We accept a new public Python plan type in exchange for a stable boundary
  between future interpreters and the mutation engine.

## Alternatives considered

Two saved-plan commands provide a stronger human approval gap, but they expose
file lifecycle and integrity mechanics before users need asynchronous review.

Calling an external or local language model would accept broader prose, but it
adds nondeterminism, dependencies, configuration, and provenance. The current
typed vocabulary cannot fill missing numeric values honestly anyway.

Putting prompt parsing inside `ProjectWorkspace.apply()` would shorten the call
site but mix language policy with revision storage and make future planners
harder to substitute.

## Open questions and risks

- Do imported projects use object names outside the restricted identifier
  grammar often enough to need quoting in version 2?
- When the first model-backed producer arrives, should plans become saved files
  or workspace records before execution?
- Should future relative operations read current transform values, or remain a
  separate evidenced operation family?

## Tests

- Table-test every accepted grammar form against the exact operation type and
  values.
- Reject empty, multiline, vague, relative, unit-bearing, exponent, trailing,
  and compound text.
- Prove deterministic equal plans for equal prompt and HEAD input.
- Prove plan display and revision details use one operation description.
- Prove a planned mutation produces the same bytes as its explicit operation.
- Prove stale revision and artifact bindings fail without moving HEAD.
- Prove planned no-op and explicit no-op behavior remain unchanged.
- Prove existing explicit CLI output and metadata remain unchanged.
- Build the standalone executable and compare a packaged prompt result with the
  equivalent explicit result.

## Next implementation step

Add failing table-driven planner tests before writing `planning.py`.

