# Candidate B: general descriptor-driven constructor editor

## Usage

```powershell
xenosculpt generate-constructor Torus .\torus.xxp `
  --parameter MajorRadius=70 --parameter MinorRadius=18
xenosculpt project set-parameter .\torus.xsp Torus2 MajorRadius 75
```

## Shape

```python
@dataclass(frozen=True, slots=True)
class ConstructorDefinition:
    name: str
    style: int
    parameters: tuple[ParameterDefinition, ...]

@dataclass(frozen=True, slots=True)
class SetConstructorParameter:
    object_id: int
    parameter: str
    value: Decimal | int
```

The recovered descriptor table drives generation, scene recognition, CLI
parsing, and mutation.

## Why this candidate loses

Descriptors prove names, slots, ranges, and defaults. They do not prove that
arbitrary combinations evaluate safely, how parameters interact, or which
values produce closed solids. This design would turn research metadata into
write authority. Its public parameter interface would be much larger than the
native evidence behind it. The same problem stopped fabrication promotion and
the middle-Cube deletion writer.

## Red-flag audit

The definition object is coherent, but the interface leaks raw constructor
metadata and asks callers to understand XenoDream parameter policy. It fails
the evidence boundary even though the code could be clean.
