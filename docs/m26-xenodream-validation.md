# Validate XenoDream revisions with named profiles

Named validation profiles give repeated XenoDream checks a stable meaning.
Use `preview` during iteration and `review` when you need a denser mesh.

## Run a preview

Close every interactive XenoDream session. Then run:

```powershell
xenosculpt project validate .\sculpture.xsp `
  --profile preview `
  --stl-max-dimension-mm 120
```

`preview` version 1 uses 10% mesh detail, a 180-second timeout, and a one-second
poll interval. The maximum dimension is not part of the profile. It remains an
explicit physical-scale choice.

## Run a review

Use the same maximum dimension so that you can compare the two meshes:

```powershell
xenosculpt project validate .\sculpture.xsp `
  --profile review `
  --stl-max-dimension-mm 120
```

`review` version 1 uses 50% mesh detail, a 600-second timeout, and a one-second
poll interval.

## Read the result

The JSON retains the existing `NativeValidation` shape. A named request adds
`profile` and `installation` objects inside `settings`. These objects bind the
evidence to the profile version, profile-definition digest, XenoDream file
version, and executable hash.

`outcome: "succeeded"` and `evaluates_to_3d: true` establish that the pinned
XenoDream installation loaded and evaluated the revision. `basic_mesh_valid`
is a separate mesh predicate. It requires one connected component, so a valid
scene with separated objects can exit with status 1 even when native evaluation
succeeds.

`fabrication_suitable` remains false. Preview and review do not check exact
self-intersection, local thickness, supports, tolerances, or process rules.

## Session and preference behavior

Named validation accepts only XenoDream X file version `1.22.0.0` with the
executable hash recorded for the XDX 1.220 evidence set. A copy at another path
is accepted only when its version and bytes match.

The command acquires a per-user Windows mutex before it starts XenoDream. It
then refuses to run if another `XenoDreamX.exe` process exists. XenoSculpt does
not attach to, drive, or close a process that it did not create.

The mutex coordinates named-profile XenoSculpt commands across Windows logon
sessions for the same account. It cannot reserve XenoDream against a person or
another program launching an interactive session after the final process check,
so keep XenoDream closed until validation finishes. Raw validation retains its
historical unmanaged session behavior.

XenoDream stores STL maximum dimension and mesh detail in shared user
preferences. Those values persist after validation. M26 does not restore them
because a restore could race a new interactive session. The native report
records the values before and after each run.

## Use raw settings

Use raw settings for evidence work that no named profile represents:

```powershell
xenosculpt project validate .\sculpture.xsp `
  --stl-max-dimension-mm 120 `
  --mesh-size-percent 25 `
  --timeout-seconds 300 `
  --poll-seconds 1
```

Do not combine `--profile` with `--mesh-size-percent`, `--timeout-seconds`, or
`--poll-seconds`. Raw validation retains its historical executable, session,
cache, and preference behavior.

## Current limits

- Only the pinned XenoDream X 1.220 executable is accepted for named profiles.
- Profile definitions are immutable. A setting change requires a new version.
- A cache hit reuses only successful evidence with the same revision, artifact,
  installation, profile, effective settings, and runner schema.
- Named validation does not change `HEAD` or the native `.xxp` artifact.
- Named validation does not approve a mesh for fabrication.
