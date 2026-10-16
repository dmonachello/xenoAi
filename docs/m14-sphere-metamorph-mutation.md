# Evidence-gated Sphere metamorph mutation

## Capability

The workspace mutation boundary can now apply fifteen measured Sphere
metamorph profiles to an existing native XDX 1.220 revision. The profiles cover
the strong isolated effects from M12 and the tested conditional controls from
M13:

- positive and negative Warp;
- Warp with Sharp Anti or Tear Anti shape;
- Waist, Ovoid, Bilobe, Shear, and XZ Curve;
- Shear with Bias;
- Taper X with Y or Z type and Curve up shape; and
- the four-parameter cushion core.

The profile registry is packaged as
`src/xenodream_xxp/data/xdx-1.220-sphere-mutation-profiles.json`. It is separate
from the descriptor registry. Descriptor metadata says what XenoDream can
store; the profile registry says which exact states have measured native mesh
evidence and may be written by this operation.

## Safety boundary

Each profile stores a complete twelve-token `Pars` vector. Applying it resets
the active Sphere metamorph to that measured state while preserving the
project's transform, hierarchy, color, other metamorph records, unknown data,
whitespace, and line endings. This prevents an old parameter from creating an
untested combination.

The mutation engine requires:

- an exact-round-tripping XDX 1.220 file;
- one uniquely named verified Sphere object;
- Style 1, NumPars 12, and twelve persisted tokens;
- a packaged profile with traceable M12 or M13 evidence; and
- a structural diff containing only the active Sphere `Pars` tokens.

Cube targets, unknown profiles, malformed Sphere records, and unsupported XDX
versions are rejected.

## Revision record

Workspace revisions store the profile name, object name, evidence identifiers,
and two explicit status fields:

- `native_validation_required: true`
- `fabrication_suitable: false`

The M12 and M13 experiments validate the profile on the accepted standalone
Sphere at their tested export settings. Applying the same profile to a changed
model produces a structurally controlled native revision, not an automatic
claim about its evaluated mesh or printability.

## Usage

```powershell
xenosculpt project metamorph sculpture.xsp --object Sphere2 `
  --profile warp-tear-anti --message "tear-shaped warp"

xenosculpt project metamorph sculpture.xsp --object Sphere2 `
  --profile cushion-core --message "switch to cushion core"
```

Switching profiles replaces the whole parameter vector. Reapplying the current
profile is byte-identical and creates no new revision.

The rebuilt standalone executable has SHA-256
`9c690504e950179c9bf20d993c73b757315ee8c247060c8459e034af2d505d70`.
Its `warp-tear-anti` smoke output has SHA-256
`f77d431353332c673d6afb717634f20123df382b4c6d9b4b392f90afd4263072`,
which is byte-identical to the same profile from the completed M13 native
evaluation. The packaged-path record is
`evidence/runtime/m14-packaged-mutation-smoke.json`.

## Next step

Add a workspace validation operation that exports the active revision through
the supervised XenoDream runner, inspects the mesh, and attaches the report to
the revision. That will move a specific mutation from “requires native
validation” to measured geometry without weakening the distinction between
native validity, mesh validity, and fabrication suitability.
