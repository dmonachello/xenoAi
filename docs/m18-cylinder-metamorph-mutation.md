# Evidence-gated Cylinder metamorph mutation

## Result

The workspace can now apply eight measured Cylinder profiles without exposing
the recovered descriptor ranges as arbitrary write controls. Each profile
replaces the complete seven-token Cylinder metamorph vector and records its
runtime evidence in the new revision.

The available profiles are:

- `length-three`
- `closed-ends-none`
- `closed-ends-back`
- `wedge-yes`
- `spherical-yes`
- `bevel-25-both`
- `bevel-25-front`
- `bevel-25-back`

The first five cite the isolated M16 campaign. The three bevel profiles cite
the M17 interaction campaign and always pair Bevel Edges 25 with an explicit
end selector.

## Command

Apply a profile to a Cylinder workspace:

```powershell
xenosculpt project metamorph sculpture.xsp `
  --operation Cylinder `
  --object Cylinder2 `
  --profile bevel-25-front `
  --message "apply measured front bevel"
```

Sphere remains the default operation, so existing Sphere commands do not need
the new option.

## Safety boundary

The mutation path requires XDX 1.220, one uniquely named Type 1 target, Style
13, NumPars 7, and exactly seven persisted `Pars` tokens. It changes only that
record's token values, audits the structural diff, and exact-round-trips the
result.

Cylinder recognition is private to this profile operation. It does not enable
ordinary Cylinder object mutation, row placement, seeded variation, arbitrary
metamorph values, or unresolved Arc values.

Every resulting revision retains:

```text
native_validation_required: true
fabrication_suitable: false
```

The source profiles passed native evaluation and the current basic topology
checks at 10 percent discovery detail. Applying the same bytes in a changed
scene still requires revision-level native validation. No profile establishes
self-intersection freedom, minimum thickness, support requirements,
tolerances, or fabrication suitability.

## Reproduction check

Applying `bevel-25-front` to a newly generated Cylinder produced SHA-256
`7f7c48375ecaf621e22250887538c8a67af9040611b7cca853ae465b3db618e8`.
That result is byte-identical to the retained M17 variant evaluated by
XenoDream. The checked-in comparison record is
`evidence/runtime/m18-cylinder-profile-equivalence.json`.

The same profile was then applied through a revision workspace and evaluated
by XenoDream at 10 percent Mesh Size. The export completed in 19.5 seconds with
3,942 triangles, one connected component, and zero errors in the current basic
topology checks. The source artifact and disposable input remained unchanged.
See `evidence/runtime/m18-cylinder-live-validation.json`.

The rebuilt `xenosculpt.exe` also generated the source, created the workspace,
applied the profile, and exported the revision. The packaged output had the
same SHA-256 as the retained M17 variant. See
`evidence/runtime/m18-packaged-cylinder-smoke.json`.
