# Centered X-row recipe

## Problem

The first procedural recipe must position objects without expanding the XDX
format model. The generator already owns immutable object specifications and
the exact five object sequences accepted by `ProjectSpec`. The private template
compiler owns record locations, numeric formatting, template hashes, and opaque
defaults. Row placement belongs between those layers.

## Usage

Python callers create supported objects, arrange them, then use the existing
compiler.

```python
from decimal import Decimal

from xenodream_xxp import CubeSpec, SphereSpec, centered_x_row, compile_project

project = centered_x_row(
    (CubeSpec(), SphereSpec()),
    spacing=Decimal("100"),
)
payload = compile_project(project)
```

The optional center sets the complete row position. The recipe replaces each
input position and preserves every other object field.

```python
from xenodream_xxp import Vector3

project = centered_x_row(
    (CubeSpec(), CubeSpec(), CubeSpec()),
    spacing=Decimal("75"),
    center=Vector3(Decimal("20"), Decimal("10"), Decimal("-5")),
)
```

The CLI exposes the same operation.

```console
xxp generate-row output/cube-sphere.xxp cube sphere --spacing 100
xxp generate-row output/three-cubes.xxp cube cube cube --spacing 75
```

## Shape

`recipes.py` owns one pure operation:

```python
def centered_x_row(
    objects: SupportedObjects,
    *,
    spacing: Decimal,
    center: Vector3 = Vector3(),
) -> ProjectSpec:
    raise NotImplementedError
```

The function validates its own `spacing` and `center` inputs. It constructs a
`ProjectSpec` before and after placement, so the existing project type remains
the only source of truth for supported sequences. For object index `i` in a
sequence of length `n`, the X coordinate is:

```text
center.x + (i - (n - 1) / 2) * spacing
```

The function uses `Decimal` arithmetic and `dataclasses.replace`. It sets Y and
Z to `center.y` and `center.z`, which makes the result a row even when input
objects already have different positions. It does not round derived values.
The compiler keeps ownership of the verified five-place transform encoding and
rejects values that require more precision.

`cli.py` maps the words `cube` and `sphere` to the existing object types, calls
`centered_x_row`, and passes the result to `compile_project`. The command does
not select templates or inspect XDX records.

The compiler remains unchanged. Unsupported sequences such as sphere followed
by cube or two spheres still fail at `ProjectSpec` construction.

## Synthesis decision

The pure-function candidate is the base because it adds one composable domain
operation and no new recipe type. The value-object candidate supplied the
complete-position replacement rule and optional center. Its `CenteredRowSpec`
class was rejected because no caller needs to retain recipe intent yet. The
compile-first candidate supplied the CLI shape, but `compile_row() -> bytes`
was rejected because it would hide the useful `ProjectSpec` result and couple
layout to serialization.

The helper candidate proposed placing the function in `generator.py`. A
separate `recipes.py` keeps construction policy out of the evidence-gated
object and compiler module. The project expects more procedural recipes, so
the module has a clear owner rather than being a permanent one-function split.

## Tradeoffs accepted

- We accept full position replacement in exchange for a row with one precise
  meaning.
- We accept that compilation can reject a finite derived position in exchange
  for keeping XDX precision rules inside the compiler.
- We accept zero spacing and negative spacing because no observed format or
  application rule forbids overlapping or reversed placement.
- We accept a small CLI object vocabulary in exchange for direct access to the
  recipe. `ProjectSpec` still rejects every unprofiled sequence.

## Alternatives considered

`CenteredRowSpec.to_project()` preserves recipe intent, but adds a public type
and a materialization step with no second consumer. `compile_row()` shortens
one call site, but prevents callers from inspecting or combining the resulting
project. Adding row fields to `ProjectSpec` would mix final project state with
one way of constructing that state.

## Risks

A spacing with five decimal places can yield a six-place half-spacing for an
even object count. The recipe returns the exact `Decimal`; `compile_project`
then raises the existing precision error. A future recipe language might need
recipe values as data. That requirement can add a value type later without
changing this function's result contract.

## Red-flag screen

The function hides placement arithmetic and immutable reconstruction behind
one call. It does not expose XDX data, duplicate the supported-sequence list,
or forward unchanged arguments to the compiler. Layout and serialization stay
separate because each result is useful on its own. The CLI is a thin input and
file-output boundary over the same operation.

## Next implementation step

Add tests that reproduce the accepted one-, two-, and three-object profile
bytes, then implement the pure placement function and CLI command.
