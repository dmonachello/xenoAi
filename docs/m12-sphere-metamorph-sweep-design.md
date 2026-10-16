# Sphere metamorph sweep design

## Problem

The single-parameter probe proves that one exact XDX token can be changed,
evaluated by XenoDream, and measured as an STL. Repeating that workflow by
hand for every Sphere parameter would recreate the manual bottleneck this
project is meant to remove. The sweep must remain an investigation tool. It
must not grant normal generator write access before the results establish a
useful and safe range.

## Usage

An explicit case file records the value and why it was selected:

```json
{
  "operation": "Sphere",
  "cases": [
    {"parameter": "Waist", "value": "12", "source": "XDXSystem.xmm Sphere/Pear"},
    {"parameter": "Ovoid", "value": "2.8", "source": "user-observed native dice"}
  ]
}
```

The experiment runner prepares exact one-token variants, resumes completed
exports, retries pre-evaluation automation failures, and writes one summary:

```powershell
python scripts/sweep_metamorph_mesh.py `
  experiments/metamorph-sweeps/sphere-isolated-v1.json `
  output/sphere-isolated-v1
```

The caller supplies no token indexes, native ranges, report paths, or Windows
automation steps. The case file names semantic parameters and cites the
existing evidence that selected each value.

## Shape

`sweep_metamorph_mesh.py` owns the experiment lifecycle behind one command:

```python
def run_sweep(
    case_file: Path,
    output_directory: Path,
    *,
    attempts: int = 2,
    settings: MeshExportSettings = MeshExportSettings(100, 25),
) -> dict[str, object]: ...
```

The script validates the case schema, requires one baseline case, and rejects
duplicate parameters. It delegates variant construction to
`probe_metamorph_mesh.build_variant`, so the descriptor registry, range checks,
precision checks, one-token diff audit, and lossless round trip remain in one
place. It delegates each native run to the existing supervised exporter. A
case is complete only when a report records the expected source hash and a
successful STL. Failed attempts stay on disk and a rerun continues from the
first incomplete case.

The final summary compares every successful case with repeated baseline runs.
It records dimensions, triangle count, volume, connected components, and the
existing basic topology predicates. It ranks cases by normalized dimension
change and volume change. Rankings describe geometric impact, not quality or
printability.

The first case file uses values already present in XenoDream's installed
Sphere presets or observed from its own randomizer. It tests numeric parameters
one at a time. Choice parameters and bias or shape controls that need another
non-default parameter are deferred to an interaction sweep. This keeps the
isolated sweep interpretable.

## Synthesis decision

The base design is a separate resumable experiment coordinator. It keeps the
single-parameter probe strict and keeps native automation outside the package.
I rejected adding a batch mode to `probe_metamorph_mesh.py` because that would
mix deterministic XDX construction with Windows process control. I also
rejected adding these cases to `mutation.py`; doing so would turn questions
into supported product features before XenoDream and mesh evidence answer
them.

The coordinator is intentionally one deep script rather than separate plan,
run, retry, and summarize commands. Callers should not have to understand run
directory naming or report reconciliation. The manifest and reports remain
plain JSON for audit and recovery.

## Tradeoffs accepted

- We accept an explicit case file in exchange for traceable value selection.
- We accept sequential native exports in exchange for process isolation and
  avoiding concurrent access to XenoDream's user settings.
- We accept basic mesh measurements in exchange for using the proven exporter
  and inspector. Self-intersections and local thickness remain later gates.
- We defer discrete interactions so each result in this sweep has one changed
  token and one plausible cause.

## Alternatives considered

Extending the single-probe script with batch and retry options would put
Windows runtime policy beside byte-level mutation policy. The interface would
be smaller, but the module would own unrelated failure modes.

Generating random values from every descriptor range would cover more numbers
but provide weaker evidence. Native limits describe accepted input, not useful
sculpture ranges. Installed presets give us values XenoDream itself ships.

Adding the recovered fields directly to `ObjectMutation` would make them easy
to use, but it would erase the distinction between a measured experiment and a
supported modeling operation.

## Open questions and risks

- Will every isolated preset-derived value produce a mesh, or do some
  parameters require a companion choice or bias setting?
- Are the native preset values stable evidence for XDX 1.220 even when older
  saved projects used shorter parameter arrays?
- Which strong changes preserve one component and basic closed topology?
- How much repeated-export variation appears for highly deformed shapes?

## Next implementation step

Implement schema validation and resumable execution with a fake exporter test
before launching the full native sweep.
