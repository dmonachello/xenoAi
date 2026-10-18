# Interacting XenoDream spirals

XenoSculpt can create one exact XDX 1.220 composition containing eight varied
closed holons arranged as two interleaved four-member helices. The profile is
named `interleaved-eight/v1`.

Create it directly:

```powershell
xenosculpt generate-interacting-spirals output/interacting-spirals.xxp
xenosculpt project init output/interacting-spirals.xsp `
  output/interacting-spirals.xxp
```

Or ask the hosted planner for the same bounded scene:

```powershell
xenosculpt create output/interacting-spirals.xsp `
  --prompt "Create multiple interacting spirals made out of a series of varying holon shapes" `
  --model MODEL_FROM_AUTH_MODELS `
  --export output/interacting-spirals.xxp
```

The members, in physical section order, are `SpiralShell2`, `Torus3`, `Cog4`,
`Pipe5`, `RoundCube6`, `SpiralShell7`, `Pipe8`, and `Cog9`. Each member uses an
exact previously native-evaluated constructor vector. The compiler changes only
its verified scale and position fields, assigns contiguous IDs and sections,
and verifies the complete scene before returning bytes.

The packaged native proof loaded the generated artifact in XenoDream X 1.220
under the `preview` profile at 123 mm and 10 percent density. It produced a
5,326-triangle, one-component mesh with zero boundary, non-manifold,
inconsistent-winding, or degenerate-triangle defects. Source and disposable
XDX hashes stayed unchanged, and process cleanup completed.

This is a named composition, not a general spiral grammar. It does not expose
arbitrary member counts, paths, spacing, constructor parameters, XenoDream
Iterator records, or free-form mixed-scene insertion. Scale and position remain
editable through the existing typed object operations. Native evaluation does
not establish self-intersection freedom, minimum feature size, process fitness,
or fabrication suitability.
