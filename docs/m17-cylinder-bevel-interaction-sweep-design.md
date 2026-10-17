# Cylinder bevel interaction sweep design

## Problem

The isolated Cylinder sweep changed the Bevel selector while Bevel Edges was
zero. That selector cannot produce a useful measurement until a nonzero bevel
amount activates it. The next experiment must combine a generated Cylinder
source with complete multi-mutation cases and named mesh controls. Existing
v1, v2, and v3 plans must retain their current meanings.

## Usage

Plan schema v4 combines the generated source syntax from v3 with the
interaction case syntax from v2:

```json
{
  "schema": "xenosculpt-metamorph-sweep-plan/v4",
  "operation": "Cylinder",
  "source": {"kind": "generated", "constructor": "Cylinder"},
  "holon": 1,
  "baseline_replicates": 2,
  "cases": [
    {
      "id": "bevel-25-both",
      "compare_to": "baseline",
      "source": "REA descriptor R034 nonzero bevel control",
      "mutations": [
        {"parameter": "Bevel Edges", "value": "25"},
        {"parameter": "Bevel", "value": "Both Ends"}
      ]
    }
  ]
}
```

The existing command runs the focused plan at discovery detail:

```powershell
python scripts\sweep_metamorph_mesh.py `
  experiments\metamorph-sweeps\cylinder-bevel-interactions-v1.json `
  output\cylinder-bevel-interactions-preview-v1 `
  --attempts 1 `
  --timeout-seconds 120 `
  --stl-max-dimension-mm 120 `
  --mesh-size-percent 10
```

## Shape

Four schema capability sets define source and case grammar. V1 and v3 use one
mutation per case. V2 and v4 use complete mutation lists with named controls.
V1 and v2 read a source file. V3 and v4 compile the recovered Cylinder source.
This keeps schema policy in one place without changing the validated dictionary
used by preparation.

Every case starts from the generated baseline. The Front and Back cases repeat
`Bevel Edges=25` because `compare_to` selects only the mesh used for delta
calculation. It does not inherit mutations or bytes. The Both Ends control
states the default choice explicitly, so its manifest records one changed
numeric mutation and one unchanged choice mutation.

The manifest, exporter, and summary formats already store generated source
identity, cumulative mutations, and named controls. They do not change.

## Synthesis decision

Three independent sketches agreed on a v4 plan. The selected design uses
capability sets because it preserves the current preparation path and adds no
new public API. The compatibility sketch contributed strict source and case
boundary tests.

I rejected a full dataclass normalization because it would rewrite stable code
without changing the experiment interface. I also rejected a constructor
registry because Cylinder is the only recovered generated constructor in scope.
Changing v2 or v3 in place would weaken their reproducibility contracts.

## Tradeoffs accepted

- We accept another schema version in exchange for freezing existing schema
  meanings.
- We accept repeated complete mutations in exchange for cases with no hidden
  inherited state.
- We accept an exploratory Bevel Edges value of 25 in exchange for a signal
  large enough to survive the 10 percent discovery mesh.

## Alternatives considered

Widening v3 to accept two case shapes would produce a smaller diff but an
ambiguous wire contract. A separate Cylinder interaction runner would duplicate
preparation, retry, and summary rules. Building dependent cases from their
controls would shorten the JSON but hide the final token state.

## Open questions and risks

- Does 10 percent detail distinguish Front, Back, and Both Ends?
- Does Bevel Edges 25 preserve basic topology for every selector choice?
- Which cases merit a 25 or 40 percent confirmation export?

## Next implementation step

Validate v4 parsing, generated cumulative diffs, and named-control summaries
before starting native exports.
