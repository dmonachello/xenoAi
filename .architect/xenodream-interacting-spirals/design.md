# XenoDream interacting spirals

## Problem

The user wants multiple interacting spirals made from a series of varying
holon shapes. XenoSculpt can compile and transform one RoundCube, Pipe, Torus,
Cog, or SpiralShell, but it has no evidence-authorized mixed writer for these
constructors. The design must create a useful sculpture without turning one
successful synthetic file into a claim of arbitrary duplication or scene
serialization.

## Usage

```powershell
xenosculpt generate-interacting-spirals .\output\interacting-spirals.xxp
xenosculpt project init .\output\interacting-spirals.xsp .\output\interacting-spirals.xxp
xenosculpt project validate .\output\interacting-spirals.xsp `
  --profile preview --stl-max-dimension-mm 123
```

After native acceptance, natural creation can select the same immutable seed:

```powershell
xenosculpt create .\output\interacting-spirals.xsp `
  --prompt "Create multiple interacting spirals made out of a series of varying holon shapes" `
  --model gpt-6.1-sol --export .\output\interacting-spirals.xxp
```

## Shape

```python
class InteractingSpiralProfile(StrEnum):
    INTERLEAVED_EIGHT_V1 = "interleaved-eight/v1"

@dataclass(frozen=True, slots=True)
class InteractingSpiralsSpec:
    profile: InteractingSpiralProfile = InteractingSpiralProfile.INTERLEAVED_EIGHT_V1

@dataclass(frozen=True, slots=True)
class SpiralMember:
    holon_index: int
    constructor: ClosedConstructorName
    scale: Vector3
    position: Vector3

def interacting_spiral_members(spec: InteractingSpiralsSpec) -> tuple[SpiralMember, ...]: ...
def compile_interacting_spirals(spec: InteractingSpiralsSpec | None = None) -> bytes: ...
```

The fixed member sequence is:

1. SpiralShell at `(28, 0, -30)`, scale `(28, 28, 28)`
2. Torus at `(-28, 0, -30)`, scale `(26, 26, 26)`
3. Cog at `(0, 28, -10)`, scale `(25, 25, 25)`
4. Pipe at `(0, -28, -10)`, scale `(27, 27, 27)`
5. RoundCube at `(-28, 0, 10)`, scale `(24, 24, 24)`
6. SpiralShell at `(28, 0, 10)`, scale `(30, 30, 30)`
7. Pipe at `(0, -28, 30)`, scale `(26, 26, 26)`
8. Cog at `(0, 28, 30)`, scale `(25, 25, 25)`

`xenodream_xxp.multi_spiral` owns the profile and complete byte audit. It uses
the existing `compile_closed_constructor()` as the sole authority for each
constructor block. It extracts the canonical `Holon\\1` plus `MM\\0` span,
rewrites that span to its assigned index, and assembles the eight spans between
the existing Group1 root and untouched project tail. `Header.NumHolons` becomes
9. The compiler then reparses and requires exactly `Group1` plus the eight
verified constructors in profile order, with exact IDs, group IDs, transforms,
and no diagnostics.

The public interface is one profile and one compiler. This follows Foundational
Thinking by encoding the physical arrangement before logic, Model the Domain by
making each member typed, and Boundary Discipline by keeping raw XDX records
private. No generic `AddClosedConstructor` enters mutation, planning, workspace,
or core.

Natural creation gains one seed, `InteractingSpirals`. Its recipe must be empty
in v1. The hosted model may select the seed but cannot change membership or raw
constructor parameters. The initial revision records the prompt and provider as
it does for every other seed.

## Native gate

Before public exposure, the exact compiled artifact must pass packaged preview
validation against the pinned XenoDream X 1.220 executable. Required facts are
successful outcome, native model validity, evaluated 3D output, unchanged source
and disposable hashes, confirmed cleanup, independently parsed STL, and retained
artifact/report/mesh hashes. Multiple mesh components are reported honestly and
do not by themselves invalidate native acceptance. Fabrication suitability stays
false.

## Synthesis decision

Candidate A is the base because it gives one atomic call and makes unsupported
member sequences impossible. Candidate B's repeatable append was rejected: it
would publish a general allocation and cloning rule after only one mixed-scene
proof, and callers would have to coordinate eight revisions. Iterator-native
spirals were also rejected because iterator identity, payload, ordering, and
interaction semantics remain unverified.

## Tradeoffs accepted

- We accept one fixed sculpture in exchange for honest evidence and atomic output.
- We accept a whole-project compiler in exchange for preserving the existing
  mutation layer's narrow structural authority.
- We accept that scale and position make a helical arrangement but do not claim
  an XenoDream Iterator or mathematically continuous curve.

## Alternatives considered

- Repeatable append exposes more flexibility but also exposes unproved allocation,
  retry, and partial-scene rules.
- A generic `ClosedCompositionSpec` would accept combinations not covered by the
  first native proof.
- XenoDream Iterator records could encode a procedural spiral, but their write
  semantics and relationships are not authorized by current evidence.

## Open questions and risks

- Will eight overlapping closed holons evaluate within the preview timeout?
- Will the mesh become one component, several clean components, or produce a
  topology defect where fields overlap?
- Does XenoDream preserve the assembled identity and section order when opened?

## Next implementation step

Write failing compiler tests for the exact profile and complete scene audit, then
implement `multi_spiral.py` and run the packaged native gate before wiring the
natural seed.
