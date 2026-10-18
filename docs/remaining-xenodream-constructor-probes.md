# XenoDream constructor probes

The closed constructor probe recovers descriptor metadata from the pinned
XenoDream X 1.220 executable, derives one default candidate from the normalized
Sphere scaffold, finds historical corpus anchors, and evaluates the candidate
through the managed preview profile.

```powershell
python .\scripts\probe_xenodream_constructors.py `
  --constructor RoundCube `
  --corpus-root "$HOME\Documents\XenoDreamX" `
  --output-dir C:\new-empty-directory
```

The accepted names are `RoundCube`, `Pipe`, `Torus`, `Cog`, and `SpiralShell`.
The output directory must be new or empty. It retains the candidate XDX,
revision workspace, native validation evidence, mesh, and `manifest.json`.

The 2026-10-18 campaign recovered complete contiguous descriptor sets and
obtained a successful native preview for all five candidates. Each produced
one connected component with no boundary, non-manifold, inconsistent-winding,
or degenerate-triangle defects. The first Torus attempt ended in a batch source
chooser automation timeout; cleanup succeeded, and a fresh retry verified the
same candidate hash.

The probe itself remains research-only and never grants write authority. A
later promotion gate added a closed public compiler for the same five exact
default vectors, proved canonical artifact hashes, and natively evaluated
non-default scale and position variants. See
[Closed XenoDream constructors](xenodream-closed-constructors.md).

Raw parameter mutation, interaction behavior, mixed-scene insertion, and
printability remain unsupported. `writer_authorized` and `registry_promoted`
in old probe manifests describe what the probe authorized at the time; the
separate promotion evidence is the authority for the current compiler.

The retained campaign summary is
[`remaining-constructor-probes.json`](../evidence/runtime/remaining-constructor-probes.json).
