# XenoDream X `.xxp` tools

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
xxp roundtrip samples/originals/20061109Sirps08.xxp output/roundtrip.xxp
xxp diff samples/originals/20061109Sirps08.xxp output/roundtrip.xxp
xxp generate-cube output/generated_cube.xxp
xxp generate-sphere output/generated_sphere.xxp
xxp generate-two-cubes output/generated_two_cubes.xxp
xxp generate-three-cubes output/generated_three_cubes.xxp
xxp generate-cube-sphere output/generated_cube_sphere.xxp
xxp generate-row output/generated_row.xxp cube sphere --spacing 100
```

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
  --report evidence/runtime/mesh-run.json
```

The runner never attaches to an existing XenoDream process. It uses a Windows
Job Object to guarantee cleanup, works from a disposable source copy, records
source hashes and process activity, and refuses output collisions. XenoDream
1.220 ignores programmatic edits to its visible batch destination field, so
the runner gives the disposable project a unique name and relocates only that
newly created STL from XenoDream's default output directory.

The report validates binary STL structure, finite coordinates, degeneracy,
edge incidence, winding consistency, connected components, bounds, and signed
volume. These checks do not establish physical units, minimum wall thickness,
self-intersection freedom, support requirements, or fabrication suitability.
An exported STL must not be called printable solely because this command
succeeds.

Generated files belong under `output/`. Never overwrite files under
`samples/originals/`.
