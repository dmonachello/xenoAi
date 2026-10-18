# M26: named XenoDream validation sessions

## Usage

Use `preview` while you edit a revision:

```powershell
xenosculpt project validate .\sculpture.xsp `
  --profile preview `
  --stl-max-dimension-mm 120
```

Use `review` when you want denser mesh evidence:

```powershell
xenosculpt project validate .\sculpture.xsp `
  --profile review `
  --stl-max-dimension-mm 120
```

The maximum dimension remains explicit because it sets physical scale. The
profile selects mesh density and timing only. `preview` and `review` establish
native evaluation and mesh facts. Neither profile establishes fabrication
suitability.

The raw command remains compatible:

```powershell
xenosculpt project validate .\sculpture.xsp `
  --stl-max-dimension-mm 120 `
  --mesh-size-percent 25 `
  --timeout-seconds 300 `
  --poll-seconds 1
```

Do not combine `--profile` with `--mesh-size-percent`, `--timeout-seconds`, or
`--poll-seconds`. Raw validation remains the experimental path.

## Decision

M26 adds an app-owned managed validation path before the next structural edit.
The path combines four facts:

- the exact supported XenoDream installation;
- one immutable validation profile;
- an explicit physical maximum dimension; and
- one content-bound workspace revision.

The existing `ProjectWorkspace.validate_native()` method and its request keys
remain unchanged. `ProjectWorkspace.validate_profile()` adds the managed path.
Both methods share one private execution and persistence implementation.

M26 does not change `xenosculpt.core`, the workspace schema, the raw runner
report, fabrication policy, ComfyUI, or MoI.

## Profiles

The code-owned profiles are:

| Name | Version | Mesh detail | Timeout | Poll |
| --- | ---: | ---: | ---: | ---: |
| `preview` | 1 | 10% | 180 seconds | 1 second |
| `review` | 1 | 50% | 600 seconds | 1 second |

`preview` uses the density that completed the M16 through M18 and M25 discovery
runs. `review` uses the calibrated current default density. Both profiles use
the caller's `stl_max_dimension_mm` value.

A profile change requires a new version. The request stores the name, version,
and a digest of the complete profile definition. A raw request never reuses a
named result, even when the numeric settings match.

## Domain model

`xenodream_xxp.validation` owns the managed policy:

```python
class ValidationProfileName(str, Enum):
    PREVIEW = "preview"
    REVIEW = "review"


@dataclass(frozen=True, slots=True)
class ValidationProfile:
    name: ValidationProfileName
    version: int
    mesh_size_percent: int
    timeout_seconds: float
    poll_seconds: float
    definition_sha256: str


@dataclass(frozen=True, slots=True)
class XenoDreamInstallation:
    executable: str
    file_version: str
    executable_sha256: str


@dataclass(frozen=True, slots=True)
class ResolvedValidationRequest:
    settings: MeshExportSettings
    timeout_seconds: float
    poll_seconds: float
    profile: ValidationProfile
    installation: XenoDreamInstallation


def validation_profile(name: ValidationProfileName) -> ValidationProfile: ...


def resolve_xenodream_installation(
    executable: str | Path,
) -> XenoDreamInstallation: ...


def resolve_profile_request(
    name: ValidationProfileName,
    *,
    stl_max_dimension_mm: int,
    executable: str | Path,
) -> ResolvedValidationRequest: ...
```

The first supported installation is XenoDream X file version `1.22.0.0` with
SHA-256
`1674590ed60cea95cfeef076dfdafce4384fb86f118f087c42e23fd9429f1b6e`.
The hash comes from the XDX 1.220 registry. A path is evidence, not authority.

`resolve_profile_request()` rejects a wrong version or hash before it starts a
process, creates a run directory, reads shared preferences, or writes a
validation row.

## Session guard

Named validation acquires a per-user Windows named mutex for XenoDream's shared
mesh-export preference domain. Windows releases the mutex if the caller exits.
A cache hit does not acquire the mutex.

After it acquires the mutex, the managed path enumerates Windows processes. It
refuses to run if another `XenoDreamX.exe` process exists. It never attaches to,
drives, or terminates a process that it did not create. The refusal occurs
before run-directory creation and preference access.

M26 does not restore preferences. XenoDream persists the requested maximum
dimension and density after validation. Restoration needs separate evidence
that a write after XenoDream exits is durable and cannot race a newly opened
interactive session. The report continues to record the values before and
after the run.

The raw path keeps its current behavior. It does not require the supported
installation, the mutex, or an idle application session. This preserves the
experimental API and all existing request keys.

## Workspace API and cache identity

```python
class ProjectWorkspace(RevisionWorkspace):
    def validate_profile(
        self,
        profile: ValidationProfileName,
        *,
        stl_max_dimension_mm: int,
        ref: str = "HEAD",
        executable: str | Path = DEFAULT_XENODREAM_EXECUTABLE,
    ) -> NativeValidation: ...

    def validate_native(
        self,
        *,
        ref: str = "HEAD",
        executable: str | Path = DEFAULT_XENODREAM_EXECUTABLE,
        settings: MeshExportSettings = MeshExportSettings(),
        timeout_seconds: float = 600,
        poll_seconds: float = 1,
    ) -> NativeValidation: ...
```

The named request adds `profile` and `installation` objects to the existing
request JSON in `validations.settings_json`. The profile object contains its
name, version, digest, timeout, and poll interval. The installation object
contains its file version and executable hash. The effective mesh settings
remain in the existing `settings` object.

The request key covers the revision, artifact, effective settings, installation,
profile, and runner schema. The runner remains `xenodream-batch-stl/v2`.
Successful named requests can reuse only successful named evidence with the
same complete identity.

No SQLite migration is needed. Old rows have no profile or installation
object and remain raw evidence. The system never infers a profile name from old
numeric settings.

## CLI contract

`project validate` adds `--profile {preview,review}`. The parser uses `None` as
the internal default for the three profile-owned raw flags so that it can detect
conflicts. When `--profile` is absent, the handler restores the existing raw
defaults of 50%, 600 seconds, and one second. The existing default maximum
dimension remains 250 mm for raw validation.

When `--profile` is present, `--stl-max-dimension-mm` is required. The handler
rejects profile-owned overrides and calls `validate_profile()`.

The output keeps the `NativeValidation` JSON shape. Named requests appear in
the existing `settings` field. Exit status remains compatible: zero requires
`basic_mesh_valid`. A separated sculpture can therefore report
`outcome="succeeded"` and `evaluates_to_3d=true` while the command exits one
because the mesh has multiple components.

## Module ownership

- `xenodream_xxp.validation` owns profile definitions, installation admission,
  request resolution, the named mutex, and process discovery.
- `xenodream_xxp.native_export` keeps the existing owned-process UI automation
  and raw v2 report.
- `xenodream_xxp.workspace` binds requests to revisions, caches successful
  evidence, retains meshes, and writes validation rows.
- `xenodream_xxp.cli` owns syntax, conflict checks, JSON, and exit codes.
- `xenosculpt.mesh` remains the app-neutral STL inspector.
- `xenosculpt.core`, ComfyUI, and MoI remain unchanged.

## Verification sequence

1. Add failing tests for the two profile definitions, profile digests, explicit
   physical maximum, and invalid profile or raw-setting combinations.
2. Add installation tests for the supported file version and hash. Prove that a
   mismatch stops before the exporter runs.
3. Pin a golden raw request payload and request key. Refactor workspace
   validation through one private method without changing that golden result.
4. Add named workspace tests for request identity, cache reuse, preview-review
   separation, raw-profile separation, unchanged `HEAD`, and rejection before a
   validation row is written.
5. Add deterministic guard tests. Prove mutex contention and preexisting process
   refusal without touching run files or the exporter.
6. Run the full suite, `scripts/verify_reference.py`, import-isolation tests,
   packaged help, and `git diff --check`.
7. Build the packaged executable. Run `preview` and `review` against the same
   M25 revision and the same maximum dimension. Retain installation, profile,
   source hash, cleanup, settings, mesh, bounds, and timing evidence. Require
   review to produce more triangles. Do not require identical STL bytes.
8. Repeat the packaged MoI create, reopen, and STL proof. Run the packaged
   ComfyUI proof if its server is available. Otherwise, record the checked
   endpoints and make no fresh-live claim.

## Compatibility requirements

- Raw Python and CLI validation keep their signatures, defaults, request keys,
  JSON, cache behavior, report schema, and preference behavior.
- Existing workspace schema-v3 databases and validation IDs remain unchanged.
- Named validation never moves `HEAD` or edits the native artifact.
- A rejected installation or session writes no validation row.
- Both profiles keep `fabrication_suitable=false`.
- No XenoDream runtime type enters the shared core or another app package.

## Next composition layer

After M26, capture the controlled `Group1, Cube2` to
`Group1, Cube2, Sphere3` transition required by M25. Then add the bounded
Sphere append with the existing pinned target block and reverse byte audit.
Validate the result with both M26 profiles at one physical maximum.

## Alternatives and tradeoffs

### Add Sphere first

The final Cube-Sphere profile is native-accepted, but the exact interactive add
transition was not retained. M26 fixes the validation path that every later
structural operation needs. Sphere append follows after one controlled
transition.

### Put maximum dimension in each profile

This would make `review` change physical size as well as detail. The calibrated
evidence shows that these controls are independent. The caller therefore owns
physical maximum dimension.

### Restore preferences

This looks courteous but is not yet safe. A restore can race a user who opens
XenoDream after the owned process exits. M26 serializes cooperating runs,
refuses an existing session, records the persistent effect, and does not claim
restoration.

### Replace raw validation

Raw controls produced the current evidence and remain useful for experiments.
The managed path adds stable product policy without removing those controls.

### Put profiles in shared core

XenoDream's density control, executable identity, Windows UI session, and
preferences do not apply to ComfyUI or MoI. Shared revision storage remains the
correct common layer.

## Red-flag audit

- **Shallow module:** clear. `validation` hides profile identity, executable
  admission, mutex ownership, process discovery, and request resolution.
- **Information leakage:** clear. Windows mutex names and process APIs stay out
  of CLI, workspace storage types, and the shared core.
- **Temporal decomposition:** clear. Callers request one validation. They do not
  coordinate the lock, process inventory, exporter, cleanup, or evidence write.
- **Pass-through service:** clear. `validate_profile()` resolves and enforces a
  closed policy that raw callers cannot override.
- **Premature generalization:** clear. There is no generic application runtime,
  installation registry, or validation profile in `xenosculpt.core`.
- **Capability overclaim:** clear. The names are `preview` and `review`, not
  `final`. Neither name changes fabrication policy.
- **Compatibility erosion:** clear. Raw validation retains its existing request
  shape and implementation contract.
