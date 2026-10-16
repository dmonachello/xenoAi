# Active Metamorph randomization

Date: 2026-10-16

Target: XenoDream X 1.220, `XenoDreamX.exe`, SHA-256
`1674590ed60cea95cfeef076dfdafce4384fb86f118f087c42e23fd9429f1b6e`.

## Observed binary behavior

The embedded form metadata identifies the dice control as
`btnRandomActMMPars`, with `OnClick=btnRandomActMMParsClick`. Delphi method
metadata maps that handler to `0x77b4c4`. REA exact bytes for the handler are
preserved as Evidence
`ev_70b1e6e6efa70faed2fb6c6b8006b9d114bea3948f53f80889e5a05ca1de7362`.
The corresponding reset handler is `btnResetMMParsClick` at `0x77bbf4`.

The handler loops over the active metamorph's parameter descriptors. It treats
numeric controls and discrete list controls separately. When the active
metamorph has more than two parameters, it uses the extended-precision
constant at `0x77b92c`; decoding its bytes produces exactly `0.033`. The
per-parameter probability of selecting the stored default is therefore
`(parameter_count - 2) * 0.033`.

For numeric parameters that are not reset to default, the handler reads
descriptor limits and control metadata. Signed ranges use a center-weighted
sample containing the product of two differences between independent random
draws. The result is clamped to descriptor limits and rounded at a scale chosen
from the control metadata. Discrete controls either select their stored
default or a uniformly chosen list index. The handler then copies each
resulting control value into the active metamorph parameter array and marks the
project dirty.

The reset handler copies stored parameter defaults into the same numeric or
discrete controls and parameter array. This supports the default-path
interpretation independently of the random handler.

## Cross-validation

**CONFIRMS:** The user's Sphere dice result retained many apparent defaults
while changing only some controls. A 12-parameter Sphere receives a default
probability of `10 * 0.033 = 0.33` per parameter, which is consistent with that
outcome. One screenshot does not prove the distribution by itself.

**EXTENDS:** Manual experiments established the Sphere's 12-token `Pars`
record but did not establish how the dice selected values. The handler reveals
default retention, numeric-versus-discrete handling, center-weighted sampling,
descriptor clamping, and rounding behavior as a family rather than through
one-control experiments.

**UNRESOLVED:** The exact descriptor table population path, every parameter's
stored range, and the relationship between all resulting values and printable
geometry still require recovery and automated mesh evaluation. The handler
does not by itself prove that a random result is structurally strong or
fabrication-safe.

No contradiction with the existing generator was found. The generator's
current restraint remains correct: only verified stored fields may be changed.

## Generator implication

XenoDream's dice is a reference mutation operator, not the project's sole
mutation mechanism. `SeededVariation` adopts two recovered ideas—probabilistic
retention and center-weighted sampling—behind a repository-owned, seeded,
versioned algorithm. It changes only previously verified physical-form fields
and records the seed and strength in the revision graph. Native dice automation
can later be added as an isolated optional operator whose output is imported,
diffed, meshed, and scored.

The project-authored mutation envelopes are not represented as XenoDream
limits. Sphere metamorph fields remain unavailable until their descriptor
ranges, persistence mapping, and mesh effects are cross-validated.
