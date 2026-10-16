# Sphere metamorph interaction sweep

## Result

The first interaction-aware Sphere sweep completed twelve unattended
XenoDream jobs: two fresh baselines and ten mutation cases. Every final export
produced one connected component with zero detected boundary edges,
non-manifold edges, winding conflicts, or degenerate triangles. Two jobs needed
one automated retry; the coordinator retained the failed attempts and resumed
without repeating completed work.

This sweep establishes that several Sphere parameters are conditional controls,
not useful isolated mutations. It also validates cumulative multi-token probes
and comparison against a named earlier case instead of always comparing with
the unmodified baseline.

## Method

Each case began from the accepted XDX 1.220 Sphere source. The coordinator
applied every listed mutation through the recovered descriptor metadata, audited
the exact persisted token changes, exported the result through supervised
XenoDream automation, and inspected the binary STL independently.

Choice cases were compared with a matching numeric control:

- Warp Shape cases were compared with `Warp=-7`.
- Shear Bias was compared with `Shear=8`.
- Taper Type and Taper Shape were compared with `Taper X=-28`.
- The four-parameter cushion case was also compared with `Taper X=-28`, so its
  score represents the combined addition of XZ Curve, Taper Type, and Taper
  Shape.

Exports used a 100 mm maximum dimension and 25 percent Mesh Size. The two
baseline exports had 21,662 triangles. Their absolute-volume span was 0.0923
mm3, their largest dimension span was 0.0171 mm, and their triangle-count span
was zero.

## Measurements

The table reports each case relative to its named control, not necessarily the
unmodified Sphere.

| Rank | Case | Compared with | Impact | Triangle delta | Volume delta (mm3) | Dimensions (mm) |
| ---: | --- | --- | ---: | ---: | ---: | --- |
| 1 | Warp -7 + Tear Anti | Warp -7 | 0.423633 | +3,264 | -99,813.863 | 95.446 x 55.294 x 95.446 |
| 2 | Cushion core | Taper X -28 | 0.336021 | +2,324 | +125,278.154 | 95.905 x 95.886 x 95.905 |
| 3 | Shear 8 | Baseline | 0.320698 | -1,160 | -148,038.795 | 84.229 x 95.862 x 84.232 |
| 4 | Warp -7 + Sharp Anti | Warp -7 | 0.315362 | +2,180 | -54,513.568 | 95.000 x 65.681 x 95.000 |
| 5 | Taper X -28 | Baseline | 0.192336 | -1,700 | -88,785.140 | 95.902 x 95.796 x 95.796 |
| 6 | Taper X -28 + Type Y | Taper X -28 | 0.109525 | +850 | +40,834.237 | 95.897 x 95.796 x 95.884 |
| 7 | Taper X -28 + Type Z | Taper X -28 | 0.109525 | +850 | +40,834.212 | 95.888 x 95.888 x 95.790 |
| 8 | Taper X -28 + Curve up | Taper X -28 | 0.109025 | +702 | +40,647.659 | 95.902 x 95.905 x 95.905 |
| 9 | Warp -7 | Baseline | 0.077822 | +102 | -35,923.642 | 93.281 x 95.935 x 93.285 |
| 10 | Shear 8 + Bias 100 | Shear 8 | 0.073228 | +238 | +22,962.550 | 84.357 x 95.257 x 84.351 |

The impact score is the larger of maximum relative dimension change and
relative absolute-volume change. It measures geometric change only. It is not
an aesthetic score or a printability score.

## Interpretation

All tested interactions exceeded the repeated-baseline spans in triangle count,
volume, and dimensions.

- Warp Shape is an active geometric selector when Warp is nonzero. `Tear Anti`
  and `Sharp Anti` create substantially different meshes from the same Warp
  control.
- Shear Bias is interaction-dependent. Its isolated test was near export noise,
  but with nonzero Shear it produced a clear additional effect.
- Taper Type selects the orientation of the Taper X effect. Type Y and Type Z
  had almost identical volume and triangle changes but moved the small extent
  change to different axes.
- Taper Shape changes the Taper X result. `Curve up` produced a clear mesh
  difference from the linear control.
- The preset-derived cushion combination produced the largest positive volume
  change in this sweep while retaining the current basic topology predicates.

These findings confirm the recovered descriptor roles and extend the manual
work with measured conditional behavior. They do not prove that arbitrary
values or arbitrary combinations are safe.

## Validation level

The sweep establishes that every tested project was structurally accepted,
evaluated into 3D geometry, and exported as a one-component mesh that passed the
current basic edge and degeneracy checks. It does not test self-intersections,
local feature thickness, overhangs, tolerances, or fabrication suitability.
Every result therefore keeps `printable` false.

## Generator implication

The evidence is now sufficient for a first experimental Sphere metamorph
mutation policy using these exact tested controls and combinations. Such
mutations should remain opt-in and should require native evaluation plus mesh
scoring. The normal template compiler must not infer safety for unrestricted
descriptor-domain combinations.

