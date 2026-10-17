# M24: XenoDream scene description

## Usage

```powershell
xenosculpt project describe .\sculpture.xsp
xenosculpt project describe .\sculpture.xsp --ref alternate
```

The command returns a revision-bound JSON description of the XenoDream scene:
persisted holon IDs, current section positions, literal group references, transforms,
ordered metamorphs, verified constructor recognition, and the existing edits
that are safe for each object. Unsupported records remain visible and
read-only.

```python
workspace = ProjectWorkspace.open("sculpture.xsp")
scene = workspace.describe(ref="HEAD")
for node in scene.nodes:
    print(node.id, node.name, node.constructor, node.allowed_operations)
```

Existing name-targeted mutation commands continue to work. After M24, a known
Cube or Sphere may be edited even when an unrelated object in the same project
is not recognized. Unknown neighbors remain byte-identical.

## Decision

Add one XenoDream-owned, read-first semantic layer in
`xenodream_xxp.scene`. It projects a lossless `Document` into immutable scene
values without serializing or normalizing the project. `ProjectWorkspace`
binds that description to an exact revision and verified artifact hash. The
existing mutation engine reuses the same node recognition instead of building
a separate closed-world object list.

This milestone does not add, delete, reorder, duplicate, or reparent holons. It
does not broaden the natural-language planner, add new constructors, or change
native validation. Those layers depend on the scene identity established here.

The shared `xenosculpt.core` remains unchanged. Holons and metamorphs are not a
cross-application abstraction: ComfyUI owns workflow graphs and MoI owns CAD
geometry.

## Domain model

`src/xenodream_xxp/scene.py` owns these public immutable values:

```python
class Recognition(StrEnum):
    VERIFIED = "verified"
    OBSERVED = "observed"
    UNKNOWN = "unknown"

class SceneOperation(StrEnum):
    SET_SCALE = "set-scale-v1"
    SET_ROTATION = "set-rotation-v1"
    SET_POSITION = "set-position-v1"
    SET_COLOR_DENSITY = "set-color-density-v1"
    SET_FACE_WARP = "set-face-warp-v1"
    APPLY_SPHERE_PROFILE = "apply-sphere-profile-v1"
    APPLY_CYLINDER_PROFILE = "apply-cylinder-profile-v1"

@dataclass(frozen=True, slots=True)
class SceneBinding:
    revision_id: str
    artifact_sha256: str

@dataclass(frozen=True, slots=True)
class SceneNode:
    id: int | None
    holon_index: int
    section_occurrence: int
    section_ordinal: int
    type_code: int | None
    name: str | None
    group_id: int | None
    constructor: str | None
    recognition: Recognition
    transform: SceneTransform | None
    metamorphs: tuple[SceneMetamorph, ...]
    allowed_operations: tuple[SceneOperation, ...]
    write_blockers: tuple[str, ...]

@dataclass(frozen=True, slots=True)
class SceneDescription:
    binding: SceneBinding
    xdx_version: str | None
    declared_holon_count: int | None
    nodes: tuple[SceneNode, ...]
    diagnostics: tuple[SceneDiagnostic, ...]
    schema: str = "xenosculpt-xenodream-scene/v1"
```

`SceneTransform` contains optional scale, rotation, and position vectors.
`SceneMetamorph` contains its numeric suffix, section occurrence, literal style
and count, ordered parameters, resolved operation name, and `schema_verified`
status.
`SceneDiagnostic` contains a stable code, message, holon index, and section
occurrence when available.

The JSON form has exactly these top-level keys: `schema`, `binding`,
`xdx_version`, `declared_holon_count`, `nodes`, and `diagnostics`. Binding has
`revision_id` and `artifact_sha256`. Optional facts are emitted as JSON null;
Decimals are emitted as native token strings. Nodes follow physical Holon
section order, metamorphs follow physical section order, parameters follow
token order, operations follow enum order, and diagnostics have deterministic
code/location order.

Transforms use `Decimal`, not binary floats. Metamorph parameters retain their
raw token text and expose names only when the packaged registry verifies the
exact version/style/count shape. Persisted `ID` is distinct from
`holon_index`, section occurrence, and physical ordinal; names are presentation
and current compatibility locators,
not identity.

`describe_xdx_scene(data, binding)` parses once, exact-roundtrips the bytes,
indexes holon and metamorph sections, derives conservative recognition, and
returns diagnostics for partial or contradictory structure. Unknown styles,
type codes, missing optional fields, duplicate names, unresolved group IDs,
and count mismatches do not disappear. They suppress only the capabilities
whose exact preconditions they violate.

Non-XDX input, a non-ASCII Program or Progversion header, parser roundtrip failure, and a
tampered stored artifact are fatal. Duplicate IDs, duplicate names, missing or
self-referential groups, count mismatches, duplicate sections/keys, malformed
transforms, and malformed metamorphs return diagnostics. Each issue suppresses
only operations that consume or depend on the affected fact. `GroupID` remains
the literal observed `group_id`; M24 does not
rename it to a proven parent edge. Partly understood scenes still return exit
zero.

## Recognition and writes

Scene recognition is the only authority for identifying verified Cube, Sphere,
and Cylinder record families. Recognition requires XDX 1.220, one occurrence-0
Holon section, one occurrence-0 `MM\\0`, unique Style/NumPars/Pars fields, a
constructor-role registry entry, and declared/actual token-count agreement. A
private node index exposes the current section
locator to `mutation.py`; the public model never accepts a section path as
identity.

M24 preserves every existing operation type and serialized detail. Capabilities
are derived per operation from the exact fields and token shapes the operation
consumes, not from constructor name alone. The mutation engine resolves a
requested name against every Type 1 node, rejects duplicate names even when one
match is opaque, and checks only the unique target's capability. This removes
the present failure where one isolated unknown Type 1 holon blocks a supported
target elsewhere in the project. Ambiguity involving the target or its
constructor block remains a local write blocker.

Whole-scene row and seeded-variation operations remain closed-world: every
affected object must be a currently supported constructor with the required
capability. Cylinder's measured profile operation remains supported, but M24
does not infer new Cylinder transform permissions.

The byte replacement helpers, precision rules, complete profile vectors,
parser roundtrip, and allowed-diff audit remain the write authority. The audit
compares the complete diff locator, including section and key occurrences, so a
duplicate record cannot satisfy permission intended for another occurrence.

## Public boundary

```python
class ProjectWorkspace(RevisionWorkspace):
    def describe(self, ref: str = "HEAD") -> SceneDescription: ...
```

The method resolves the ref once, verifies the content-addressed artifact, and
supplies the exact revision/hash binding. It does not write the database or
move HEAD.

`scene_description_to_dict()` owns the versioned JSON projection. The CLI only
dispatches and prints it. The existing literal `inspect` command remains
available for byte-level forensics.

## Ownership

- `xenodream_xxp.document`: exact records and byte roundtrip.
- `xenodream_xxp.scene`: scene identity, conservative semantic projection,
  constructor recognition, and advertised operations.
- `xenodream_xxp.metamorph`: versioned descriptor evidence.
- `xenodream_xxp.mutation`: authorized byte edits and diff audit.
- `xenodream_xxp.workspace`: revision binding plus XenoDream runtime evidence.
- `xenosculpt.core`: unchanged artifact/revision/ref mechanics.

This follows boundary discipline: validate wire data at the XenoDream edge and
keep trusted domain values inside the app package. It also follows model the
domain: ID, section position, name, and the literal group reference are
separate facts.
Sequence verifiable units requires the read model before structural writes.

## Compatibility and proof

- No database migration. Existing schema-v3 workspaces and revision IDs remain
  unchanged.
- Existing name-targeted operations must produce identical bytes, details, and
  revision IDs.
- Description is read-only and never normalizes an artifact.
- Known targets remain editable beside opaque nodes; opaque bytes remain exact.
- Duplicate names, sections, IDs, or constructor ownership never become an
  accidental write target.
- Row/variation still reject scenes containing unsupported participants.
- Original fixtures and available corpus projects exact-roundtrip.
- `project describe --ref` binds to a non-HEAD revision without checkout.
- Tampered content-addressed artifacts fail before description.
- Full XenoDream, architecture, ComfyUI, and MoI tests run on every milestone.
- `scripts/verify_reference.py` and packaged CLI help/smoke remain green.

Live ComfyUI and MoI checks run after structural editing, multi-operation
planning, and fabrication milestones. Their cheap unit and isolation gates run
continuously.

## Layered continuation

1. M24: scene description and target-local recognition.
2. M25: evidence-backed add, duplicate, remove, reorder, and group operations
   for the current Cube/Sphere/Cylinder vocabulary.
3. M26: pinned XenoDream installation identity, serialized native access, and
   named preview/review validation profiles. Low-density evidence never implies
   fabrication suitability.
4. M27: promote RoundCube, Torus, Pipe, Cog, and SpiralShell individually
   through native construction and mesh evidence.
5. M28: revision-bound, dry-runnable multi-operation plans; controlled English
   remains the deterministic fallback.
6. M29: self-intersection, thickness, orientation, support, tolerance, and
   process checks with unresolved evidence kept explicit.
7. M30: create, branch, revise, validate, open in XenoDream, and fabricate one
   original sculpture with retained evidence.

## Alternatives rejected

- A general mutable scene serializer would expose unverified allocation and
  hierarchy rules.
- More constructor-specific lookup branches would deepen the current split
  recognition problem.
- A generic scene graph in `xenosculpt.core` would weaken the proven boundary
  between XDX holons, ComfyUI graphs, and MoI CAD.
- Runtime preview/final changes in M24 would mix scene identity with executable
  pinning and shared-preference safety. They form the separate M26 layer.
- A model-backed planner now would improve phrasing without increasing safe
  capability.

## Red-flag audit

- `scene.py` is deep: one projection hides record association, registry
  binding, hierarchy checks, capability policy, and diagnostics.
- Parser records, style numbers, and token indexes do not leak through the
  public workspace API.
- The workspace method adds revision/hash guarantees rather than forwarding a
  parser call.
- Unknown nodes stay visible and suppress only their own write permissions.
- No XenoDream type enters the shared core.
- The design adds no shared writable state and no temporal load/validate/save
  pipeline for callers to coordinate.
