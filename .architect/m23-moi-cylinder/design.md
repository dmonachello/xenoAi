# M23: native MoI cylinder proof

## Problem

M23 must prove that the shared revision core can hold a native CAD artifact
authored by a third application. MoI's `.3dm` format stays opaque to
XenoSculpt. The verified write path is an owned MoI process running generated
JavaScript, not direct binary mutation. The first slice must create one useful
closed solid, preserve the editable `.3dm`, reopen it in a fresh process, and
retain a measured STL without changing the MoI installation or user files.

The installed target is the stable MoI 4 build at
`C:\Program Files\MoI 4.0\MoI.exe`, version `4.0.2020.1222`. Installed MoI 5
betas are separate targets and are not accepted by this milestone.

## Usage

Create a 15 mm radius by 40 mm high cylinder workspace:

```powershell
xenosculpt moi create-cylinder .\demo-cylinder.msp `
  --radius-mm 15 --height-mm 40 `
  --moi-executable "C:\Program Files\MoI 4.0\MoI.exe"
```

The command returns only after MoI has saved the native file, a second fresh
MoI process has reopened that exact file, and the reopened document has
exported a valid STL with the expected dimensions.

```powershell
xenosculpt moi status .\demo-cylinder.msp
xenosculpt moi export .\demo-cylinder.msp .\demo-cylinder.3dm
xenosculpt moi export-stl .\demo-cylinder.msp .\demo-cylinder.stl
```

M23 does not expose separate create, validate, and retain stages. The caller
asks for one verified native project or gets no workspace.

The Python entry point has the same shape:

```python
from decimal import Decimal
from xenosculpt.moi import CylinderSpec, MoiProject

project = MoiProject.create_cylinder(
    "demo-cylinder.msp",
    CylinderSpec(radius_mm=Decimal("15"), height_mm=Decimal("40")),
    moi_executable=r"C:\Program Files\MoI 4.0\MoI.exe",
)
assert project.status().evidence.mesh.triangle_count > 0
```

## Shape

### Public domain values

```python
@dataclass(frozen=True, slots=True)
class CylinderSpec:
    radius_mm: Decimal
    height_mm: Decimal

@dataclass(frozen=True, slots=True)
class MoiInstallation:
    executable: Path
    file_version: str
    executable_sha256: str

@dataclass(frozen=True, slots=True)
class MoiEvidence:
    schema: str
    installation: MoiInstallation
    request_sha256: str
    create_script_sha256: str
    reopen_script_sha256: str
    native_sha256: str
    native_bytes: int
    stl_sha256: str
    stl_bytes: int
    mesh: StlReport

@dataclass(frozen=True, slots=True)
class MoiStatus:
    root: str
    application_id: str
    document_kind: str
    head: Revision
    cylinder: CylinderSpec
    evidence: MoiEvidence
```

`CylinderSpec` accepts finite positive decimals within a documented automation
range. The cylinder is fixed at the world origin, aligned to positive Z, named
`Cylinder1`, and measured in millimetres. M23 exposes no raw JavaScript, factory
indices, object handles, or mesh option strings.

### Native boundary

```python
MOI_VERSION = "4.0.2020.1222"

@dataclass(frozen=True, slots=True)
class NativeCylinderResult:
    native_data: bytes
    stl_data: bytes
    evidence: MoiEvidence

class MoiCylinderRuntime:
    @classmethod
    def for_executable(cls, executable: str | Path) -> "MoiCylinderRuntime": ...

    def create_and_verify(
        self,
        spec: CylinderSpec,
        *,
        timeout_seconds: float = 120,
    ) -> NativeCylinderResult: ...
```

`create_and_verify()` is one deep operation. It creates a unique disposable
directory and renders two fixed scripts using canonical numeric values and
internally selected paths.

The first script sets millimetre units, creates one cylinder through MoI's
factory API, names it, saves `model.3dm`, and exits. The second script runs in a
fresh process with a fresh isolated INI, opens `model.3dm`, exports
`validation.stl` with one pinned no-dialog tessellation profile, and exits.

The runtime owns both process trees. It launches the exact inspected executable
with hidden windows, tracks PIDs, waits for bounded completion, and terminates
only owned processes on timeout. A zero exit code is not success by itself.
The native and STL outputs must exist, stay inside the run directory, satisfy
size limits, and hash correctly. The STL must pass the existing basic topology
predicate. Its dimensions must match `2r × 2r × h` within the tolerance defined
by the pinned mesh profile.

The runtime does not call `moi_commandprocessor.exe` directly. That executable
is part of MoI's internal worker model. Child cleanup is based on ownership of
the launched MoI process tree.

### Workspace boundary

```python
MOI_APPLICATION = ApplicationIdentity(
    name="moi3d",
    document_kind="moi3d/3dm-v5",
    artifact_suffix=".3dm",
)

class MoiProject(RevisionWorkspace):
    @classmethod
    def create_cylinder(
        cls,
        root: str | Path,
        spec: CylinderSpec,
        *,
        moi_executable: str | Path,
        timeout_seconds: float = 120,
    ) -> "MoiProject": ...

    @classmethod
    def open(cls, root: str | Path) -> "MoiProject": ...

    def status(self) -> MoiStatus: ...
    def export_stl(self, destination: str | Path) -> ArtifactInfo: ...
```

Creation happens under a verified sibling staging directory. Only after both
native runs and all output checks pass does the workspace initialize shared
history, add its MoI-owned evidence row, retain the STL by hash, and atomically
rename the staging directory to the requested `.msp` path. A crash or rejected
output leaves no published workspace.

The initial revision operation is `moi-create-cylinder-v1`. Revision details
contain the canonical cylinder request and evidence ID. The `.3dm` is the
primary revision artifact. The STL is derived evidence under
`run-artifacts/<sha256>.stl`; it never replaces the editable native file.

M23 adds one application-owned table keyed by revision ID. `status()` rechecks
the evidence JSON hash, native artifact binding, retained STL path containment,
STL length and hash, and mesh report before returning success.

### Modules

```text
src/xenosculpt/moi/
  __init__.py       public CylinderSpec and MoiProject
  model.py          immutable public values and validation
  runtime.py        MoI version pin, inline scripts, owned processes, output checks
  workspace.py      staged publication, revision binding, retained evidence
  cli.py            create-cylinder, status, export, export-stl

src/xenosculpt/mesh.py
  application-neutral STL report and inspection
```

The STL parser currently lives under `xenodream_xxp.mesh` even though it has no
XenoDream dependency. M23 moves its implementation to `xenosculpt.mesh` and
keeps compatibility imports in `xenodream_xxp.mesh`. That lets MoI reuse the
mesh checker without reversing the application dependency direction.

The top-level CLI adds one explicit `moi` branch. Three installed applications
still do not justify a dynamic plugin registry.

## Safety and failure behavior

- Require the exact MoI 4 file version and retain the executable hash.
- Use a unique run directory and isolated INI for each process.
- Generate scripts from fixed templates. User text never becomes JavaScript.
- Never overwrite an existing workspace or destination export.
- Never read or write the user's `.3dm` corpus.
- Treat output files and mesh measurements as the completion signal.
- Kill only the owned process tree after timeout.
- Publish the workspace atomically after every required file and database row
  exists.
- Treat `.3dm` bytes as opaque. M23 makes no claim about deterministic MoI
  serialization or arbitrary document semantics.
- Treat the STL as geometry evidence, not printability approval.

## Tests and live proof

Pure tests cover decimal bounds, executable admission, JavaScript escaping,
strict evidence decoding, fake-runner failure modes, staged publication,
application identity, evidence tampering, mesh tampering, CLI dispatch, and
legacy XenoDream and ComfyUI behavior.

The first live gate runs before workspace code is filled in. A disposable
script must create one cylinder with MoI 4, save `.3dm`, exit, reopen the exact
file in a second fresh process, and export STL without a dialog. If that gate
fails, M23 stops rather than shipping opaque file storage as a MoI integration.

The packaged proof then creates the workspace outside the repository, exports
both retained artifacts, and repeats the same request twice. It records the MoI
version and executable hash, script hashes, request hash, native hashes, STL
hashes, process durations, and mesh reports. Native byte equality is an
observation, not a success requirement.

## Synthesis decision

The smallest-surface candidate is the base because one verified creation call
hides the full native protocol and publishes no partial workspace. The runner
candidate contributed explicit owned process-tree cleanup and the requirement
that the validation STL come from a reopened native file. Its durable pending
workspace was rejected because the initial operation is short and can publish
atomically; public resume semantics would add states without preserving a valid
revision. The CAD candidate contributed opaque `.3dm` admission and semantic
honesty, but manual import, recipe revision, and recipe comparison are deferred
until the creation path proves stable object and serializer behavior.

## Tradeoffs accepted

- We accept create-only history in exchange for proving the native CAD boundary
  before inventing object identity and mutation semantics.
- We accept one fixed cylinder in exchange for a closed solid with measurable
  physical dimensions.
- We accept synchronous bounded execution in exchange for a public interface
  without caller-coordinated run stages.
- We accept MoI-specific evidence in exchange for keeping native process details
  out of the shared core.
- We accept possible byte differences between equivalent `.3dm` saves in
  exchange for letting MoI remain the only native writer.

## Alternatives considered

A general CAD adapter lost because M23 cannot parse or safely mutate arbitrary
`.3dm` scenes. It would expose untyped handles while hiding little policy.

A durable pending workspace with `resume-create` lost because no valid native
revision exists until creation and reopen checks finish. Atomic staging gives
the caller a simpler invariant: the workspace either exists and is complete or
does not exist.

Manual `.3dm` import plus in-place cylinder editing lost because XenoSculpt
cannot yet prove that a MoI resave preserves every unrelated CAD property.

Using MoI 5 lost because three different beta builds are installed. "MoI 5" is
not one reproducible target. Stable V4 is pinned and matches the existing local
corpus producer.

## Open questions and risks

- Does the external script launch reliably execute and exit under MoI 4?
- Does an isolated INI also exclude user startup scripts and plugins?
- Which fixed tessellation profile gives a fast cylinder proof without making
  the dimension tolerance meaningless?
- Does the MoI child worker always remain attributable to the owned parent?
- Does the current license state avoid first-run or activation dialogs?

## Red-flag audit

`MoiCylinderRuntime.create_and_verify()` is a deep operation. Callers do not
coordinate transport stages. Script templates, factory indices, INI settings,
mesh options, temporary paths, and evidence SQL each have one owner. The module
split follows domain knowledge rather than execution order. No generic CAD
scene, generic run table, or pass-through adapter is introduced.

## Next implementation step

Prove the disposable MoI 4 script, save, reopen, STL export, and owned-process
cleanup path before adding workspace or CLI code.
