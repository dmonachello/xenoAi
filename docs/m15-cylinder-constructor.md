# M15 Cylinder constructor recovery

## Reconciliation

The historical corpus contains nine Style 13 Cylinder records in versions
0.992 through 1.007. Every record declares seven parameters. The XenoDream X
1.220 operation table entry at `0x5af204` independently defines seven indexed
descriptors:

The exact extracted descriptor payload is retained in
`evidence/recovered/cylinder-descriptor-recovery.json`.

| Index | Parameter | Domain | Default |
|---:|---|---|---:|
| 0 | Length | 0–200 numeric | 1 |
| 1 | Arc | 0.01–360 numeric | 360 |
| 2 | Closed Ends | None, Back, Both | Both |
| 3 | Wedge | No, Yes | No |
| 4 | Spherical | No, Yes | No |
| 5 | Bevel Edges | -100–100 numeric | 0 |
| 6 | Bevel | Front, Back, Both Ends | Both Ends |

This **CONFIRMS** the historical Style, parameter count, ordering, names, and
default-shaped vectors; it **EXTENDS** them with current descriptor ranges,
steps, precision, and choice labels. Installed `XDXSystem.xmm` presets named
Wedge, Open half cylinder, Closed half cylinder, and Pot align with those
fields. The extra preset values remain unresolved and are not copied into the
native `Pars` record.

## Construction and acceptance

The generator derives the one-Cylinder project from the normalized one-object
1.220 scaffold. It replaces only the object name and the constructor's Style,
NumPars, and Pars records, then applies the already verified scale and position
tokens. No manually created 1.220 Cylinder project is used.

Generated native SHA-256:
`99d74c4fe1220d4cbf9fdfe09425eb0fcb76a9ababad081dce4241e59f02f651`.
XenoDream accepted the file and exported 63,450 triangles. Independent
inspection found one connected component, zero boundary, non-manifold,
inconsistent-winding, or degenerate edges or triangles, and nonzero signed
volume. Mesh SHA-256:
`9982b49ad80a45f44a01eae41ac521bebfa87f2b6fb28c0064306fd306fd7360`.

This establishes a structurally valid native model, successful 3D evaluation,
and the current basic mesh predicate for the default. It does not establish
self-intersection freedom, minimum feature thickness, or fabrication
suitability. Parameter mutation remains closed until automated sweeps measure
useful and safe envelopes.
