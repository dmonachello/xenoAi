# Candidate B: repeatable closed-constructor append

## Usage

```powershell
xenosculpt project add-closed shape.xsp --constructor SpiralShell --position 28 0 -30
xenosculpt project add-closed shape.xsp --constructor Torus --position -28 0 -30
```

## Shape

```python
@dataclass(frozen=True, slots=True)
class AddClosedConstructor:
    constructor: ClosedConstructorName
    scale: Vector3
    position: Vector3

def append_closed_constructor(data: bytes, operation: AddClosedConstructor) -> CompositionRewrite: ...
```

The writer would admit a flat Group1 scene, allocate the next ID/name/section,
clone a canonical constructor block, and commit one revision per append.

## Rationale

This surface looks flexible but leaks the unproved allocation and repeatability
policy to every caller. A crash or rejection midway leaves a partial sculpture,
and current evidence does not authorize arbitrary constructor sequences,
fourth-through-eighth allocation, or add-after-edit behavior. It is rejected
for the first release. It may follow after several independently accepted
mixed compositions establish the generic rule.

