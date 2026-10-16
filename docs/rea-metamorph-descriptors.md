# XenoDream metamorph descriptor recovery

## Result

The XenoDream X 1.220 executable contains a table of 246 operation classes at
virtual address `0x7f4390`. The active-metamorph panel does not infer its
controls from display order. Its loader at `0x788e0c` reads explicit descriptor
indexes from the selected operation class and maps them to the persisted
parameter slots.

For the supported constructors, this establishes all persisted token names:

- Sphere Style 1 has 12 indexed descriptors: Warp, Warp Shape, Waist, Ovoid,
  Sharpness, Bilobe, Shear, Shear Bias, XZ Curve, Taper X, Taper Type, and
  Taper Shape.
- Cube Style 5 has nine indexed descriptors: Face Warp, Face Shape, Face Curve,
  Inset, Edge Warp, Crop Face, Corner Crush, Face Squeeze, and Face Choice.

Each numeric descriptor also supplies its native minimum, maximum, default,
step, and decimal-place setting. Each discrete descriptor supplies its default
index and choice strings. The versioned read-only registry packages these
values for `inspect-metamorphs`.

This does not establish each parameter's geometric formula, interaction with
other metamorphs, printability, or safe mutation envelope. The recovered
metadata therefore does not grant generator write access by itself.

## Cross-validation

Relationship: **CONFIRMS + EXTENDS**.

- It confirms the manual Cube experiment: Cube Style 5 descriptor index 0 is
  Face Warp, matching `E049` exactly.
- It confirms the accepted Sphere and Cube record sizes: the descriptor counts
  are 12 and 9, matching their XDX 1.220 `NumPars` values.
- It confirms the previously recovered Active Metamorph labels, while adding
  the explicit stored index, data kind, bounds, defaults, precision, and choice
  domains that the label strings alone could not establish.
- No contradiction with an accepted generated or resaved file was found.

## Native flow

- `0x5e0114` enumerates all 246 operation classes and extracts their descriptor
  metadata.
- `0x788e0c` populates the twelve reusable Active Metamorph controls for the
  selected operation.
- `0x67a88c` extracts numeric descriptors.
- `0x67a728` extracts discrete-choice descriptors.
- `0x5130bc` copies the descriptor decimal-place field into the numeric control;
  the dice handler later reads the same control field when rounding values.
- Sphere Style 1 metadata begins at `0x5aaca8`.
- Cube Style 5 metadata begins at `0x5abfd8`.

The deterministic extractor is
`scripts/recover_metamorph_descriptors.py`. It accepts only the installed
executable hash
`1674590ed60cea95cfeef076dfdafce4384fb86f118f087c42e23fd9429f1b6e`
and fails closed if descriptor counts, indexes, metadata bounds, or the hash do
not match. The full REA session evidence is preserved at
`evidence/rea/metamorph-descriptor-session.json`.

## Generator implications

The immediate improvement is semantic inspection: current Sphere and Cube
files can now be reported with correct token names and native descriptor
domains. Mutation remains restricted to fields already supported by controlled
experiments. The next investigation should trace selected descriptor values
into the Sphere and Cube evaluator functions, then use automated native STL
exports to measure topology, connectedness, thickness, and surface changes for
small isolated parameter sweeps.
