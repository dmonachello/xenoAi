# Metamorph mesh-probe design

## Problem

The binary registry now identifies every Sphere and Cube parameter slot, but a
native label and range do not tell us whether a value produces useful solid
geometry. The next experiment must connect one persisted token change to one
evaluated mesh without turning untested descriptor ranges into public mutation
permissions.

## Usage

Create audited one-token variants from an accepted source:

```powershell
python scripts/probe_metamorph_mesh.py prepare `
  src/xenodream_xxp/templates/xdx-1.220/sphere_base.xxp `
  output/metamorph-probe --holon 1 --parameter Warp `
  --value 0 --value 0.13 --value -0.13
```

Export each generated project with the existing supervised native runner, then
summarize the completed reports:

```powershell
python scripts/probe_metamorph_mesh.py summarize `
  output/metamorph-probe/manifest.json `
  --report output/metamorph-probe/run-000/report.json `
  --report output/metamorph-probe/run-001/report.json `
  --report output/metamorph-probe/run-002/report.json
```

## Shape

`probe_metamorph_mesh.py` owns the experiment contract. `prepare_probe` resolves
the source metamorph through the packaged registry, requires a current schema
match, parses the requested value according to the recovered descriptor, and
replaces exactly one `Pars` token. It rejects values outside the native domain,
values that need more precision than the descriptor allows, choices not listed
by the descriptor, unexpected source structure, duplicate output directories,
and any structural diff beyond the selected token.

The manifest records the immutable source hash, operation Style and name,
parameter index and descriptor, requested values, variant hashes, and exact
diffs. It does not claim that the variants are accepted or meaningful.

`summarize_probe` accepts only supervised-export reports whose input hash
matches one manifest variant. It allows repeated reports for the same variant,
measures the observed baseline variation, then compares triangle count,
dimensions, volume, components, and basic topology flags against the first
value. Runtime acceptance and geometric effects remain separate fields.

This is an experiment script, not a public generator module. It hides record
replacement and report reconciliation behind two commands while keeping the
existing application runner independent. The separation prevents a failed GUI
run from corrupting the variant manifest and avoids importing Windows-only
automation into the lossless parser or generator.

## Synthesis decision

The chosen design combines a strict variant builder with an offline report
summarizer. An integrated command that launched every export would be convenient
but would couple deterministic file construction to slow GUI state and make
partial reruns awkward. A public generic metamorph mutation API would be smaller
to call but would silently grant write authority to every recovered descriptor.
Both alternatives cross the current evidence boundary.

## Tradeoffs accepted

- We accept a two-stage command in exchange for resumable native runs and a
  deterministic manifest.
- We accept operation-specific current registry coverage in exchange for exact
  source and token validation.
- We accept basic STL metrics in exchange for reusing the tested mesh inspector;
  self-intersections and minimum local thickness remain separate work.

## Alternatives considered

Directly extend `ObjectMutation` with a parameter dictionary. That exposes
unvalidated writes to normal projects and loses the distinction between a probe
and a supported edit.

Drive XenoDream's native dice and compare its saved files. That changes several
parameters at once, has no recovered seed control, and cannot attribute a mesh
effect to one slot.

## Open questions and risks

- Which parameter magnitudes avoid both an imperceptible change and destructive
  geometry?
- Does native export normalize any probe value on load?
- Which mesh differences exceed XenoDream's measured run-to-run variation?
- Which slots change topology rather than only surface coordinates?

## Next implementation step

Implement and test the one-token variant manifest before launching any native
process.
