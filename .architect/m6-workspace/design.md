# M6 persistent revisions and controlled mutations

## Problem

The current compiler safely creates a few XDX 1.220 profiles, but it cannot
load an existing native artifact, change one verified property, and retain a
history. The lossless parser preserves the bytes needed for that operation,
but it deliberately has no editing policy. The new boundary must preserve
unrelated bytes, keep native `.xxp` artifacts accessible, make revisions and
branches crash-safe, and refuse mutations beyond the established evidence.

## Usage (caller's view)

```powershell
xenosculpt project init sculpture.xsp output/smoke_test.xxp `
  --process FDM --build-volume 220 220 250 --min-feature-mm 1.2

xenosculpt project mutate sculpture.xsp --object Cube2 `
  --scale 40 55 70 --message "elongate the cube"

xenosculpt project branch sculpture.xsp wider --checkout
xenosculpt project row sculpture.xsp --spacing 120 `
  --message "separate the forms"

xenosculpt project log sculpture.xsp
xenosculpt project compare sculpture.xsp main wider
xenosculpt project checkout sculpture.xsp main
xenosculpt project export sculpture.xsp output/restored.xxp
xenosculpt project import sculpture.xsp manually-edited.xxp `
  --message "import XenoDream edit"
```

Python callers use one stateful domain object and typed operations:

```python
workspace = ProjectWorkspace.create(root, source, constraints)
revision = workspace.apply(
    ObjectMutation(object_name="Cube2", scale=Vector3(...)),
    message="elongate the cube",
)
workspace.create_branch("wider", checkout=True)
workspace.apply(CenteredRowMutation(spacing=Decimal("120")))
```

## Shape

`workspace.py` owns persistence, revision identity, branch movement, imports,
exports, and recovery policy. A workspace contains `project.sqlite3` plus
content-addressed `artifacts/<sha256>.xxp` files. SQLite transactions make
revision insertion and reference movement atomic. Artifacts are written and
verified before the transaction, so an interrupted operation can leave only an
unreferenced content-addressed file, never a branch pointing at missing bytes.

```python
@dataclass(frozen=True, slots=True)
class FabricationConstraints:
    process: str | None = None
    build_volume_mm: Vector3 | None = None
    min_feature_mm: Decimal | None = None

@dataclass(frozen=True, slots=True)
class Revision:
    id: str
    parent_id: str | None
    artifact_sha256: str
    created_at: str
    operation: str
    message: str
    prompt: str | None

class ProjectWorkspace:
    @classmethod
    def create(cls, root: Path, source: Path,
               constraints: FabricationConstraints) -> ProjectWorkspace: ...
    @classmethod
    def open(cls, root: Path) -> ProjectWorkspace: ...
    def status(self) -> WorkspaceStatus: ...
    def apply(self, operation: VerifiedOperation, *, message: str,
              prompt: str | None = None) -> ApplyResult: ...
    def import_artifact(self, source: Path, *, message: str,
                        prompt: str | None = None) -> ApplyResult: ...
    def create_branch(self, name: str, *, from_ref: str = "HEAD",
                      checkout: bool = False) -> Revision: ...
    def checkout(self, ref: str) -> Revision: ...
    def history(self, ref: str = "HEAD") -> tuple[Revision, ...]: ...
    def compare(self, before: str, after: str) -> list[dict[str, object]]: ...
    def export(self, destination: Path, ref: str = "HEAD") -> ArtifactInfo: ...
```

`mutation.py` owns the verified edit vocabulary and byte-preserving mutation
policy. It locates one unambiguous XDX 1.220 object, validates its established
Cube or Sphere metamorph signature, formats numbers at the known precision,
replaces only the allowed record tokens, audits the structural diff, and
requires an exact parser round trip.

```python
@dataclass(frozen=True, slots=True)
class ObjectMutation:
    object_name: str
    scale: Vector3 | None = None
    rotation: Vector3 | None = None
    position: Vector3 | None = None
    color_density: Decimal | None = None
    face_warp: Decimal | None = None

@dataclass(frozen=True, slots=True)
class CenteredRowMutation:
    spacing: Decimal
    center: Vector3 = Vector3.zero()

VerifiedOperation = ObjectMutation | CenteredRowMutation

def apply_verified_mutation(data: bytes,
                            operation: VerifiedOperation) -> MutationResult: ...
```

The CLI parses transport values into these domain types and prints JSON. It
does not know the database schema, record locators, decimal formats, or branch
rules. Existing generation commands remain unchanged.

## Synthesis decision

The SQLite design is the base because it hides crash recovery, graph queries,
branch updates, and consistency checks behind one domain interface. The
alternative JSONL design contributed content-addressed native artifacts and an
append-only conceptual history, but its separate mutable refs would require
custom transaction and recovery rules. A single monolithic project file was
rejected because it would hide the native `.xxp` artifacts and make manual
XenoDream editing awkward.

## Tradeoffs accepted

- We accept an internal SQLite database in exchange for atomic revision and
  branch state.
- We accept that identical native bytes can be reused by multiple revisions in
  exchange for deduplicated, independently hash-verifiable artifacts.
- We accept a narrow verified mutation vocabulary in exchange for preserving
  the existing evidence boundary.
- We accept that fabrication constraints are recorded but not yet enforced in
  exchange for establishing the state needed by the next validation milestone.

## Alternatives considered

- JSONL events plus JSON refs exposes transaction ordering and recovery policy
  to several modules, creating a shallower interface.
- A mutable working `.xxp` with backup copies makes current state convenient
  but weakens provenance and branch semantics.
- Storing artifacts as database blobs gives one transactional file but hides
  the editable native projects from users and XenoDream.

## Open questions and risks

- Should later revisions sign or externally timestamp research artifacts?
- When the general scene model arrives, can its operation serialization remain
  compatible with the initial typed mutation records?
- Which fabrication constraints should become enforced policy rather than
  recorded intent in the next milestone?

## Next implementation step

Implement and test the verified mutation engine before connecting it to the
workspace transaction layer.
