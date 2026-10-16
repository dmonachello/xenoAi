# M14 evidence-gated Sphere metamorph mutation

## Caller view

Python callers apply one measured profile to one named Sphere:

```python
result = apply_verified_mutation(
    source,
    SphereMetamorphMutation("Sphere2", "cushion-core"),
)
```

Workspace users record the same change as a native revision:

```powershell
xenosculpt project metamorph sculpture.xsp `
  --object Sphere2 --profile cushion-core `
  --message "try the measured cushion core"
```

The command reports `native_validation_required: true` and
`fabrication_suitable: false`. It creates an editable XDX revision; it does not
claim that the new revision has already been exported or is printable.

## Public types

```python
@dataclass(frozen=True, slots=True)
class SphereMetamorphMutation:
    object_name: str
    profile: str

def sphere_metamorph_profiles() -> tuple[str, ...]: ...
```

`SphereMetamorphMutation` joins `VerifiedOperation`. The name means that the
field mapping and exact profile have measured evidence, not that every model
containing it is fabrication-safe.

## Data model

Add `data/xdx-1.220-sphere-mutation-profiles.json`. Each profile owns:

- a stable command name;
- the complete twelve-token `Pars` vector in persisted spelling;
- evidence references;
- the native test result and current topology result;
- `native_validation_required: true` and `fabrication_suitable: false`.

Profiles include the strong isolated effects from M12 and the conditional
effects from M13. Weak isolated Sharpness and isolated Shear Bias are retained
in the evidence logs but are not mutation profiles.

The full vector is intentional. Applying a profile replaces the Sphere's
entire active metamorph vector, so an earlier unmeasured metamorph cannot leak
into a supposedly tested combination. Transform, hierarchy, color, other
metamorph slots, unknown records, whitespace, and line endings remain byte
identical.

## Mutation flow

1. Parse and exact-round-trip the current XDX 1.220 artifact.
2. Resolve the named object uniquely through the existing object inventory.
3. Require the object to match the verified Sphere Style 1, NumPars 12 record.
4. Load and validate the packaged profile registry.
5. Replace only `Holon\N\MM\0.Pars` tokens 0 through 11 while retaining the
   original whitespace and trailing space.
6. Audit the structural diff against those twelve allowed locators.
7. Exact-round-trip the result and return validation requirements with it.

The mutation engine does not import the experiment scripts. Product code owns
the small byte-token replacement primitive; experiment code remains a caller
of the same format facts rather than a runtime dependency.

## Workspace and CLI

Workspace revision details record:

```json
{
  "type": "sphere-metamorph-profile-v1",
  "object_name": "Sphere2",
  "profile": "cushion-core",
  "evidence": ["R031", "E096"],
  "native_validation_required": true,
  "fabrication_suitable": false
}
```

The CLI exposes `project metamorph` as a separate command instead of adding
many optional fields to `project mutate`. This keeps ordinary transform edits
separate from experimental form operations and gives profile discovery a
single bounded vocabulary.

## Rejected alternatives

Arbitrary `--parameter NAME VALUE` input would expose the entire recovered
descriptor domain even though only selected values and combinations have mesh
evidence. It remains deferred.

Adding twelve Sphere fields to `SphereSpec` would make template generation
appear generally validated. M14 changes existing native artifacts through the
mutation boundary only.

Applying only the non-default tokens of a profile would preserve previous
metamorph values and create unmeasured combinations. Full-vector replacement
prevents that ambiguity.

Automatically declaring the revision accepted after mutation would collapse
native structural validity, 3D evaluation, mesh validity, and fabrication
suitability. Those states remain separate.

## Tests

- Every packaged profile has exactly twelve tokens and cites M12 or M13.
- Applying a profile changes only the expected `Pars` tokens.
- Switching profiles resets tokens omitted by the new profile.
- Cube targets, missing objects, unknown profiles, malformed Sphere records,
  and unsupported versions fail without output.
- Reapplying a profile is byte-identical and creates no revision.
- Workspace details and CLI output retain the validation requirement.
- Existing transform, row, seeded-variation, parser, and generator tests remain
  unchanged and pass.

## Next boundary

After M14, connect the workspace operation to the supervised native exporter
and mesh inspector as an explicit validation command. Only then should an
individual revision advance from `native_validation_required` to measured 3D
and mesh states.
