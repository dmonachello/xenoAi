# Sphere metamorph interaction sweep design

## Problem

The isolated sweep measures numeric parameters against the untouched Sphere,
but three choice parameters describe how another active parameter behaves.
Shear Bias is also nearly inert without Shear. Testing these controls requires
several exact token changes in one case and comparison with a named control,
not with the untouched baseline. The existing v1 plans and their results must
remain reproducible.

## Usage

A v2 case lists its complete mutations and the case that isolates the added
interaction:

```json
{
  "id": "shear-biased",
  "compare_to": "shear-control",
  "source": "XDXSystem.xmm Sphere/Heart 2",
  "mutations": [
    {"parameter": "Shear", "value": "8"},
    {"parameter": "Shear Bias", "value": "100"}
  ]
}
```

The same command runs v1 and v2 plans:

```powershell
python scripts/sweep_metamorph_mesh.py `
  experiments/metamorph-sweeps/sphere-interactions-v1.json `
  output/sphere-interactions-v1
```

## Shape

The plan loader accepts both schemas:

```python
PLAN_SCHEMAS = {
    "xenosculpt-metamorph-sweep-plan/v1",
    "xenosculpt-metamorph-sweep-plan/v2",
}
```

The loader converts each v1 parameter and value pair into one internal
mutation. V2 cases provide a non-empty mutation list and a `compare_to` value.
`compare_to` must name `baseline` or an earlier case. This ordering rule makes
the comparison graph acyclic without exposing graph management to callers.

Case construction begins with the accepted source for every case. It calls the
existing one-token builder once per requested mutation. The builder continues
to enforce the descriptor schema, range, precision, exact token diff, and byte
round trip at each step. The coordinator rejects repeated parameters within a
case. It then records the cumulative diff from the original source, so the
manifest proves that no other field changed.

Summary comparison uses the named control mesh for dimensions, triangle count,
and volume. Global repeated baselines still measure exporter variation. Every
result records `compare_to` and the control hash, which prevents a shape choice
from being mistaken for the effect of the numeric parameter it modifies.

The script remains an experiment tool. `mutation.py`, the generator, workspace
revisions, and the packaged executable do not gain new permissions in this
step.

## Synthesis decision

The chosen design extends the existing manifest rather than adding a second
interaction runner. One coordinator already owns preparation, retry, report
matching, and mesh summaries. Adding a second runner would duplicate those
rules and invite different failure handling.

I rejected a free-form dependency graph. Requiring controls to appear earlier
is enough for these experiments and catches cycles during ordinary validation.
I also rejected mutating a control case's bytes to construct a dependent case.
Every case starts from the accepted source, so its complete token set remains
explicit and independent of case ordering.

## Tradeoffs accepted

- We accept ordered case declarations in exchange for cycle-free comparisons
  without a graph subsystem.
- We accept cumulative cases with several changed tokens in exchange for
  measuring real parameter interactions.
- We retain two untouched baselines even though named controls provide the
  causal comparison. The baselines quantify exporter variation across the
  whole run.
- We continue sequential exports because XenoDream stores mesh settings in
  shared user configuration.

## Alternatives considered

A separate script for each interaction family would keep individual plans
simple but duplicate resume and evidence rules. Callers would also need to
merge several summary formats.

Constructing interaction cases by editing a prior control artifact would save
a little work. It would make a case depend on hidden inherited mutations and
weaken the final diff audit.

Promoting the controls directly into the product mutation model would skip the
experiment layer. That would make unmeasured combinations look supported.

## Open questions and risks

- Which Warp Shape choices remain connected at the selected Warp value?
- Does Shear Bias materially change a nonzero Shear mesh?
- Do Taper Type and Taper Shape alter the same axes implied by their labels?
- Does the shipped Cushion combination remain closed when isolated from its
  other preset values?

## Next implementation step

Add v2 normalization and cumulative-diff tests before starting native exports.
