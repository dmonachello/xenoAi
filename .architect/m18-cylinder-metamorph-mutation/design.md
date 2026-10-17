# M18 evidence-gated Cylinder metamorph mutation

## Caller view

Existing Sphere commands remain unchanged. Cylinder callers select the native
operation explicitly:

```powershell
xenosculpt project metamorph sculpture.xsp `
  --operation Cylinder `
  --object Cylinder2 `
  --profile bevel-25-back `
  --message "apply measured back bevel"
```

Python callers use a separate request type:

```python
result = apply_verified_mutation(
    source,
    CylinderMetamorphMutation("Cylinder2", "bevel-25-back"),
)
```

Omitting `--operation` keeps the existing Sphere default. The operation is an
authorization choice, not an inference from the object name.

## Public types

```python
@dataclass(frozen=True, slots=True)
class CylinderMetamorphMutation:
    object_name: str
    profile: str

def cylinder_metamorph_profiles() -> tuple[str, ...]: ...
def cylinder_metamorph_profile_evidence(name: str) -> tuple[str, ...]: ...
```

The existing Sphere type, helpers, CLI syntax, and revision operation remain
unchanged.

## Promoted profiles

Add `data/xdx-1.220-cylinder-mutation-profiles.json`. It pins XenoDream X
1.220, Cylinder Style 13, NumPars 7, complete-vector replacement, and the same
conservative status policy as the Sphere registry.

The first release contains eight exact measured states:

| Profile | Complete `Pars` vector | Evidence |
| --- | --- | --- |
| `length-three` | `3.00000 360.0000 2 0 0 0.000 2` | R035 |
| `closed-ends-none` | `1.00000 360.0000 0 0 0 0.000 2` | R035 |
| `closed-ends-back` | `1.00000 360.0000 1 0 0 0.000 2` | R035 |
| `wedge-yes` | `1.00000 360.0000 2 1 0 0.000 2` | R035 |
| `spherical-yes` | `1.00000 360.0000 2 0 1 0.000 2` | R035 |
| `bevel-25-both` | `1.00000 360.0000 2 0 0 25.000 2` | R036 |
| `bevel-25-front` | `1.00000 360.0000 2 0 0 25.000 0` | R036 |
| `bevel-25-back` | `1.00000 360.0000 2 0 0 25.000 1` | R036 |

Arc 180 is excluded because it did not complete. Bevel Edges 2 and the
selector-only Back case are excluded because M16 showed weak or inert effects;
M17 provides the useful coupled bevel states. Arbitrary descriptor-valid
values and unmeasured combinations remain unauthorized.

## Authorization boundary

Do not add Cylinder to the shared `_objects()` inventory. That inventory feeds
ordinary object mutation, row placement, and seeded variation, whose current
branches assume Cube or Sphere. Global Cylinder recognition would therefore
grant unrelated behavior accidentally.

Cylinder profile mutation uses a dedicated selector that scans top-level
`Type=1` objects, resolves the requested name uniquely, and requires Style 13,
NumPars 7, and seven `Pars` tokens. It grants no transform, row, variation, or
arbitrary metamorph capability. Existing operations continue through their
unchanged Cube/Sphere inventory and reject Cylinder projects.

## Mutation flow

1. Parse and exact-round-trip the current XDX 1.220 artifact.
2. For a Cylinder profile request, bypass the shared Cube/Sphere inventory.
3. Resolve exactly one named top-level Cylinder record through the dedicated
   Style 13 and NumPars 7 selector.
4. Load the exact complete vector from the packaged Cylinder registry.
5. Replace all seven `Holon\\N\\MM\\0.Pars` tokens while preserving the
   surrounding bytes.
6. Audit the structural diff against those seven token locators only.
7. Exact-round-trip the result.
8. Return `native_validation_required: true` and
   `fabrication_suitable: false`.

Switching profiles clears prior Cylinder state because each profile replaces
the complete vector. Reapplying one profile is byte-identical.

## Workspace and CLI

Cylinder revisions record:

```json
{
  "type": "cylinder-metamorph-profile-v1",
  "object_name": "Cylinder2",
  "profile": "bevel-25-back",
  "evidence": ["R036"],
  "native_validation_required": true,
  "fabrication_suitable": false
}
```

`project metamorph` gains `--operation {Sphere,Cylinder}`, defaulting to
`Sphere`. `--profile` lists the union of current packaged names; the selected
typed request validates that the profile belongs to its operation. The
explicit discriminator prevents future cross-operation name collisions from
changing dispatch. CLI status comes from the mutation result when present.

## Rejected alternatives

A flat global profile namespace would preserve the shortest command, but
future constructors could collide and dispatch would depend on registry name
ownership. An explicit operation is clearer.

A generic profile-family framework would reduce duplication but changes the
stable Sphere path and adds an abstraction before a third family exists. A
parallel registry and request type keep this milestone small.

Adding Cylinder to `_objects()` with downstream deny lists would require every
present and future mutation handler to remember to reject it. A dedicated
profile selector makes authorization local and fail-closed.

Descriptor-aware arbitrary encoding is not part of this feature. The packaged
vectors are a closed, code-reviewed allowlist pinned by literal tests.

## Tests

- Pin all eight profile names, vectors, and evidence identifiers.
- Apply every profile to generated Cylinder bytes and require exact parser
  round trips and `Pars`-only diffs.
- Switch profiles to prove complete-state replacement.
- Reapply a profile to prove byte identity.
- Reject unknown profiles, wrong object families, malformed Style/NumPars/token
  count, missing names, and duplicate names.
- Prove Cylinder remains rejected by ordinary object mutation, row placement,
  and seeded variation.
- Record exact workspace evidence and operation identity.
- Exercise both the existing default Sphere CLI and explicit Cylinder CLI.
- Compare at least one generated profile artifact with its retained sweep
  variant before claiming completion.

