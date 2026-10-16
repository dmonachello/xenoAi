# Seeded sculpture variation

## Problem

The project can apply exact user-specified edits, but it cannot yet derive a
creative mutation from the current revision. XenoDream's Active Metamorph dice
provides useful evidence about mutation policy: it probabilistically retains
defaults, distinguishes continuous from discrete parameters, and favors values
near the center rather than sampling every value uniformly. We need to learn
from that behavior without making an opaque GUI action the source of truth or
expanding beyond fields whose file mappings are already verified.

## Usage (caller's view)

```powershell
xenosculpt project evolve sculpture.xsp --seed 20261016 --strength 0.35 `
  --message "first seeded variation"
```

Repeating that operation from the same revision with the same seed and
strength produces the same native `.xxp` bytes. A caller can branch first to
retain several candidates:

```powershell
xenosculpt project branch sculpture.xsp variation-a --checkout
xenosculpt project evolve sculpture.xsp --seed 17 --strength 0.5 `
  --message "variation A"
```

Python callers use the same revision path:

```python
workspace.apply(
    SeededVariation(seed=17, strength=Decimal("0.5")),
    message="variation A",
)
```

## Shape

Add one immutable public operation, `SeededVariation(seed, strength)`, to
`mutation.py`. `apply_verified_mutation` recognizes it alongside exact object
and row operations. The operation inspects the current verified Cube/Sphere
records and derives replacement values, then passes those values through the
same precision formatting, allowed-difference audit, and exact round-trip gate
as existing mutations.

The algorithm is explicitly versioned in revision details. Version 1 uses a
local deterministic PRNG seeded by the supplied integer. For each eligible
scalar field it first makes a retain/change decision. The retain probability is
the recovered XenoDream rule `min(0.9, 0.033 * max(0, n - 2))`, where `n` is
the number of fields our operation can safely edit for that object. Changed
values use the recovered center-weighted shape `(u1-u2)*(u3-u4)`, but our own
documented envelopes:

- scale: multiplicative change bounded by `strength`, with a positive floor;
- rotation: additive change within 45 degrees times `strength`;
- position: additive change within the object's largest scale times
  `strength`;
- Cube Face Warp: constrained to the experimentally exercised 0.0–0.25
  envelope.

Sphere rotation and metamorph parameters remain untouched because their native
file semantics or allowed ranges are not yet verified. Color density remains
untouched because it is a rendering control, not a physical-form priority.
This is our algorithm informed by XenoDream, not a claim that it reproduces
Delphi's PRNG or all native dice results.

`workspace.py` records `seed`, `strength`, and the algorithm identifier in the
revision. `cli.py` contributes only argument parsing and output; it does not
implement mutation policy. No database migration is required because revision
details are already schemaless JSON.

This is a deep interface: two caller inputs hide field discovery, deterministic
sampling, physical-form policy, precision handling, byte replacement, diff
auditing, and revision recording. The parser remains syntax-only, and the
template compiler remains a regression oracle.

## Synthesis decision

Two shapes were considered locally because team delegation is disabled for
this turn. Candidate A returned an explicit mutation plan for callers to apply
field by field. Candidate B made seeded variation a single typed operation.
Candidate B is the base because callers should not coordinate random draws and
multiple byte edits. Candidate A's useful idea—record the concrete outputs—was
retained through the existing diff and revision details.

## Tradeoffs accepted

- We accept a deliberately small mutation vocabulary in exchange for preserving
  the established evidence boundary.
- We accept a project-authored mutation envelope in exchange for deterministic,
  testable behavior; it is not presented as a native XenoDream range.
- We accept that a very small mutation can be a no-op after quantization in
  exchange for keeping the algorithm honest and idempotent.
- We accept Python PRNG compatibility as part of algorithm version 1 and record
  the version so a future implementation can coexist rather than silently
  changing old results.

## Alternatives considered

- Return a `MutationPlan` containing many `ObjectMutation` values. This exposes
  sequencing and atomicity to every caller and makes a single revision harder
  to guarantee.
- Automate the native dice as the only mutation mechanism. This is
  non-reproducible without recovering native seed state, depends on fragile UI
  selection, and can change currently unverified fields. Native dice remains a
  valuable isolated experimental operator and future optional strategy.
- Expose all 12 Sphere parameters immediately from the decompiled loop. The
  handler establishes the randomization mechanism, but not yet every stored
  parameter's range and geometric consequence, so this would outrun the
  cross-validation record.

## Open questions and risks

- Should a future version select one object rather than varying all verified
  objects?
- Which recovered native ranges should replace the provisional Face Warp
  envelope after automated mesh validation exists?
- Does Python's seeded PRNG need replacement with a repository-owned integer
  generator before cross-language clients are supported?
- When should native-dice output become an optional mutation operator whose
  results are imported and compared with our deterministic operator?

## Next implementation step

Add failing deterministic mutation tests, implement the typed operation and
workspace/CLI integration, then package and smoke-test the executable.

## Red-flag screening

- Shallow module: no; the two-field operation hides all mutation policy.
- Information leakage: no; field mappings remain owned by `mutation.py`.
- Temporal decomposition: no; discovery, sampling, editing, and audit happen
  behind one operation boundary.
- Pass-through method: no; workspace adds atomic revision and provenance policy.
