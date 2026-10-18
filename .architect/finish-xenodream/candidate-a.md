# Candidate A: promote exact single-object constructors

## Usage

```powershell
xenosculpt generate-constructor Torus .\torus.xxp `
  --scale 60 60 40 --position 0 0 10
xenosculpt project init .\torus.xsp .\torus.xxp
xenosculpt project prompt .\torus.xsp `
  "set object Torus2 position to 25 0 10"
xenosculpt project validate .\torus.xsp `
  --profile preview --stl-max-dimension-mm 123
```

## Shape

```python
class ClosedConstructorName(StrEnum):
    ROUND_CUBE = "RoundCube"
    PIPE = "Pipe"
    TORUS = "Torus"
    COG = "Cog"
    SPIRAL_SHELL = "SpiralShell"

@dataclass(frozen=True, slots=True)
class ClosedConstructorSpec:
    constructor: ClosedConstructorName
    scale: Vector3 = Vector3(Decimal("50"), Decimal("50"), Decimal("50"))
    position: Vector3 = Vector3()

def compile_closed_constructor(spec: ClosedConstructorSpec) -> bytes: ...
```

`constructor.py` owns the closed profile table, scaffold rewrite, byte audit,
and canonical hashes. `scene.py` recognizes only these exact current-version
profiles. It advertises scale and position only after native transformed-
artifact tests pass. The existing `ObjectMutation` and workspace revision path
perform later edits. The public interface hides styles, parameter vectors, and
descriptor recovery.

## Tradeoffs

- We accept five exact default constructor profiles in exchange for shipping
  useful new forms without claiming a general serializer.
- We keep constructor parameters read-only in exchange for avoiding unmeasured
  interaction claims.

## Red-flag audit

One compiler call hides profile selection and byte auditing. XDX style numbers
and raw parameter vectors remain private. The module is organized around
constructor knowledge, not generation stages. No pass-through layer is added.
