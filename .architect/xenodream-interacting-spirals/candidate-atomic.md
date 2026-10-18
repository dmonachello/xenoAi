# Candidate A: atomic interacting-spirals compiler

## Usage

```powershell
xenosculpt generate-interacting-spirals .\output\interacting-spirals.xxp
xenosculpt project init .\output\interacting-spirals.xsp .\output\interacting-spirals.xxp
```

Natural creation may select the same fixed seed:

```powershell
xenosculpt create .\output\interacting-spirals.xsp `
  --prompt "Create multiple interacting spirals made from varying holon shapes" `
  --model gpt-6.1-sol --export .\output\interacting-spirals.xxp
```

## Shape

```python
@dataclass(frozen=True, slots=True)
class InteractingSpiralsSpec:
    profile: Literal["interleaved-eight/v1"] = "interleaved-eight/v1"

@dataclass(frozen=True, slots=True)
class SpiralMember:
    holon_index: int
    constructor: ClosedConstructorName
    scale: Vector3
    position: Vector3

def interacting_spiral_members(spec: InteractingSpiralsSpec) -> tuple[SpiralMember, ...]: ...
def compile_interacting_spirals(spec: InteractingSpiralsSpec | None = None) -> bytes: ...
```

`multi_spiral.py` owns the exact eight-member profile, extracts one canonical
object span from each existing closed-constructor compiler, rewrites only its
section identity, persisted ID, name, and already-authorized transform tokens,
then assembles one Group1 project. It audits the complete record sequence,
exact parser roundtrip, scene identities, constructor recognition, scale, and
position. The CLI and natural creator call one function and never coordinate
member insertion.

## Rationale

This is a deep interface. One profile name hides allocation, section rewriting,
constructor selection, record assembly, and semantic audits. Illegal arbitrary
member combinations are unrepresentable. The price is intentional narrowness:
the first native proof authorizes one useful sculpture, not generic cloning.

