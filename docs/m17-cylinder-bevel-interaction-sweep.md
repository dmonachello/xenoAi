# Cylinder bevel interaction sweep

## Result

The focused bevel sweep completed two baselines and three mutation cases on the
first attempt. Every export produced one connected mesh with zero detected
boundary edges, non-manifold edges, winding conflicts, or degenerate triangles.

The run confirms that the Bevel selector changes geometry when Bevel Edges is
nonzero. It also explains why the isolated `Bevel=Back` case was nearly inert.
That earlier case retained the default bevel amount of zero.

## Method

Each case began from the generated XDX 1.220 Cylinder. The control set Bevel
Edges to 25 and kept the default Both Ends selector. The Front and Back cases
repeated the same amount and changed only the selector. Each selector case was
compared with the Both Ends control.

Exports used a 120 mm maximum dimension and 10 percent Mesh Size. The two
baseline exports had 3,962 triangles and identical dimensions. Their
absolute-volume span was 1.1075 mm3.

## Measurements

| Case | Compared with | Impact | Triangle delta | Volume delta (mm3) |
| --- | --- | ---: | ---: | ---: |
| Bevel Edges 25, Both Ends | Baseline | 0.031340 | -38 | -18,259.036 |
| Bevel Edges 25, Back | Both Ends | 0.016179 | +18 | +9,130.510 |
| Bevel Edges 25, Front | Both Ends | 0.016177 | +18 | +9,129.449 |

All cases retained the baseline dimensions of 113.790 x 113.790 x 57.309 mm.
Front and Back had equal triangle counts. Their 1.0603 mm3 volume difference
was smaller than the repeated-baseline volume span. Their STL hashes differed,
which is consistent with opposite-end geometry that has equal aggregate
measurements.

## Interpretation

Bevel Edges 25 removes about 3.13 percent of the baseline absolute volume when
applied to both ends. Selecting one end restores about half of that removed
volume. Front and Back are equivalent in aggregate measures at this detail.

The evidence supports complete Cylinder bevel profiles that pair a nonzero
Bevel Edges value with an explicit selector. It does not support changing the
selector alone as a useful profile.

## Validation level

The sweep establishes native acceptance, interaction behavior, and the current
basic mesh predicates for these exact values. It does not test self-intersections,
local thickness, support requirements, tolerances, or fabrication suitability.
Every result keeps `printable` false.

The compact evidence record is
`evidence/runtime/m17-cylinder-bevel-interaction-sweep-summary.json`.
