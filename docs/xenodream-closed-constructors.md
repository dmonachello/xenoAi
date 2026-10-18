# Closed XenoDream constructors

`generate-constructor` creates one exact XDX 1.220 project for a
native-evaluated constructor profile.

```powershell
xenosculpt generate-constructor Torus .\torus.xxp `
  --scale 60 60 40 --position 0 0 10
xenosculpt project init .\torus.xsp .\torus.xxp
xenosculpt project prompt .\torus.xsp `
  "set object Torus2 position to 25 0 10" `
  --message "move the torus"
xenosculpt project validate .\torus.xsp `
  --profile preview --stl-max-dimension-mm 123
```

The accepted names are `RoundCube`, `Pipe`, `Torus`, `Cog`, and
`SpiralShell`. The compiler uses a fixed constructor style, arity, and default
parameter vector recovered from the pinned XenoDream X 1.220 executable. It
starts with the normalized one-object scaffold, changes only the constructor
identity and requested scale and position tokens, audits the complete diff,
and checks the canonical default artifact hash.

The scene reader advertises `set-scale-v1` and `set-position-v1` only when the
constructor has the exact admitted parameter vector. A manual parameter change
makes the node read-only. Rotation, raw parameter editing, mixed-scene
insertion, duplication, and fabrication suitability remain unsupported.

All five non-default transformed artifacts passed managed native preview
validation. Each produced one connected component with no boundary,
non-manifold, inconsistent-winding, or degenerate-triangle defects. The first
SpiralShell attempt hit the source-chooser automation timeout, cleaned up, and
the fresh retry succeeded with the same artifact hash. See
[`xenodream-closed-constructor-promotion.json`](../evidence/runtime/xenodream-closed-constructor-promotion.json).

These checks establish native loading and evaluation for the exact profiles.
They do not establish arbitrary constructor parameter combinations,
self-intersection freedom, minimum feature size, printer process rules, or a
physical fabrication result. Every generated or transformed revision requires
native validation and remains fabrication-unsuitable.

