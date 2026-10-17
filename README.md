# XenoDream X `.xxp` tools

The current roadmap is
[conversational control for physical sculpture](docs/project-direction.md).
XenoDream remains the first implementation. The project will preserve native
editability, revision history, and fabrication constraints as it grows beyond
the current bounded generator.

This repository starts with a conservative reader and writer for XenoDream X
parameter files. The current milestone preserves observed syntax. It does not
claim that static parsing proves XenoDream accepts a file.

The supplied reference is preserved at
`samples/originals/20061109Sirps08.xxp`. Its provenance and hash are recorded in
`samples/SHA256SUMS` and `docs/format-evidence.tsv`.

## Development

```powershell
python -m pip install -e .
pytest
python scripts/verify_reference.py
xxp inspect samples/originals/20061109Sirps08.xxp
xxp inspect-metamorphs samples/originals/20061109Sirps08.xxp
xxp roundtrip samples/originals/20061109Sirps08.xxp output/roundtrip.xxp
xxp diff samples/originals/20061109Sirps08.xxp output/roundtrip.xxp
xxp validate-stl output/model.stl
xxp solidify-stl output/model.stl output/model-solid.stl `
  --amount-mm 1.0 --voxel-mm 0.5
xxp generate-cube output/generated_cube.xxp
xxp generate-sphere output/generated_sphere.xxp
xxp generate-cylinder output/generated_cylinder.xxp
xxp generate-two-cubes output/generated_two_cubes.xxp
xxp generate-three-cubes output/generated_three_cubes.xxp
xxp generate-cube-sphere output/generated_cube_sphere.xxp
xxp generate-row output/generated_row.xxp cube sphere --spacing 100
```

## Standalone Windows executable

Build the command without requiring Python on the test machine:

```powershell
python -m pip install -e ".[build,fabrication]"
python scripts/build_xenosculpt.py
dist\xenosculpt.exe --help
```

Install `.[fabrication]` before running from Python or include those dependencies
when building the standalone executable. `solidify-stl` adds geometric material
to a derived STL. It leaves the editable native project and source mesh alone.
The amount and voxel size are millimetres. The operation is not slicer infill,
and a successful result is not by itself a printability guarantee.

The executable exposes the same evidence-backed commands as `xxp`, including
native project generation, persistent project revisions, controlled mutations,
and `validate-stl`. Natural-language planning will build on the typed revision
interface; unrestricted text-to-scene interpretation is not yet available.

## Persistent projects and controlled mutations

Create a workspace from any existing native XDX project. The source is never
modified. Native artifacts are stored by SHA-256, while SQLite records the
revision graph, branches, prompts, and fabrication constraints.

```powershell
xenosculpt project init sculpture.xsp output/smoke_test.xxp `
  --process FDM --build-volume 220 220 250 --min-feature-mm 1.2

xenosculpt project mutate sculpture.xsp --object Cube2 `
  --scale 25 50 100 --message "elongate cube" `
  --prompt "make the cube taller"

xenosculpt project branch sculpture.xsp alternate --checkout
xenosculpt project mutate sculpture.xsp --object Cube2 `
  --face-warp 0.25 --message "warp the faces"
xenosculpt project evolve sculpture.xsp --seed 17 --strength 0.5 `
  --message "seeded physical-form variation"
xenosculpt project metamorph sculpture.xsp --object Sphere2 `
  --profile cushion-core --message "measured cushion form"
xenosculpt project metamorph sculpture.xsp --operation Cylinder `
  --object Cylinder2 --profile bevel-25-front `
  --message "measured front bevel"
xenosculpt project validate sculpture.xsp `
  --stl-max-dimension-mm 120 --mesh-size-percent 50
xenosculpt project compare sculpture.xsp main alternate
xenosculpt project checkout sculpture.xsp main
xenosculpt project export sculpture.xsp output/restored-main.xxp
```

Other commands are `project status`, `project log`, `project row`,
`project evolve`, `project metamorph`, and `project import`. Import records a
model edited manually in XenoDream as a new revision. Checkout accepts a branch
name or an unambiguous revision prefix. Export refuses to overwrite an existing
file.

`project validate` evaluates a disposable copy of the selected revision in an
isolated XenoDream process, exports binary STL, and attaches the native and mesh
report to that revision. It does not advance HEAD or change the native model.
Meshes are stored by SHA-256 under the workspace. The report distinguishes
native acceptance, production of 3D geometry, basic mesh topology, and
fabrication suitability; the last remains false until process-specific checks
exist.

Controlled object mutation currently follows the same evidence boundary as the
generator. Cubes support scale, rotation, position, color density, and Face
Warp. Spheres support scale and position. A requested edit outside those rules
is rejected. Every mutation audits its structural diff and preserves all
unrelated bytes.

`project metamorph` applies one measured parameter profile. Sphere remains the
default operation. Use `--operation Cylinder` for the measured Cylinder forms.
Run the command with `--help` to list stable names. A profile replaces the
complete operation-specific metamorph vector, preventing values from a prior
profile from leaking into an unmeasured combination. The resulting revision
remains editable in XenoDream, but the command reports
`native_validation_required: true` and `fabrication_suitable: false`. It does
not turn recovered descriptor ranges into unrestricted write permission.

`generate-cylinder` is the first constructor added without a manually created
1.220 Cylinder template. Its Style 13 identity, seven parameter slots, names,
domains, and defaults come from the executable operation registry and are
reconciled with nine historical native records and installed presets. The
default project passed isolated XenoDream evaluation and basic mesh validation.
The public command currently exposes only verified transform controls. Native
sweeps measured Length, Closed Ends, Wedge, Spherical, and conditional Bevel
behavior at discovery detail. Eight exact complete states are available through
evidence-gated profiles. `Arc=180` remains unresolved, and unrestricted
Cylinder metamorph edits remain disabled. See the
[`M16 isolated sweep`](docs/m16-cylinder-metamorph-sweep.md) and the
[`M17 bevel interaction sweep`](docs/m17-cylinder-bevel-interaction-sweep.md),
then the [`M18 mutation boundary`](docs/m18-cylinder-metamorph-mutation.md).

`project evolve` derives a repeatable variation from the current revision.
The same source revision, seed, and strength produce identical native bytes.
Its center-weighted sampling is informed by XenoDream's recovered metamorph
randomizer, while its mutation envelopes and PRNG are deliberately owned and
versioned by this project. It changes only verified physical-form fields:
Cube/Sphere scale and position, Cube rotation, and Cube Face Warp. It does not
claim to reproduce XenoDream's native dice or infer undocumented parameter
ranges.

`inspect-metamorphs` reports every persisted `Holon\N\MM\M` block, its Style,
declared and observed parameter counts, operation-registry match, and individual
raw tokens. For XenoDream X 1.220 Sphere and Cube records, it reports every
token's binary-recovered name and whether it is numeric or discrete. Numeric
descriptors include the native minimum, maximum, default, step, and decimal
places; discrete descriptors include the default index and choice strings.
These are read-only facts and do not authorize unvalidated mutations. Candidate
families such as Cylinder, Torus, Pipe, RoundCube, Cog, SpiralShell, and Crystal
remain identification leads, not writable generator operations.

`generate-cube` uses the evidence-gated XDX 1.220 compiler. It refuses to
overwrite an existing path. Verified controls can be supplied explicitly:

```powershell
xxp generate-cube output/elongated_cube.xxp --scale 25 50 100
xxp generate-cube output/rotated_cube.xxp --rotation 10 20 30
```

`generate-three-cubes` reproduces the controlled Group1 project containing
Cube2, Cube3, and Cube4 at X positions -75, 0, and 75. Supply `--position X Y Z`
exactly three times to change their positions. Other object counts are not yet
supported because they have not been established by controlled samples.

`generate-two-cubes` reproduces the clean Group1 project containing Cube2 and
Cube3 at X positions -50 and 50. Supply `--position X Y Z` exactly twice to
change their positions. The Python API exposes `CubeProjectSpec` for the
verified one, two, and three cube counts and rejects every other count.

`generate-sphere` reproduces the controlled Group1 and Sphere2 project.
`generate-cube-sphere` reproduces the controlled Group1 project containing
Cube2 at X -50 followed by Sphere3 at X 50. The Python API exposes
`ProjectSpec`, `CubeSpec`, and `SphereSpec`. It accepts only the five profiled
object sequences: one to three cubes, one sphere, or cube followed by sphere.
`SphereSpec` exposes only the verified scale and position controls.

`generate-row` places a supported object sequence at equal intervals on the X
axis. The row is centered at the origin by default. Use `--center X Y Z` to
move the row. The command accepts the same five object sequences as
`ProjectSpec` and rejects every other sequence.

The Python API returns a project so callers can inspect or combine it before
compilation:

```python
from decimal import Decimal

from xenodream_xxp import CubeSpec, SphereSpec, centered_x_row, compile_project

project = centered_x_row(
    (CubeSpec(), SphereSpec()),
    spacing=Decimal("100"),
)
data = compile_project(project)
```

Generated files still require an open-and-render check in XenoDream. Static
parsing and byte comparisons do not prove application acceptance.

## Experimental mesh acceptance

On Windows with XenoDream X 1.220 installed, the supervised runner can load a
generated project in a fresh, isolated XenoDream process and export binary
STL through the application's Batch Export room:

```powershell
python -m pip install -e ".[automation]"
python scripts/run_xenodream_batch_stl.py `
  output/generated_cube.xxp tmp/mesh-run `
  --stl-max-dimension-mm 250 --mesh-size-percent 50 `
  --report evidence/runtime/mesh-run.json
```

The runner never attaches to an existing XenoDream process. It uses a Windows
Job Object to guarantee cleanup, works from a disposable source copy, records
source hashes and process activity, and refuses output collisions. XenoDream
1.220 ignores programmatic edits to its visible batch destination field, so
the runner gives the disposable project a unique name and relocates only that
newly created STL from XenoDream's default output directory.

`--stl-max-dimension-mm` accepts XenoDream's recovered range of 10 through
10,000 mm. `--mesh-size-percent` accepts 1 through 100 and controls linear
sampling resolution. For the calibrated cube, doubling that percentage
multiplies triangle count by approximately four without changing physical
bounds. The runner records requested, displayed, and persisted settings and
rejects a nominal success if XenoDream did not apply them.

The report validates binary STL structure, finite coordinates, degeneracy,
edge incidence, winding consistency, connected components, dimensions, and
signed volume. Native STL coordinates are millimetres. These checks do not
establish minimum wall thickness, self-intersection freedom, support
requirements, or fabrication suitability. An exported STL must not be called
printable solely because this command succeeds. See
`docs/m5-physical-calibration.md` for the static and runtime evidence.

Generated files belong under `output/`. Never overwrite files under
`samples/originals/`.
