# Sphere isolated metamorph sweep

## Result

The first systematic Sphere sweep completed eleven unattended XenoDream jobs:
two fresh baselines and nine one-token mutations. Every final export produced
one connected component with zero detected boundary edges, non-manifold edges,
winding conflicts, or degenerate triangles. Two jobs needed a second attempt.
The coordinator retained the failed reports and resumed without repeating the
other jobs.

This is the first broad map from XDX Sphere parameters to measured native mesh
effects. It replaces nine manual edit, load, and export cycles.

## Value selection

The sweep did not sample arbitrary fractions of the descriptor ranges. Eight
values came from the installed `XDXSystem.xmm` Sphere presets. Ovoid 2.8 came
from the native randomizer result observed in XenoDream. Each generated file
changed exactly one persisted `Pars` token from the accepted Sphere baseline.

Choice parameters were not tested alone. Warp Shape, Taper Type, and Taper
Shape describe how another non-default value behaves, so they belong in a
later interaction sweep. Shear Bias was retained in this isolated pass to test
whether it has an independent effect.

## Measurements

Exports used a 100 mm maximum dimension and 25 percent Mesh Size. The two
baseline exports had the same 21,662 triangles. Their absolute volume differed
by 0.146 and their largest dimension span was 0.0204 mm.

| Rank | Parameter and value | Impact score | Triangle delta | Volume delta | Dimensions (mm) |
| ---: | --- | ---: | ---: | ---: | --- |
| 1 | Ovoid 2.8 | 0.828455 | -830 | -382,426.566 | 39.884 x 95.011 x 39.876 |
| 2 | Shear 8 | 0.320698 | -1,160 | -148,038.679 | 84.232 x 95.862 x 84.232 |
| 3 | Warp 10 | 0.314135 | -714 | -145,009.165 | 84.452 x 94.922 x 84.459 |
| 4 | Waist 12 | 0.199847 | -1,526 | -92,252.204 | 96.128 x 85.941 x 96.118 |
| 5 | Taper X -28 | 0.192337 | -1,700 | -88,785.556 | 95.902 x 95.797 x 95.788 |
| 6 | XZ Curve -20 | 0.153799 | +1,122 | +70,995.900 | 95.905 x 95.900 x 95.905 |
| 7 | Bilobe 5 | 0.049783 | +850 | -20,697.520 | 91.130 x 91.141 x 94.730 |
| 8 | Sharpness 2 | 0.000106 | 0 | -2.043 | 95.905 x 95.905 x 95.895 |
| 9 | Shear Bias 100 | 0.000071 | 0 | -0.201 | 95.905 x 95.895 x 95.898 |

The impact score is the larger of maximum relative dimension change and
relative absolute-volume change. It ranks geometric change only. It is not an
aesthetic score or a printability score.

Ovoid, Shear, Warp, Waist, Taper X, XZ Curve, and Bilobe changed triangle count,
volume, and dimensions beyond the observed baseline spans. Sharpness 2 and
Shear Bias 100 produced only small changes. The Shear Bias result supports the
expected interaction hypothesis: bias probably needs nonzero Shear before it
has a substantial effect. Sharpness needs a stronger or interaction-aware
probe before we classify its usefulness.

## Validation level

The sweep establishes four facts for each tested value:

- XenoDream accepted the one-token project.
- XenoDream evaluated it into 3D geometry.
- The exported STL passed the current basic topology checks.
- The measured effect can be compared with repeated baseline variation.

It does not establish self-intersection freedom, local wall thickness,
overhang safety, tolerances, or fabrication suitability. Every result keeps
`printable` false.

## Next investigation

The next sweep should test the interactions that the native presets imply:

- Warp with selected Warp Shape choices.
- Shear with and without Shear Bias.
- Taper X with each Taper Type and a small set of Taper Shape choices.
- Sharpness at stronger preset-derived values and with Warp or Ovoid.

Those results can define the first evidence-gated Sphere metamorph mutation
policy. Native evaluation and mesh scoring should remain mandatory for
generated combinations until interaction failures are understood.
