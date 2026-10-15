# M4 object vocabulary design

## Problem

The cube compiler chooses a project template from cube count alone. The new
controlled sample proves one mixed XDX 1.220 shape: Group1 contains Cube2 at
X -50 followed by Sphere3 at X 50. A reusable modeling vocabulary needs to
name both object kinds without implying that arbitrary orders, counts, or
sphere metamorph parameters are understood.

## Usage

Callers describe objects and compile one of the exact supported sequences.

```python
from decimal import Decimal

from xenodream_xxp.generator import (
    CubeSpec,
    ProjectSpec,
    SphereSpec,
    Vector3,
    compile_project,
)

project = ProjectSpec(
    objects=(
        CubeSpec(position=Vector3(Decimal("-50"), Decimal("0"), Decimal("0"))),
        SphereSpec(position=Vector3(Decimal("50"), Decimal("0"), Decimal("0"))),
    )
)
payload = compile_project(project)
```

The compiler accepts only these object sequences:

- one, two, or three cubes;
- one sphere;
- one cube followed by one sphere.

Existing `compile_cube`, `compile_cube_project`, and `compile_three_cubes`
calls keep their current behavior and byte output.

## Shape

`generator.py` adds `SphereSpec`, `ProjectSpec`, and `compile_project`.
`SphereSpec` exposes only scale and position because those are the sphere
controls established by controlled experiments. It does not expose rotation,
color density, or Style 1 parameters.

The private template compiler selects a profile by the exact tuple of object
types. Every supported sequence has a hash-pinned, application-created
template. The profile owns object names, IDs, section slots, metamorph styles,
parameter counts, opaque parameter payloads, and source transform values.
Callers cannot provide any of those wire-format details.

Each compile checks the template hash and structure before editing it. Cube
objects retain their verified scale, rotation, position, Color Density, and
Face Warp controls. Sphere objects allow only scale and position changes.
The compiler rejects any diff outside those field locations and requires an
exact parser round trip before returning bytes.

This keeps the public call small while the private compiler owns template
selection, XDX identities, numeric formatting, line endings, opaque defaults,
and output auditing.

## Synthesis decision

The bounded domain candidate is the base because M4 needs object kinds that
can later feed a constrained recipe layer. The narrow-profile candidate
contributed the strict hash-pinned mixed template, complete checks of the
opaque sphere metamorph block, and a separate XenoDream acceptance gate.

A dedicated `CubeSphereProjectSpec` was rejected because each new observed
combination would add another public type and compile function. An unrestricted
object list was also rejected because the evidence covers only five exact
sequences. `ProjectSpec` has one entry point but rejects all unprofiled shapes.

## Tradeoffs accepted

- We accept five explicit project profiles in exchange for promises that match
  the current evidence.
- We accept a sparse sphere type in exchange for making undocumented sphere
  controls impossible to request.
- We accept two additional packaged templates in exchange for preserving
  unknown XDX fields exactly.
- We accept manual XenoDream acceptance in exchange for keeping static byte
  checks separate from application validity.

## Open questions and risks

- Will XenoDream byte-identically resave the generated sphere and mixed files?
- Will a modified sphere scale remain accepted in the mixed sibling slot?
- Which additional object sequence gives the most useful next recipe without
  encouraging unsupported generalization?

## Next implementation step

Pin the sphere and cube-sphere references, add failing exact-output and field
isolation tests, then implement the bounded compiler paths.
