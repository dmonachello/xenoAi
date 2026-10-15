# M3 cube generator design

## Problem

M3 must write a native XenoDream X project without weakening the lossless
parser or assigning meanings to opaque fields. The controlled XDX 1.220 cube
baseline supplies one complete project and verified locations for cube scale,
rotation, position, Color Density, and Face Warp. XenoDream remains the
acceptance authority.

## Usage

The library compiles one cube project to bytes. Callers provide only verified
controls.

```python
from decimal import Decimal

from xenodream_xxp.generator import CubeSpec, Vector3, compile_cube

basic = compile_cube()
elongated = compile_cube(
    CubeSpec(scale=Vector3(Decimal("25"), Decimal("50"), Decimal("100")))
)
```

The CLI creates a new file and refuses to overwrite an existing path.

```powershell
xxp generate-cube output/generated_cube.xxp
xxp generate-cube output/elongated_cube.xxp --scale 25 50 100
```

## Shape

`generator.py` owns the public `Vector3`, `CubeSpec`, and `compile_cube`
interface. A private template module owns the verified XDX 1.220 template
hash, semantic field locations, fixed decimal formatting, immutable record
replacement, and post-build checks. `document.py` remains unchanged.

The compiler loads a packaged byte-exact copy of the controlled cube baseline
and verifies its SHA-256 hash. Each field replacement checks the expected
source value before changing it. Transform tokens use five decimal places,
Color Density uses three, and Face Warp uses four. The compiler rejects
non-finite values and values that require silent rounding. It does not invent
numeric ranges.

The default specification must reproduce the controlled baseline byte for
byte. A modified specification may change only the verified field locations.
The compiler reparses its output and requires a byte-exact second
serialization before returning it.

This is a deep interface. One call hides template provenance, XDX sections,
token indexes, number formatting, line endings, and opaque defaults. Callers
cannot provide holon IDs, type codes, group references, or raw field names.

## Synthesis decision

The guarded-template candidate is the base because it preserves opaque fields
without presenting them as understood generator policy. The simple candidate
contributed the one-call library interface, exact default-output oracle, and
thin no-overwrite CLI. The broader IR candidate clarified the future boundary
between semantic scenes and an XDX compiler, but its `Project`, `Group`, and
multi-object types are deferred until M3 establishes accepted multi-object
files.

Direct construction lost because it would transcribe every opaque default
into code before we know which records XenoDream requires. A generic document
patch API lost because it would expose section names and token indexes to
callers. A full scene IR lost for this checkpoint because its supported shape
would exceed the evidence.

## Tradeoffs accepted

- We accept one pinned XDX 1.220 template in exchange for preserving unknown
  fields exactly.
- We accept a cube-only compiler in exchange for promises that match the
  controlled experiments.
- We accept `Decimal` inputs in exchange for deterministic fixed-point text.
- We accept manual XenoDream opening and rendering in exchange for keeping
  static checks separate from application acceptance.

## Open questions and risks

- Will XenoDream open and render the generated file under a new filename?
- Will it preserve the file byte for byte when reopened and saved, or rewrite
  opaque state?
- What extra records or selection data does XenoDream require for three cube
  siblings?

## Three-cube extension

The controlled `3_cube_positions.xxp` sample establishes one additional
project shape: Group1 with exactly three cube siblings. The compiler therefore
adds `ThreeCubeProjectSpec` and `compile_three_cubes`, backed by a second
hash-pinned template. The type requires exactly three `CubeSpec` values; it
does not present an arbitrary-length scene API.

Three architecture candidates were compared. Guarded block cloning was
rejected for this checkpoint because it would promote the observed sibling
pattern into a construction rule before application acceptance. A broader
project/group IR was rejected because only one group shape and two
cardinalities are known. A separate pinned profile won because it preserves
all opaque state and gives the default output a byte-exact oracle.

The three-cube profile verifies the header, group, sibling IDs, group links,
type codes, names, metamorph styles, exact source values, allowed semantic
deltas, and parser round trip. Tuple order maps only to the observed Holon 1,
2, and 3 slots. XenoDream open, render, and resave remains a separate
acceptance checkpoint.

## Bounded cube project compiler

The clean `two_cubesV2.xxp` reference fills the missing cardinality between
the accepted one-cube and three-cube projects. The public `CubeProjectSpec`
therefore accepts fixed tuples containing exactly one, two, or three
`CubeSpec` values. `compile_cube_project` selects the matching hash-pinned
template. Counts zero and four or greater fail at the type boundary.

Three designs were compared. A new standalone two-cube compiler was rejected
because it would add a third copy of the same validation and patch logic. A
record-cloning compiler was rejected because template selection preserves
opaque application state without promoting repeated record shapes into a
general construction rule. The bounded profile compiler won because it
centralizes proven mechanics while keeping one byte-exact source for every
supported count.

`compile_cube` and `compile_three_cubes` remain compatibility adapters. They
use the bounded compiler and retain their existing byte output. The private
compiler owns hashes, section identities, expected source tokens, number
formatting, allowed differences, and exact round-trip validation.
