# XenoDream X: Text-to-Native-Project Generator

> Status: historical starting specification. The current project direction is
> [docs/project-direction.md](docs/project-direction.md). Where the documents
> conflict, the current direction governs. In particular, REA/Ghidra, other
> suitable investigation tools, and automated application testing now replace
> repeated manual discovery. Physical fabrication is the primary outcome, and
> the system must preserve project state across conversational mutations.

## Codex handoff | 2026-10-15

### Mission
Build an evidence-based workflow that converts a user's natural-language description of a 3D object into a **native XenoDream X `.xxp` project**, opened and rendered in XenoDream X. Generate procedural holons, transforms, metamorphs, materials, and scene settings, **not merely an imported mesh**.

Example desired prompt: "Create an abstract seashell sculpture with a tapered spiral, repeating curved ribs, and smooth ivory material." The generated `.xxp` should open in XenoDream X and approximate the description.

### User context and source material
- Windows desktop; XenoDream X installed and running.
- Sample directory: `C:\Users\dmona\Documents\XenoDreamX\Samples\Dirk Monteny`.
- Uploaded sample: `20061109Sirps08.xxp` (include this file in the Codex workspace separately; this handoff does not embed its contents).
- User works with Codex in VS Code and has REA/Ghidra experience. REA is an optional investigative tool, **not the starting point**.
- User values repeatability, traceable evidence, tests, incremental validation, and source-backed claims.

### Observations verified from the uploaded sample
The file is 19,797 bytes, ASCII text with CRLF line endings and long lines. It is INI-like, with section headers and key/value records. Header excerpt:

```ini
[Header]
Program=XDX
Progversion=1.007
Author=dirk monteny
Comments=Import and mod by Garth
MaxMMPars=12
NumHolons=26
```

It has **26 `[Holon\\N]` sections**, indexed 0 through 25; one `Type=0` group (`Group1`) and 25 `Type=2` holons (`Iter2` through `Iter26`). It also contains sections named `Gradients`, `TagNames`, `HolonCamera`, `SceneCamera`, `Image Generation`, `Light Sources`, `Environment Background`, `Materials`, `Material\\0`, `Material\\1`, and `SelectionSpots`.

The file includes transforms, density/iteration settings, geometry/metamorph-related parameters, gradients, materials, camera and lighting data. **Do not infer full parameter semantics from names alone.** Earlier discussion speculated that 12 transform numbers correspond to scale/skew/rotation/position; this is plausible but must be verified experimentally or against documentation.

### Architectural direction
1. **Lossless native format reader/writer**: preserve ordering, unknown keys/sections, whitespace when possible, long values, and line endings. Treat this as a round-trip serializer first, not a generic `configparser` rewrite that discards formatting.
2. **Typed intermediate representation (IR)**: project, group, holon, transform, metamorphs, material, render settings; record known vs unknown fields and supporting evidence.
3. **Validation**: structural checks, IDs/references, expected counts, value ranges when established; distinguish static validation from successful opening/rendering.
4. **Modeling planner**: turn natural-language descriptions into a constrained, versioned JSON specification using only verified modeling operations.
5. **Deterministic compiler**: compile that specification into `.xxp` without relying on free-form LLM text generation for file syntax.
6. **Render-feedback loop**: open in XenoDream, compare rendered output to desired result, adjust parameters, and save results and observations. Initially this is human-in-the-loop; automation is a later goal.

### Milestones and acceptance tests

**M0: Inventory and documentation**
- Create repository layout (`samples/`, `src/`, `tests/`, `docs/`, `experiments/`).
- Inspect the sample and any additional files supplied. Locate official documentation and examples if available; distinguish documented semantics from hypotheses.
- Record hashes and provenance of originals; never overwrite samples.

**M1: Read and round-trip**
- Parse the uploaded sample and emit a structured report: hierarchy, IDs, type codes, transforms, metamorph fields, materials, cameras.
- Serialize the unchanged parsed sample and compare byte-for-byte. Ideally achieve exact identity; otherwise explain every difference and test XenoDream acceptance.
- Automated tests for all observed sections, unusual long lines, CRLF, missing/extra fields, and unknown keys.

**M2: Controlled file diffs**
- User creates a minimal sphere in XenoDream, saves A; changes one parameter, saves B.
- Compare A/B at key/array-element level, keeping all other variables constant.
- Repeat for scale, position, rotation, color, group creation, and individual metamorph controls.
- Store each experiment's source files, UI action, expected delta, observed delta, and application outcome.

**M3: Native geometry generation**
- Generate a basic primitive, an elongated primitive, and a group of three positioned primitives.
- Verify all generated files open correctly and render as expected in XenoDream X.
- Introduce one experimentally understood metamorph; verify its effects.

**M4: Procedural modeling vocabulary**
- Build a reusable, evidence-backed library of operations/patterns from sample projects and controlled experiments.
- Prefer simple, composable geometry recipes over attempting unrestricted text-to-anything generation immediately.

**M5: Text-to-XXP prototype**
- Support a constrained prompt set (e.g. 'three spheres in a row', 'tapered column', 'radial repeated petals') with explicit capability limits.
- Translate prompt -> JSON IR -> `.xxp` -> manual XenoDream rendering -> comparison and refinement.
- Keep a reproducible record of prompt, plan, generator version, `.xxp`, preview image, and test results.

### Important engineering rules
- Do not claim a project is valid merely because it parses or passes static checks. **XenoDream is the reference implementation.**
- Preserve unknown fields. Never fabricate undocumented enum values or metamorph parameter layouts.
- Treat the sample as evidence for syntax, **not** proof of the complete format or compatibility across versions.
- Maintain a mapping: format field -> evidence (sample diff, manual, experiment) -> confidence.
- Avoid touching user originals. Write new artifacts into a designated output folder.
- Start without reverse engineering the executable. Use REA/Ghidra selectively only if file experiments/documentation are insufficient and appropriate rights/permissions have been assessed.
- Ensure all generated files and tests are reproducible.

### First assignment for Codex
1. Locate/read `20061109Sirps08.xxp` in the workspace. If missing, ask the user to copy it in; do not guess its content.
2. Inspect and document the exact section/key schema observed in this one sample, including any repeated keys or multi-number values.
3. Implement a lossless parser/serializer with tests and a CLI: `inspect`, `roundtrip`, `diff`.
4. Run `roundtrip` and report byte-for-byte identity or differences.
5. Produce a concise experiment guide asking the user to create **two minimal XenoDream X projects differing by only one UI setting**.
6. Stop at the checkpoint and report findings, open questions, and next experiments. **Do not start generating complex geometry before this foundation is verified.**

### Explicit non-goals for the first iteration
- Reconstructing the XenoDream application or rendering engine.
- Directly generating STL/OBJ in place of a native `.xxp`.
- Claiming arbitrary natural-language sculpture generation works before verified primitives and metamorphs exist.
- Training a model from sample projects before establishing their semantics and legal/provenance constraints.

### Future design question
Can XenoDream open a `.xxp` written entirely by our generator, rather than one produced by editing a saved file? Test this early with a minimal generated project and record the result.
