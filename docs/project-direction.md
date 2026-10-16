# Project direction: conversational control for physical sculpture

Date: 2026-10-16

This document defines the current direction. It preserves the existing
XenoDream generator and its evidence. It replaces the original handoff only
where that handoff treats manual experiments as the main discovery method or
systematic executable investigation as merely optional.

## Goal

Build a conversational system that controls existing creative applications and
keeps their native artifacts editable. XenoDream X is the first application.
The immediate outcome is an original procedural sculpture that the user can
create, revise through later prompts, open in XenoDream, export as a mesh, and
fabricate.

MoI3D, ComfyUI, and HueForge are later candidates. Do not build a generic
multi-application framework until the XenoDream implementation reveals which
parts are genuinely reusable.

## Investigation tool policy

Use whichever lawful and technically appropriate tools best answer the current
question or advance the fabrication goal. REA/Ghidra is the primary static
analysis environment for XenoDream, not an exclusive tool requirement.

The available methods include:

- official documentation, embedded help, installed metadata, and corpus mining;
- REA/Ghidra, other disassemblers and decompilers, debuggers, and runtime tracing;
- documented APIs, command-line tools, native file generation and mutation,
  scripting, and Windows UI Automation;
- controlled process, file, registry, and system-call observation or
  instrumentation; and
- mesh-processing, validation, repair, CAD, slicing, automated testing,
  quantitative comparison, and fabrication experiments.

Choose the least invasive method that can produce reliable evidence. Preserve
original artifacts and isolate runtime experiments. Record the target version,
artifact hash, tool and method, evidence location, interpretation, confidence,
and unresolved questions. Cross-validate binary findings against existing
models, experiments, tests, and observed application behavior. Decompiled code
is evidence, not automatic authority.

Do not make repeated user-operated experiments the routine discovery process.
Do not reconstruct unrelated parts of the application. Invoke internal
application functions only when static and runtime evidence establishes a safe,
necessary reason to do so.

## What the repository already proves

The current code has four useful foundations.

1. The lossless parser preserves arbitrary observed `.xxp` bytes. It retains
   unknown records, order, duplicate keys, whitespace, and line endings.
2. The evidence-gated generator creates the accepted Cube, Sphere, projects
   containing one to three Cubes, and Cube-then-Sphere profiles. XenoDream
   opened and rendered these files. Accepted resaves serve as regression
   references.
3. REA/Ghidra findings are cross-validated against manual experiments in
   `docs/rea-cross-validation.tsv`. The investigation has recovered loader,
   selection-state, isosurface evaluation, mesh-processing, batch-export, and
   STL scaling paths.
4. The supervised runtime starts an isolated XenoDream process, evaluates a
   disposable project, exports STL, and cleans up its process. M5 established
   millimetre scaling and the relationship between sampling resolution and
   triangle count.

The current suite has 110 tests. The standalone `xenosculpt.exe` build can
generate the supported native projects, inspect `.xxp`, compare files, and run
basic binary-STL validation.

## What the current generator is

The generator has a small semantic model, but it does not yet have a general
XenoDream model representation.

`Document` is a lossless syntax model. `ProjectSpec`, `CubeSpec`, `SphereSpec`,
and `Vector3` are typed semantic inputs for a few verified operations. The
compiler selects a hash-pinned whole-project template and replaces an allowed
set of fields or tokens.

This design was correct for proving native generation without corrupting opaque
state. It is not enough for reliable conversational editing because it cannot:

- represent arbitrary holons, groups, iterators, or metamorph stacks;
- load an arbitrary current project into a semantic scene model;
- mutate one object while preserving every unrelated semantic property;
- add, remove, reorder, or reparent arbitrary objects using recovered identity
  and reference rules; or
- express most of XenoDream's procedural modeling vocabulary.

Keep the accepted template compiler as a regression oracle. Replace its limits
incrementally as serializer and scene rules become verified.

## What remains unknown

The main application-knowledge gaps are:

- the complete holon factory and constructor, iterator, and metamorph
  registries;
- parameter names, types, defaults, ranges, units, and formulas;
- general object identity, hierarchy, ordering, reference, and deletion rules;
- model evaluation order and transform composition;
- which operations yield closed solids and how combinations affect
  connectedness and feature thickness;
- the full native serializer contract, including defaults and version paths;
- mesh-processing algorithms and safe settings; and
- native or external repair behavior that preserves the intended form.

REA/Ghidra can investigate the first six items directly through factories,
dispatch tables, descriptor metadata, UI bindings, evaluators, and load/save
callers. The installed `XDXSystem.xmm` database and 247-project corpus provide
independent data for cross-validation. Runtime exports must still verify
geometry formulas and application behavior.

## What prevents consistent printable sculpture generation

A structurally valid `.xxp` and a closed STL are not enough. The current system
does not yet check:

- self-intersections;
- minimum wall and feature thickness;
- unsupported floating components;
- process-specific overhangs and support needs;
- printer build volume and tolerance rules;
- repaired-mesh fidelity; or
- fabrication results.

The generator also lacks enough verified procedural operations to design a
wide range of original forms. The small Cube and Sphere vocabulary proves the
pipeline, not the artistic objective.

## Conversational architecture

Build the XenoDream implementation around five boundaries.

1. **Project state** stores the active native artifact, application version,
   fabrication constraints, current revision, and revision history.
2. **Intent interpretation** converts a prompt into a typed creation or
   mutation plan. It never writes `.xxp` syntax directly.
3. **The XenoDream adapter** applies verified operations through native file
   compilation or mutation and supervised application automation.
4. **Revision control** records parent revisions, branches, prompts, operation
   plans, artifact hashes, and validation results. Importing a manual XenoDream
   edit creates a new revision instead of discarding history.
5. **Validation feedback** evaluates the native model, inspects the mesh, checks
   fabrication constraints, and returns specific failures to the planner.

Use documented APIs or scripting when an application provides them. Use native
file generation and UI Automation for XenoDream. Invoke internal functions only
after static and runtime evidence establishes a safe reason to do so.

## How evidence controls implementation

Continue to classify each significant finding as `CONFIRMS`, `EXTENDS`,
`CONTRADICTS`, or `UNRESOLVED`. Connect the finding to manual evidence, function
addresses, interpretation, confidence, open questions, and generator impact.

Do not replace verified behavior with plausible decompiler output. Investigate
disagreements for version differences, hidden defaults, conditional behavior,
and decompiler errors. Convert useful manual experiments into automated
regressions.

Use manual work only for questions that static analysis and automation cannot
answer, especially artistic judgment and final fabrication assessment.

## Next three tasks

### 1. Add persistent revisions and controlled mutations

Create a project workspace format that records the active `.xxp`, its hash,
the XenoDream version, fabrication constraints, and an append-only revision
graph. Add typed mutation operations for the fields already verified, including
scale, rotation, position, Cube Face Warp, and supported row placement.

The first mutation command must load the current native artifact, change only
the requested verified fields, preserve unrelated bytes, write a new revision,
and support branch, compare, restore, and import of a manual edit. Use a
structured plan before accepting unrestricted prompts.

### 2. Recover and implement the general scene model incrementally

Trace the holon factory, constructor and metamorph registries, parameter
descriptors, hierarchy rules, and save path. Reconcile each rule with the
installed metadata, the 247-project corpus, and accepted outputs.

Introduce typed `Holon`, `Group`, `Operation`, and `Parameter` records only when
the binary and observed files support them. Start with closed volumetric
operations useful for sculpture, such as Cylinder, Torus, Pipe, RoundCube, Cog,
and SpiralShell. Require the new writer to reproduce current accepted projects
before it replaces any template path.

### 3. Close the prompt-to-fabrication loop

Add a text command that maps a request to a versioned, inspectable operation
plan, applies it to the active revision, exports a measured mesh, and runs a
fabrication profile. Add external checks for intersections, thickness,
components, build volume, and process constraints. Keep repair optional and
measure its deviation from the source mesh.

Generate variations as branches. A later prompt must select or mutate the
correct branch without replacing the original. Record prompts, plans, native
artifacts, mesh reports, corrective attempts, manual interventions, and final
fabrication results for the research dataset.

## Success test

The milestone succeeds when one conversation produces an original sculpture,
then modifies that same design through several prompts while retaining its
constraints and history. The final native project must open in XenoDream. Its
exported mesh must pass the selected fabrication profile, and the object must
be fabricated successfully.
