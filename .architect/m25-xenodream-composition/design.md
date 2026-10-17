# M25: bounded Cube composition

## Usage

Add one default Cube to a verified flat XenoDream Cube composition:

```powershell
xenosculpt project add-cube .\sculpture.xsp `
  --position 75 0 0 `
  --message "add the right lobe"
```

The command creates one ordinary workspace revision and returns the allocated
native identity. This example abbreviates `revision` and shows representative
entries from the complete `differences` array:

```json
{
  "created": true,
  "revision": {},
  "added": {
    "id": 2,
    "holon_index": 2,
    "name": "Cube3",
    "group_id": 0,
    "constructor": "Cube"
  },
  "differences": [
    {
      "kind": "value_changed",
      "section": "Header",
      "section_occurrence": 0,
      "key": "NumHolons",
      "key_occurrence": 0,
      "before": "2",
      "after": "3"
    },
    {
      "kind": "key_added",
      "section": "Holon\\2",
      "section_occurrence": 0,
      "key": "ID",
      "key_occurrence": 0,
      "after": "2"
    }
  ],
  "structural_changes": [
    {
      "kind": "section_added",
      "section": "Holon\\2",
      "section_occurrence": 0,
      "record_count": 30
    },
    {
      "kind": "section_added",
      "section": "Holon\\2\\MM\\0",
      "section_occurrence": 0,
      "record_count": 9
    }
  ],
  "native_validation_required": true,
  "fabrication_suitable": false
}
```

`revision` retains its current complete JSON shape. `differences` contains the
header count change and inserted key facts. The operation is offline;
native validation remains an explicit second command:

```powershell
xenosculpt project validate .\sculpture.xsp `
  --stl-max-dimension-mm 120 `
  --mesh-size-percent 10 `
  --timeout-seconds 180
```

Close other XenoDream windows before the acceptance run. The current exporter
persists shared mesh preferences and does not restore them.

## Decision

M25 ships one typed `add-cube-v1` operation. It supports only these transitions:

| Before | After |
| --- | --- |
| `Group1, Cube2` | `Group1, Cube2, Cube3` |
| `Group1, Cube2, Cube3` | `Group1, Cube2, Cube3, Cube4` |

The result families already exist as hash-pinned, XenoDream-accepted templates.
The writer extracts only the new object's canonical record span from the target
template, places it into the current artifact, changes `Header.NumHolons`, and
proves every other pre-existing record stayed byte-identical.

The implementation does not claim general scene editing. It does not expose
Sphere addition, duplicate, remove, reorder, group creation, reparenting,
custom names, custom IDs, or four-or-more-object scenes.

The exact empty-Group3 transition is stronger structural evidence than Cube
append, but it does not yet help build a sculpture because reparenting is not
known. It remains a regression fixture and future grouping oracle rather than
the first public composition command.

## Domain model

`xenodream_xxp.composition` owns the operation and result facts:

```python
@dataclass(frozen=True, slots=True)
class AddCube:
    position: Vector3


@dataclass(frozen=True, slots=True)
class AddedCube:
    id: int
    holon_index: int
    name: str
    group_id: int
    constructor: Literal["Cube"] = "Cube"


@dataclass(frozen=True, slots=True)
class StructuralChange:
    kind: Literal["section_added"]
    section: str
    section_occurrence: int
    record_count: int


@dataclass(frozen=True, slots=True)
class CompositionRewrite:
    data: bytes
    differences: tuple[dict[str, object], ...]
    structural_changes: tuple[StructuralChange, ...]
    added: AddedCube


def append_cube(data: bytes, operation: AddCube) -> CompositionRewrite: ...
```

`AddCube` requires a `Vector3`; its established decimal admission rejects
non-finite inputs. Position formatting uses the current five-place verified
precision and rejects rounding.

`mutation.VerifiedOperation` gains `AddCube`. `MutationResult` gains defaulted
optional fields so existing construction sites and results remain compatible:

```python
@dataclass(frozen=True, slots=True)
class MutationResult:
    data: bytes
    changed: bool
    differences: tuple[dict[str, object], ...]
    object_names: tuple[str, ...]
    native_validation_required: bool = False
    fabrication_suitable: bool = False
    structural_changes: tuple[StructuralChange, ...] = ()
    added: AddedCube | None = None
```

The operation details are stable revision identity input:

```json
{
  "type": "add-cube-v1",
  "position": ["75", "0", "0"],
  "evidence": ["E055", "E056", "E057", "E060", "E061", "E062"],
  "native_validation_required": true,
  "fabrication_suitable": false
}
```

The controlled-English planner does not gain a structural rule in M25.
Hand-constructed plans containing `AddCube` fail existing provenance replay;
the explicit workspace/CLI path is the supported entry point.

## Admission boundary

The private `_FlatCubeAppendContext` is created only when all facts hold:

1. Input bytes parse and serialize identically.
2. `Header.Program=XDX` and `Header.Progversion=1.220` are unique.
3. Declared and observed Holon counts agree.
4. `Holon\0` is the unique verified `Group1` record with `ID=0`,
   `GroupID=0`, and `Type=0`.
5. The remaining nodes are exactly one or two verified Cubes in numeric Holon
   order.
6. Their Holon indexes and persisted IDs are contiguous; their names are the
   canonical `Cube2`, `Cube3` sequence; `GroupID=0`.
7. Each Cube owns exactly one adjacent verified `MM\0` constructor block.
8. Section/key occurrences are unique and no orphan metamorph, extra group,
   opaque node, or structural diagnostic exists.
9. The record layout matches the pinned source-count template after masking
   only fields that existing verified mutations may change.
10. The insertion point is uniquely after the last Cube metamorph block and
    before `Gradients`.

One Cube allocates `Holon\2`, persisted `ID=2`, and `Name=Cube3`. Two Cubes
allocate `Holon\3`, persisted `ID=3`, and `Name=Cube4`. Callers cannot select
an allocation policy or name.

M24 scene JSON remains `xenosculpt-xenodream-scene/v1`. M25 reuses its private
recognition facts but does not add a public composition-capability field yet.
The explicit command reports an exact rejection reason when the whole-scene
precondition fails. This avoids a schema v2 migration for a single operation.

## Structural rewrite and audit

For source count N, `append_cube` loads the hash-pinned N+1 Cube template
through the existing template authority and extracts the complete canonical
`Holon\N+1` plus `MM\0` record span. It changes only the new block's Transform
position tokens, replaces the unique `Header.NumHolons` value, and inserts the
block at the admitted location.

`diff_documents()` remains a user-facing comparison. It is not the structural
authorization check because it indexes key/value records and can miss section
headers, blank lines, raw records, or ordering changes beside an allowed value
change. Its `key_added` entries describe the inserted key/value records;
`structural_changes` separately reports the added `Holon` and `MM\0` sections
and partitions the complete inserted record span between them without counting
any record twice.

The write gate instead checks the complete record sequence:

1. Before and after bytes round-trip exactly.
2. Exactly one pre-existing record changed: `Header.NumHolons` at its complete
   section/key occurrence locator.
3. Exactly one contiguous record span was inserted at the admitted index.
4. The inserted span equals the target template span after only the requested
   position tokens change.
5. Removing the span and restoring the header value recreates the complete
   input bytes.
6. Every original record, including content and line ending, remains in the
   same order.
7. The output scene has the expected signature and allocated identity, all old
   nodes are unchanged, and no new diagnostic appears.
8. The new Cube advertises the existing Cube-local edit capabilities.

Any failed check raises `MutationError` before bytes reach the revision store.
The workspace's existing expected-parent transaction then protects against a
HEAD move between reading and committing.

## Module ownership

- `xenodream_xxp.document`: ordered lossless records only.
- `xenodream_xxp.scene`: read recognition reused by the private append context;
  no mutable scene graph and no public schema change.
- `xenodream_xxp.composition`: append admission, template-span extraction,
  identity allocation, record insertion, and full structural audit.
- `xenodream_xxp.mutation`: verified operation union, dispatch, common result,
  and normalized operation details.
- `xenodream_xxp.adapter`: unchanged app boundary.
- `xenodream_xxp.workspace`: unchanged content-addressed revision transaction.
- `xenodream_xxp.cli`: `project add-cube` parsing and JSON projection only.
- `xenosculpt.core`, ComfyUI, and MoI: unchanged.

This applies Boundary Discipline: XDX structure remains XenoDream knowledge;
the shared core continues to know only artifacts, revisions, refs, and
application identity.

## Verification sequence

This sequence applies Sequence Work into Verifiable Units.

1. Add failing admission tests over accepted one-, two-, and three-Cube
   templates and malformed/unsupported neighbors.
2. Implement the pure composition rewrite for one-to-two and prove full-record
   preservation plus canonical equality when source values match the target
   template.
3. Add two-to-three through the same profile table and repeat the proof.
4. Integrate mutation, workspace, and CLI; prove rejection does not create an
   artifact, database row, or HEAD change.
5. Prove the added Cube can be targeted by current mutations; existing row and
   evolve behavior remains unchanged.
6. Run the full suite, reference verifier, architecture isolation, ComfyUI and
   MoI focused suites, wheel/resource checks, and packaged CLI smoke.
7. Run a fresh packaged XenoDream acceptance at 120 mm / 10% detail with no
   preexisting XenoDream process. Require `succeeded`, native evaluation,
   unchanged source/disposable hashes, confirmed cleanup, retained executable
   hash/settings/report, and an independently parsed mesh. Basic topology is
   reported separately and fabrication suitability remains false.
8. At this first structural-edit checkpoint, repeat the packaged ComfyUI
   minimal workflow run when its server is available and the packaged MoI 4
   cylinder/reopen/STL proof. Unavailable external runtime is reported, not
   replaced by a claim.

The native proof should use a non-default first Cube plus a visibly separated
new Cube so it tests preservation as well as load/evaluation. Repeated STL
bytes are not expected to match; compare topology, counts, bounds, and
dimensions under identical settings.

## Compatibility

- Workspace schema stays at v3.
- Existing operation types, detail JSON, output bytes, and revision IDs stay
  unchanged.
- Existing `MutationResult` callers remain valid through defaulted fields.
- M24 scene JSON remains v1.
- Old `.xsp` workspaces open without migration.
- `project describe`, compare, branch, checkout, export, import, validation,
  and fabrication assessment retain their current contracts.
- Core import isolation and foreign-application rejection remain mandatory.
- Structural additions never inherit native validation or fabrication evidence
  from the parent revision.

## Principles applied

### Foundational Thinking

The shared data structure is a closed append-profile plus an admitted flat
composition, not a general mutable scene. Exact record preservation and native
identity are established before adding more verbs.

### Model the Domain

`AddCube` and `AddedCube` encode the one supported request and its allocated
result. Unsupported names, IDs, groups, constructors, copy policies, and counts
cannot be expressed.

### Boundary Discipline

CLI text becomes a typed operation once. Raw XDX bytes are validated at the
composition boundary. The writer trusts only `_FlatCubeAppendContext` and
returns audited native bytes. Generic revision code never inspects Holons.

### Sequence Work into Verifiable Units

Admission, one-to-two, two-to-three, revision integration, packaged proof, and
cross-app regression are separate gates. Sphere and later structural verbs do
not ride on an unverified generalization.

## Alternatives and tradeoffs

### Exact empty Group3 first

This is the strongest observed structural transition and remains an oracle.
It was rejected as the first public feature because, without reparenting, it
does not change the sculpture.

### Evidence acquisition before any implementation

Manually observing every UI append would reduce uncertainty, but accepted
target templates plus a complete preservation audit and a fresh native run can
prove the bounded writer without delaying the useful path. If the native run
contradicts the model, the operation does not ship.

### Generic `project add --constructor`

This is attractive for future Cube/Sphere support, but it exposes a generic
surface before more than one constructor is authorized. `add-cube` says exactly
what M25 knows; a later command can coexist or replace it with an explicit
migration.

### Recompile the whole target project

Rejected because it discards opaque current state. The selected writer inserts
one canonical span and proves all earlier bytes remain unchanged.

### Clone the last Cube

Rejected because it could copy opaque references or state. The new block comes
from the accepted target-count template and carries only the requested
position change.

### Public scene capability/schema v2

Deferred. A whole-scene capability is conceptually honest, but a public schema
change is disproportionate for the first composition verb. The classifier is
private and shared by reporting tests and the writer.

Tradeoff: the command accepts only one/two canonical flat Cube families. That
restriction buys deterministic identity, exact preservation, and a native
proof target. It is intentionally narrower than the eventual sculpture editor.

## Red-flag audit

- **Shallow module:** clear. `composition.py` hides admission, template
  selection, allocation, insertion, reverse reconstruction, and post-state
  proof behind one operation.
- **Information leakage:** clear. Section paths, record indexes, hashes, and
  masks stay private. The CLI knows only position and message.
- **Temporal decomposition:** clear. Callers do not coordinate parse,
  allocate, insert, and validate stages.
- **Pass-through service:** clear. Workspace and adapter retain independent
  revision/provenance policy; the new module performs the structural work.
- **Premature generalization:** clear. No shared scene graph, plugin protocol,
  generic constructor union, or generic structural operation enters core.
- **Capability overclaim:** guarded by the same private append context used by
  tests and the writer, plus an explicit native acceptance gate.

## Next layers

After this slice passes native and cross-app gates:

1. Add Sphere only after one controlled Cube-to-Cube/Sphere transition proves
   allocation, naming, adjacency, and source preservation.
2. Recover true duplicate behavior before using the word duplicate.
3. Generalize removal only after first/middle/last and add-after-delete evidence
   resolves section compaction, persistent IDs, and reference policy.
4. Recover group membership and reparent behavior before exposing grouping.
5. Leave reorder until physical order and evaluation effects are observed.
6. Add multi-operation natural-language planning only after these typed
   operations are stable.
