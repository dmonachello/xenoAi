# Metamorph registry checkpoint

Date: 2026-10-16

## Result

The project now has a machine-readable, evidence-scoped metamorph registry and
a read-only inspector for persisted metamorph stacks. This is the first step
away from whole-project templates toward XenoDream's procedural operation
model. It does not expand the writer yet.

Run:

```powershell
xxp inspect-metamorphs model.xxp
```

The report enumerates every `Holon\N\MM\M` section in source order. It includes
Style, `NumPars`, the raw `Pars` value, token count, count consistency, registry
status, and per-token mapping status. Unknown styles and tokens remain literal
and unresolved.

## Cross-validation

**CONFIRMS:** The accepted XDX 1.220 Cube and Sphere files contain Style 5 with
nine parameters and Style 1 with twelve parameters respectively. The registry
recognizes those exact versioned record families. Cube Style 5 token zero is
reported as Face Warp from controlled experiment E049. No other token receives
a semantic name.

**EXTENDS:** Defined executable strings expose operation help for whole
parameter families. Sphere help at `0x5ab225` names Warp, Warp Shape, Waist,
Ovoid, Sharpness, Bilobe, Shear, Shear Bias, XZ Curve, Taper X, Taper Type, and
Taper Shape. Cube strings at `0x5ac1d7` and `0x5ac406` confirm Face Warp and
describe the related face, edge, corner, inset, crop, squeeze, and choice
controls. These labels agree with the observed application panels.

**UNRESOLVED:** Ghidra reports no ordinary cross-references to these defined
help strings. The application likely reaches them through resource or metadata
tables, but static absence of a direct reference does not prove that path.
Displayed control order is not treated as `Pars` token order. Defaults, ranges,
types, persisted indexes, formulas, and printable effects remain unresolved
except for Cube Face Warp.

Historical corpus correlations identify candidate families including
RoundCube Style 6, Pipe 11, Cylinder 13, Torus 42, Cog 62, SpiralShell 65, and
Crystal 72. Their names are useful binary-analysis targets. They do not
authorize project generation because corpus versions and payload widths vary.

## Architecture boundary

`src/xenodream_xxp/metamorph.py` owns the read-only projection.
`src/xenodream_xxp/data/xdx-1.220-metamorph-registry.json` owns operation
claims, confidence, and evidence links. `Document` still owns exact bytes.
Inspection does not mutate records or feed guessed values into the compiler.

The existing Cube and Sphere generator remains the write-side regression
oracle. A future general writer must reproduce every accepted artifact before
it replaces a template path.

## Next recovery target

Trace the code that populates the parameter descriptors consumed by the native
dice and reset handlers. Begin with the known Sphere and Cube records, then
follow one closed volumetric candidate, preferably Cylinder or Torus. The next
write capability requires a verified Style, parameter width, token binding,
defaults, ranges, and an automated native mesh acceptance result.
