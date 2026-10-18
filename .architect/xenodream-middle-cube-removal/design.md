# Bounded XenoDream middle-Cube removal

Status: stopped at the native runtime gate. No public writer ships.

## Problem

XenoDream has evidence-bounded append operations but no subtractive scene edit.
E058 records a middle-sibling deletion, yet that save also moved Group1 by
`4, 1, 0`. The experiment did not establish that the movement belonged to the
delete action. A writer cannot copy that unexplained change or silently ignore
it. This milestone first captures a clean native transition, then implements
only the exact three-Cube to two-Cube family if every changed byte is explained.

## Usage

This was the proposed caller contract. The runtime gate stopped it, so the
command below is not present in the released CLI.

```powershell
xenosculpt project remove-middle-cube .\sculpture.xsp `
  --message "remove the center cube"

xenosculpt project describe .\sculpture.xsp
xenosculpt project validate .\sculpture.xsp `
  --profile preview --stl-max-dimension-mm 123
```

The command removes `Cube3` only from the verified flat
`Group1, Cube2, Cube3, Cube4` family. It preserves the persistent identity and
all admitted fields of `Cube2` and `Cube4`. `Cube4` moves from serialized
section `Holon\3` to `Holon\2` while keeping ID 3 and Name `Cube4`.

Success returns the revision, the removed object, semantic differences, and
explicit removed and reindexed section facts. It always reports native
validation required and fabrication unsuitable. Any other scene fails before
HEAD, revisions, or artifacts change.

## Shape

```python
@dataclass(frozen=True, slots=True)
class RemoveMiddleCube:
    pass

@dataclass(frozen=True, slots=True)
class RemovedCube:
    id: Literal[2] = 2
    holon_index: Literal[2] = 2
    name: Literal["Cube3"] = "Cube3"
    group_id: Literal[0] = 0
    constructor: Literal["Cube"] = "Cube"

@dataclass(frozen=True, slots=True)
class StructuralRemovalChange:
    kind: Literal["section_removed", "section_reindexed"]
    section: str
    section_occurrence: int
    record_count: int
    new_section: str | None = None

@dataclass(frozen=True, slots=True)
class RemovalRewrite:
    data: bytes
    differences: tuple[dict[str, object], ...]
    structural_changes: tuple[StructuralRemovalChange, ...]
    removed: RemovedCube

def remove_middle_cube(
    data: bytes,
    operation: RemoveMiddleCube,
) -> RemovalRewrite: ...
```

`composition.py` owns admission, record removal, section reindexing, reverse
reconstruction, and the semantic postcondition. `mutation.py` adds the closed
operation and stable revision details. The existing adapter and workspace keep
the atomic commit boundary. `cli.py` adds one direct command. Core, ComfyUI,
and MoI do not gain XenoDream scene types.

The writer admits XDX 1.220 with exactly Group1 and three verified Cube
children. Their section indexes are 1, 2, and 3; IDs are 1, 2, and 3; names are
Cube2, Cube3, and Cube4; all use GroupID 0 and one verified MM0 constructor.
The complete record sequence must match the pinned three-Cube family except
for fields already authorized by existing local mutations.

The transition removes the complete `Holon\2` and `Holon\2\MM\0` span,
renames the surviving `Holon\3` and `Holon\3\MM\0` section headers and record
ownership to index 2, and changes Header.NumHolons from 4 to 3. Every other
byte remains exact. The audit reverses those steps and must reproduce the
source byte-for-byte. The post-state must describe exactly Group1, Cube2, and
Cube4 with no diagnostics; Cube4 must retain ID 3 and its current edit
capabilities.

This is a deep, narrow interface. The caller asks for one evidenced action.
It does not coordinate record spans, section renaming, identity retention, or
revision safety.

## Synthesis decision

Two shapes were considered locally because this session does not permit the
architect workflow's normal delegated design fan-out.

The chosen shape is an operation-specific `RemovalRewrite`. It keeps the
existing addition result and `project additions` v1 contract unchanged while
making removal facts explicit.

The rejected shape broadened `CompositionRewrite.added` into a generic changed
node union and expanded the existing `StructuralChange` record. That would add
nullable fields to every existing addition result and make callers interpret
which fields apply. It exposed more internal variation for no current benefit.

## Tradeoffs accepted

- We accept a command tied to `Cube3` in one family in exchange for complete
  byte and identity audits.
- We accept separate addition and removal result records in exchange for
  keeping the existing addition JSON stable.
- We accept a fresh native evidence gate before implementation in exchange for
  refusing to encode the unexplained Group1 movement in E058.

## Alternatives considered

- A general `remove-object --id` API lost because first, last, only-child,
  group, reference, and later-allocation behavior remain unknown.
- Rebuilding the two-Cube project from a template lost because it would erase
  admitted edits and opaque state instead of preserving the source.
- Treating E058 as sufficient lost because its Group1 movement cannot be
  attributed to deletion.

## Open questions and risks

- Will a clean native deletion leave Group1 and SelectionSpots unchanged?
- Does XenoDream reindex only section paths while retaining the survivor's
  persistent ID, name, and all field bytes?
- Will preview validation report two clean components for the separated
  survivors, and will review preserve the same dimensions?

Any unexplained answer stops implementation and records the experiment only.

## Outcome

The clean native transition answered the serialization questions. Group1 and
SelectionSpots stayed unchanged. XenoDream removed Cube3, compacted Cube4's
section path, and preserved Cube4 ID 3, Name `Cube4`, transform, and remaining
field bytes. An independent rewrite matched the native target exactly and
reversed to the source exactly.

The runtime gate failed. The exact native target timed out actively under the
180-second preview profile. A candidate with the survivors at the accepted
-50 and +50 spacing also timed out at 10 percent, then timed out after 300
seconds at 1 percent. Every run preserved its source and cleaned up, but none
produced an STL.

The known-good two-Cube profile uses contiguous survivor ID 2 and Name
`Cube3`. Native deletion preserves ID 3 and Name `Cube4`. Renumbering would
invent reference semantics that the evidence does not authorize. The candidate
implementation was therefore removed. The retained experiment is negative
evidence, not a product capability.

## Next implementation step

Investigate how preserved holon identity affects evaluation and references
before reconsidering deletion. Do not implement removal by normalizing IDs or
names unless a controlled native transition establishes that behavior.
