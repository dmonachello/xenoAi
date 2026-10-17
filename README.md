# XenoSculpt

XenoSculpt is an evidence-based toolkit for XenoDream X 1.220 native project
files. It can inspect and preserve `.xxp` files, generate a small set of
verified projects, keep revision history, apply measured mutations, and ask
XenoDream to export a mesh for validation.

The project is intentionally narrow. It does not claim to be a general
XenoDream file editor, a slicer, or a printability checker.

## Architecture and future applications

XenoDream is the first application integration, not the project-wide data
model. The `xenosculpt.core` package owns content-addressed artifacts,
revisions, branches, history, and atomic updates. The
`xenodream_xxp.adapter.XenoDreamArtifactAdapter` owns XDX parsing, verified
native mutations, and XDX comparison. XenoDream execution, STL validation, and
fabrication assessment remain application-specific capabilities.

Future ComfyUI and MoI integrations can reuse the revision core while keeping
their own document formats and operations. The project does not force workflow
graphs, CAD solids, XenoDream holons, images, and meshes into one scene model.
See [the multi-application core design](.architect/m21-multi-app-core/design.md)
for the current boundary and its deliberate limits.

## What works

- Lossless parsing, inspection, round trips, and structural diffs for observed
  XDX 1.220 files.
- Deterministic generation of one to three cubes, one sphere, one Cylinder,
  and the verified cube-plus-sphere project.
- Centered rows for the supported cube and sphere sequences.
- Persistent `.xsp` workspaces with immutable native artifacts, branches,
  revision history, prompts, and fabrication constraints.
- Verified cube and sphere transforms, deterministic seeded variations, and
  measured Sphere and Cylinder metamorph profiles.
- A controlled-English `project prompt` command that maps one exact sentence
  to one existing typed operation. It runs offline and does not call a language
  model.
- Supervised XenoDream export with binary STL inspection and revision-attached
  validation reports.
- Revision-bound fabrication assessments that evaluate basic mesh validity and
  current-orientation build-volume fit without treating missing checks as a
  pass.
- Optional STL solidification that creates a derived mesh without changing the
  editable native project.

## Current limits

- Generated native projects target XenoDream X 1.220.
- The generator supports only the object sequences listed above.
- Prompt planning accepts a documented grammar, not unrestricted natural
  language. Vague, relative, and multi-operation requests fail.
- Metamorph writes use complete, measured profiles. Descriptor ranges do not
  authorize arbitrary parameter values.
- Basic mesh validation checks structure, finite coordinates, degeneracy, edge
  incidence, winding, connected components, dimensions, and signed volume. It
  does not check self-intersections, minimum wall thickness, supports,
  tolerances, or process suitability.
- Generated and mutated projects remain `fabrication_suitable: false` until
  every required check passes. The current policy cannot pass because exact
  self-intersection, minimum-feature, and process-specific checks do not exist.
- Native evaluation requires Windows and an installed copy of XenoDream X.
  XenoDream is not included in this repository.

## Install from source

XenoSculpt requires Python 3.11 or later.

```powershell
git clone https://github.com/dmonachello/xenoAi.git
cd xenoAi
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

The Python package installs the `xxp` command. Run `xxp --help` to list all
commands.

## Create and revise a native project

This example generates a default Cylinder, records it in a workspace, applies
a measured profile through the prompt planner, and exports the active revision.

```powershell
New-Item -ItemType Directory -Force output | Out-Null

xxp generate-cylinder output/cylinder.xxp
xxp inspect output/cylinder.xxp

xxp project init output/cylinder.xsp output/cylinder.xxp `
  --process FDM --build-volume 220 220 250 --min-feature-mm 1.2

xxp project prompt output/cylinder.xsp `
  "apply Cylinder profile bevel-25-front to object Cylinder2" `
  --message "apply measured front bevel"

xxp project export output/cylinder.xsp output/cylinder-bevel.xxp
```

`project prompt` records the original prompt, the matched grammar rule, the
planner identity, and the source revision hash. The workspace rejects the plan
if `HEAD` changes before application. See
[deterministic prompt planning](docs/m19-natural-language-planner.md) for every
accepted sentence form.

## Use explicit workspace operations

The prompt command calls the same typed operations exposed by the explicit
commands. Use the explicit commands when you already know the operation.

```powershell
xxp project mutate output/project.xsp --object Cube2 `
  --scale 25 50 100 --message "elongate cube"

xxp project row output/project.xsp --spacing 90 `
  --message "arrange objects"

xxp project evolve output/project.xsp --seed 17 --strength 0.5 `
  --message "seeded variation"

xxp project metamorph output/project.xsp --operation Cylinder `
  --object Cylinder2 --profile bevel-25-front `
  --message "apply measured front bevel"
```

Workspace commands also include `status`, `log`, `branch`, `checkout`,
`compare`, `import`, `export`, `validate`, and `assess`. Run
`xxp project <command> --help` for the exact arguments.

## Validate a revision in XenoDream

Install the automation dependency on the Windows computer that runs XenoDream:

```powershell
python -m pip install -e ".[automation]"
```

Then evaluate the active revision and attach the mesh report to it:

```powershell
xxp project validate output/cylinder.xsp `
  --stl-max-dimension-mm 120 --mesh-size-percent 10
```

The validator starts an isolated XenoDream process, works from a disposable
copy, exports binary STL, and cleans up the process. It does not move workspace
`HEAD` or change the native source. Mesh detail has a large effect on runtime.
Use a low percentage for discovery and increase it only when the added detail
is useful.

The default executable path is:

```text
C:\Program Files (x86)\XenoDream Software\XenoDreamX\XenoDreamX.exe
```

Pass `--executable` to `project validate` if XenoDream is installed elsewhere.

## Assess fabrication constraints

After `project validate` succeeds, assess its retained STL against the
workspace constraints:

```powershell
xxp project assess output/cylinder.xsp
```

The assessment records the exact revision, validation, mesh hash, policy, and
constraints. It checks the current basic mesh predicate and compares measured
STL dimensions with the configured build-volume axes. It does not rotate or
rescale the mesh.

The command returns exit code `1` for both `fail` and `incomplete`. An
`incomplete` result means that the available checks passed, but required
evidence is missing. It is not fabrication approval. See
[fabrication assessments](docs/m20-fabrication-assessment.md) for the check
statuses and selection options.

## Inspect and compare files

```powershell
xxp inspect samples/originals/20061109Sirps08.xxp
xxp inspect-metamorphs samples/originals/20061109Sirps08.xxp
xxp roundtrip samples/originals/20061109Sirps08.xxp output/roundtrip.xxp
xxp diff samples/originals/20061109Sirps08.xxp output/roundtrip.xxp
xxp validate-stl output/model.stl
```

The reference file is preserved at
[`samples/originals/20061109Sirps08.xxp`](samples/originals/20061109Sirps08.xxp).
Its provenance and hash are recorded in
[`samples/SHA256SUMS`](samples/SHA256SUMS) and the
[format evidence register](docs/format-evidence.tsv).

## Build the Windows executable

The standalone build produces `xenosculpt.exe`, which exposes the same command
tree as `xxp`.

```powershell
python -m pip install -e ".[build,fabrication]"
python scripts/build_xenosculpt.py
.\dist\xenosculpt.exe --help
```

The `fabrication` extra installs the numerical packages required by
`solidify-stl`:

```powershell
xxp solidify-stl output/model.stl output/model-solid.stl `
  --amount-mm 1.0 --voxel-mm 0.5
```

Solidification is not slicer infill and does not prove that a mesh is
printable.

## Evidence and design notes

This repository separates observed facts from writable features. A recovered
field becomes writable only after tests establish its record identity,
serialization rules, accepted values, and structural diff boundary. Geometry
claims require native XenoDream evaluation and retained mesh measurements.

Start with these documents:

- [Project direction](docs/project-direction.md)
- [Format evidence register](docs/format-evidence.tsv)
- [Reverse-engineering cross-validation](docs/rea-cross-validation.tsv)
- [Revision-attached native validation](docs/m15-native-revision-validation.md)
- [Cylinder constructor](docs/m15-cylinder-constructor.md)
- [Cylinder sweep results](docs/m16-cylinder-metamorph-sweep.md)
- [Cylinder bevel interactions](docs/m17-cylinder-bevel-interaction-sweep.md)
- [Measured Cylinder mutations](docs/m18-cylinder-metamorph-mutation.md)
- [Deterministic prompt planning](docs/m19-natural-language-planner.md)
- [Fabrication assessments](docs/m20-fabrication-assessment.md)

Generated files belong under `output/`. Do not overwrite files under
`samples/originals/`.

## Development

```powershell
python -m pip install -e ".[automation,build,fabrication]"
python -m pytest
python scripts/verify_reference.py
```

The test suite covers the parser, generators, mutation policies, revision
workspace, planner, command-line interface, mesh inspection, and automation
helpers. Live XenoDream validation requires the installed Windows application.

## License

This repository does not currently include an open-source license. Public
access does not grant permission to copy, modify, or redistribute the code.
