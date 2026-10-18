# Finish the evidence-backed XenoDream integration

## Problem

The integration already preserves native files, records immutable revisions,
supports bounded composition and recipes, and validates through XenoDream.
The remaining roadmap mixes three different things: useful constructor
vocabulary, structural operations whose identity rules are unknown, and
fabrication claims for which no robust analyzer or physical process profile is
available. Treating them as one generic scene-editor task would erase the
evidence boundary that has kept the project safe.

## Definition of done

The autonomous run is complete when every remaining XenoDream promise is in
one of two states:

1. A public command and typed operation pass byte, revision, native, packaged,
   and compatibility checks.
2. A retained experiment identifies the failed predicate, and no public
   command claims the unsupported behavior.

Physical fabrication itself remains a human action. Software may finish the
evidence package and report that fabrication is incomplete; it must not invent
printer, material, support, tolerance, or artistic acceptance decisions.

## Usage

The next public addition is a closed constructor compiler:

```powershell
xenosculpt generate-constructor Torus .\torus.xxp `
  --scale 60 60 40 --position 0 0 10
xenosculpt project init .\torus.xsp .\torus.xxp
xenosculpt project prompt .\torus.xsp `
  "set object Torus2 position to 25 0 10"
xenosculpt project validate .\torus.xsp `
  --profile preview --stl-max-dimension-mm 123
```

The accepted names are `RoundCube`, `Pipe`, `Torus`, `Cog`, and
`SpiralShell`. Each compiler starts from the normalized one-object XDX 1.220
scaffold and installs one hash-pinned default constructor vector. Scale and
position are the only initial write capabilities, and only if transformed
native proofs pass. Raw constructor parameters remain read-only.

## Shape

```python
class ClosedConstructorName(StrEnum):
    ROUND_CUBE = "RoundCube"
    PIPE = "Pipe"
    TORUS = "Torus"
    COG = "Cog"
    SPIRAL_SHELL = "SpiralShell"

@dataclass(frozen=True, slots=True)
class ClosedConstructorSpec:
    constructor: ClosedConstructorName
    scale: Vector3 = Vector3(Decimal("50"), Decimal("50"), Decimal("50"))
    position: Vector3 = Vector3()

def compile_closed_constructor(spec: ClosedConstructorSpec) -> bytes: ...
```

`xenodream_xxp._closed_constructor` owns the closed profile table and byte compiler.
It contains the constructor name, style, exact default parameter bytes,
descriptor count, expected canonical artifact hash, and evidence IDs. It
audits the four constructor records plus the requested transform tokens and
requires exact parser roundtrip.

`generator.py` exports the typed spec and compiler. `scene.py` recognizes the
five constructors only when XDX version, style, arity, exact default parameter
shape, and registry role agree. It grants scale and position independently
from constructor-parameter authority. `mutation.py` continues to own the
existing `ObjectMutation`, so no new mutation protocol enters the workspace or
shared core. `cli.py` adds one enum-bounded command.

The remaining lanes are independent experiments:

- identity and reference behavior after deletion;
- true duplication, reparenting, and sibling order;
- robust self-intersection and thickness analysis;
- process profiles and physical fabrication.

A failed lane records a stop without blocking verified constructor work.

The corpus and paired runtime experiment later closed one group-membership
slice. `ConfigureGroup3(profile)` accepts only the exact Group1, Cube2, Group3
family, sets Cube2's literal GroupID to persisted group ID 2, and writes one
of two complete measured group-scale vectors: 50/50/50 or 60/50/50. It is
idempotent, preserves every other byte, and requires native validation. The
100/50/50 trial timed out actively, so free-form scale is not exposed. The
public command does not generalize names, multiple children, nesting, or
arbitrary reparenting.

## Synthesis decision

Candidate A is the base. It adds the five forms users can actually work with
while keeping the raw parameter vectors private. Candidate B's typed registry
is attractive, but it promotes descriptor metadata into write authority before
parameter interactions are measured. The useful part of B, one source of truth
for closed constructor identities, is retained as a private profile table.

The normal architect fan-out was unavailable because this session forbids
subagent delegation unless the user requests it. Two structurally different
candidates were developed locally instead.

## Tradeoffs accepted

- We accept exact-profile generation rather than a general constructor API in
  exchange for native proof of every emitted artifact family.
- We accept scale and position as the only common edits in exchange for reusing
  an already audited transform writer.
- We accept explicit stop records for unsupported structural and fabrication
  work in exchange for never presenting guesses as completed functionality.

## Alternatives considered

- A descriptor-driven parameter editor lost because recovered ranges and
  defaults do not prove safe parameter combinations.
- A general `add-object` and `remove-object` interface lost because identity,
  reference, allocation, and evaluation rules remain incomplete.
- Marking the roadmap complete without new product behavior lost because the
  five native-verified constructors are useful and can be promoted through a
  smaller, testable interface.

## Open questions and risks

- Do non-default scale and position preserve native evaluation for all five
  constructor profiles?
- Does XenoDream accept the final packaged artifacts under both named profiles?
- Can any remaining structural operation be proved without interactive UI
  evidence or invented identity normalization?

## Verification sequence

1. Capture the clean baseline and add compiler/scene/CLI tests before code.
2. Implement the closed compiler and require canonical hashes.
3. Enable recognition, scale, and position only after focused byte tests pass.
4. Run one non-default transformed native preview for every constructor.
5. Revert any constructor whose native predicate fails; failures remain
   research evidence.
6. Build the package and repeat public CLI, workspace, and native checks.
7. Run the full suite, reference verifier, core isolation, ComfyUI and MoI
   regression checks.
8. Reconcile the structural and fabrication lanes into shipped or stopped
   status, then commit and push the auditable result.

## Red-flag audit

The public compiler is one operation with a closed enum. It hides styles,
parameter vectors, scaffold selection, and byte auditing. Constructor policy
lives in one XenoDream module. No XDX knowledge moves into shared core. The
workspace does not gain a forwarding API because existing initialization and
mutation paths already provide the needed boundary.

## Principles applied

- Foundational Thinking selected the closed constructor profile table before
  compiler branches.
- Model the Domain separated public write authorization from recovered
  descriptor metadata.
- Boundary Discipline keeps CLI strings and XDX bytes at the edges while the
  compiler consumes typed values.
- Build the Lever makes the compiler and native matrix rerunnable proof tools.
- Sequence Work into Verifiable Units makes each constructor independently
  keepable or revertible.
