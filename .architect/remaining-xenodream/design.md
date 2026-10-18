# Remaining XenoDream evidence campaign

## Usage first

The only new production command authorized by current native evidence is the
exact empty-Group3 transition:

```powershell
xenosculpt project add-empty-group .\sculpture.xsp `
  --message "add empty Group3"

xenosculpt project describe .\sculpture.xsp
xenosculpt project validate .\sculpture.xsp `
  --profile preview --stl-max-dimension-mm 120
```

It accepts only the verified one-Cube flat scene, appends the exact native
Group3 record span, and does not move Cube2 or claim general hierarchy support.
The command is deliberately absent from controlled-language recipes until an
object-to-group transition is observed.

Constructor work remains a repository experiment:

```powershell
python .\scripts\probe_xenodream_constructors.py `
  --constructor Pipe `
  --corpus-root <installed-corpus> `
  --output-dir <new-empty-directory>
```

The accepted constructor names are closed: RoundCube, Pipe, Torus, Cog, and
SpiralShell. A successful result means only that a hash-pinned synthetic XDX
candidate evaluated natively. The manifest always records
`writer_authorized: false`, `registry_promoted: false`, and
`fabrication_suitable: false`.

## Definition of done

This campaign is done when all of these statements are true:

1. `AddEmptyGroup` reproduces the retained native target from the canonical
   source, preserves admitted prior Cube edits, reverse-reconstructs every
   source byte, rejects a second application atomically, and passes packaged
   preview and review validation.
2. One rerunnable research driver produces an explicit VERIFIED, NOT VERIFIED,
   or INCONCLUSIVE disposition for each of the five constructor candidates.
3. No constructor becomes a public generator, writer, scene capability, or
   planner operation unless a separate promotion gate is satisfied.
4. XenoDream changes do not alter the shared revision core, ComfyUI, or MoI.
5. The full suite, reference verifier, packaged executable, native checks, and
   independent hostile review are green.

The campaign does not implement delete, duplicate, reparent, reorder, physical
fabrication, or a printability pass. Those require evidence not present today.

## Scope and rigor

The work has two independently landable units: one production operation and
five research dispositions. Native UI/process interaction and public XDX writes
make this high-rigor work. Each unit ends in a real artifact check before the
next starts. A failed constructor probe remains a recorded negative result and
does not weaken another probe's checks.

## Production shape

```python
@dataclass(frozen=True, slots=True)
class AddEmptyGroup:
    pass

@dataclass(frozen=True, slots=True)
class AddedEmptyGroup:
    id: Literal[2]
    holon_index: Literal[2]
    name: Literal["Group3"]
    group_id: Literal[2]
    kind: Literal["group"] = "group"

AddedNode: TypeAlias = AddedCube | AddedSphere | AddedEmptyGroup

def append_empty_group(data: bytes, operation: AddEmptyGroup) -> CompositionRewrite: ...
```

`composition.py` owns source admission, the pinned target span, insertion, the
complete byte audit, and the semantic postcondition. `mutation.py` adds the
closed operation and stable evidence details. The existing adapter and
workspace paths provide the atomic revision transaction. `cli.py` adds one
explicit command. Core and the other application packages remain unchanged.

The writer must:

- admit XDX 1.220 with exactly Group1 and verified Cube2;
- accept only the prior Cube fields already admitted by Cube/Sphere append;
- extract the exact 36-record Holon\\2 span from the retained native target;
- change only Header.NumHolons among pre-existing records;
- require ID 2, GroupID 2, Type 0, and Name Group3;
- remove the inserted span, restore the count, and reproduce the source bytes;
- describe exactly Group1, Cube2, Group3 with no diagnostics;
- report native validation required and fabrication unsuitable.

`project additions` stays object-only and schema-compatible. One group action
does not justify a general action registry or another capability endpoint.

## Research shape

```python
ProbeConstructor = Literal["RoundCube", "Pipe", "Torus", "Cog", "SpiralShell"]

@dataclass(frozen=True, slots=True)
class ConstructorProbeDisposition:
    constructor: ProbeConstructor
    stage: Literal[
        "descriptor_verified",
        "synthesized",
        "preview_evaluated",
        "review_evaluated",
        "failed",
    ]
    candidate_sha256: str | None
    writer_authorized: Literal[False] = False
    registry_promoted: Literal[False] = False
    fabrication_suitable: Literal[False] = False

def run_constructor_probe(...) -> ConstructorProbeDisposition: ...
```

The driver is the smallest reusable proof tool. It pins the executable, recovers
contiguous descriptors, verifies closed historical anchor hashes, declared
parameter arity, and numeric token syntax,
synthesizes from the normalized one-object XDX 1.220 scaffold, audits the four
authorized constructor fields, runs managed native validation, and writes one
self-contained manifest. It never creates a workspace operation or changes the
constructor registry.

The probe order is Pipe, Torus, Cog, RoundCube, SpiralShell. Pipe and Torus have
the strongest MM0-only historical anchors. Cleanup failure stops the campaign;
a constructor-specific failure does not.

## Verification sequence

1. Add failing exact/reverse/atomic tests for Group3.
2. Implement the pure writer and integrate the direct CLI command.
3. Run focused tests, the full suite, and reference verification; commit.
4. Build the package and run Group3 preview/review validation on a non-default
   Cube source. Retain the report and hashes.
5. Extend the descriptor recovery tool with the five closed profiles and retain
   generated descriptor evidence.
6. Add the constructor probe driver and pure synthesis tests.
7. Run each constructor independently and retain all five dispositions.
8. Run cross-app regression checks, rebuild, hostile-review the trail and
   artifacts, then push only verified work.

## Stop conditions

- Any unexplained target byte, failed reverse audit, changed source hash, or
  non-atomic rejection blocks AddEmptyGroup.
- Descriptor range, anchor hash, parameter arity or numeric syntax, native evaluation, or cleanup
  failure makes that constructor NOT VERIFIED or INCONCLUSIVE.
- Native evaluation alone never authorizes a writer. Promotion still needs a
  native-created current-version profile or a separately reviewed change to the
  promotion standard.
- Missing self-intersection, thickness, process, support, tolerance, material,
  or physical-result evidence keeps fabrication incomplete.

## Synthesis decision

The strict candidate is the base because it has the smallest honest production
interface and keeps research evidence out of product claims. The runtime
candidate contributed process ownership, paired-control thinking, and explicit
native outcomes. The product candidate contributed the later independent lanes,
but its structural-capability API and planner rule were rejected as premature
for one parameterless group action. A general structural editor, UI-action
runner, and public experimental constructors expose more policy than the current
evidence can support.

## Red-flag audit

- The group command hides template selection, admission, insertion, and audit
  behind one typed operation.
- The research driver owns the complete experiment rather than exposing stages
  callers must coordinate.
- XDX records, styles, and evidence status remain outside shared core.
- No optional bag of unrelated structural effects is introduced.
- The work is split by domain knowledge, not by chronological processing steps.

## Principles applied

- Foundational Thinking: the exact operation and probe disposition types precede
  implementation.
- Model the Domain: production authorization and research disposition are
  distinct types instead of flags on one generic constructor.
- Boundary Discipline: CLI, executable, corpus, and JSON inputs are parsed once;
  internal functions consume typed values.
- Sequence Work into Verifiable Units: Group3 lands and passes its native gate
  before constructor research begins.
- Build the Lever: the constructor driver is the rerunnable artifact that
  performs and proves the five experiments.
