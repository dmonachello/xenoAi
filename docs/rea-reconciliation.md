# XenoDream X 1.220 reconciliation and investigation baseline

Date: 2026-10-16

This report is the gate between the manual investigation and executable-led
reverse engineering. It does not authorize changes to the generator. Binary
findings are compared with observed application behavior and are not treated as
more authoritative merely because they came from decompilation.

## Physical-sculpture objective

The primary outcome is an editable native XenoDream project that evaluates to
genuinely three-dimensional geometry, can be converted to a mesh, passes
geometric validation, and is suitable for a stated fabrication process. These
are four separate acceptance levels:

1. structurally valid native `.xxp` project;
2. successful evaluation into three-dimensional geometry;
3. valid mesh, including manifoldness, closure, components, and intersections;
4. fabrication suitability, including scale, minimum feature thickness,
   supportedness, and process-specific tolerances.

Rendering, lighting, cameras, and image-generation settings are secondary
unless they directly help inspect geometry.

## Inventory and baseline

The repository contains one immutable original sample (19,797 bytes), 46
experiment `.xxp` files (166,297 bytes), 35 generated/output `.xxp` files
(145,814 bytes), 25 experiment directories, nine format/design/acceptance
documents, regression tests, and an append-only decision log. The installed
XenoDream user corpus adds 247 `.xxp` files (2,127,260 bytes), including 215
vendor samples and 30 shapes. This corpus can be mined automatically instead of
asking for combinations to be recreated manually.

The installed target is `XenoDreamX.exe` version 1.22.0.0, 6,289,920 bytes,
PE/i386, SHA-256
`1674590ed60cea95cfeef076dfdafce4384fb86f118f087c42e23fd9429f1b6e`.
REA 6.4.0 successfully opened it with Ghidra 12.1.4 and completed default
analysis: 8,667 procedures and 10,463 defined strings. The retained evidence
bundle is `evidence/rea/initial-session.json`.

The installation also contains plaintext system data. Most importantly,
`XDXSystem.xmm` has 60 named sections and 517 assignments, including Sphere,
Cube, RoundCube, Disc, Frame, Triangle, Torus, Cylinder, Cog, Pipe,
SpiralShell, Juliabulb, JuliaN, Maskit, and Terrain families. Its rows contain
presets and parameter payloads. Their exact schema is not yet established.

## 1. What the manual investigation established

The 89-test baseline passes. The parser and serializer preserve every source
byte, including unknown records, repeated sections and keys, malformed lines,
line endings, and absent final newlines. Inspection and occurrence-aware diffs
are read-only projections over that lossless representation.

For XDX 1.220, controlled save/readback experiments established these bounded
file-to-UI mappings:

- `Transform` tokens 0-2: X/Y/Z scale;
- tokens 6-8: X/Y/Z rotation in the tested cube context;
- tokens 9-11: X/Y/Z position;
- `GradDensity`: Color Density in tested group and cube contexts;
- Cube Style 5 `Pars[0]`: Face Warp.

Generated one-, two-, and three-cube projects, a sphere, and a cube followed by
a sphere opened and rendered in XenoDream. Accepted reference outputs were
resaved byte-identically except for one observed normalization of opaque
`SelectionSpots`, after which the normalized sphere became the template.

Observed structure establishes `NumHolons` for the tested shapes, child
`GroupID=0` under Group1, adjacent metamorph sections, and a distinction between
section position and persistent identity after deletion. It does not establish
a universal ID allocator, arbitrary object order/count, nested hierarchy, or
constructor dispatch rule.

## 2. What REA confirms

The first executable findings confirm rather than replace the manual evidence:

- Loader function `0x60af28` selects `[Header]`, reads program/version fields,
  reads `NumHolons`, rejects values below one, allocates that count, and loops
  over each holon through subordinate deserializers. This **CONFIRMS** that
  `Header.NumHolons` controls loaded record count in 1.220 and **EXTENDS** the
  evidence with a lower-bound check and a concrete loader path.
- `SelectionSpots` reader `0x60e698` and writer `0x61781c` operate on nine
  selection collections. Each persisted nonempty value contains collection
  metadata, an item count, and holon IDs; loading retains only IDs that resolve
  to loaded holons. This **EXTENDS** the manual normalization evidence and
  explains why the field can change without changing geometry. The UI meaning
  of each of the nine collection slots remains unresolved.
- Mesh-export dispatcher `0x7d9054` maps format selector 1 to OBJ, 2 to STL, 3
  to POV-Ray include, and 4 to PLY. This **EXTENDS** the prior project work,
  which had no mesh-export implementation evidence.
- STL writer `0x7d0220` emits a binary STL structure: an 80-byte header, a
  32-bit triangle count, and 50-byte triangle records containing a normal and
  three vertices. It applies a computed scale whose source fields are not yet
  identified.
- Functions `0x7d93f8` and `0x7da49c` control a mesh-preview manifold-status display and
  display `Manifold` or `NOT Manifold` based on an unknown flag and two unknown
  global values. These are status-display paths; the underlying topology test
  has not yet been located.
- Embedded application help states that the Mesh constructor imports OBJ, PLY,
  or STL triangle meshes and currently caps them at 10 million triangles. This
  is a separate import capability, not proof of export quality.

## 3. What REA adds

REA/Ghidra is sufficient for systematic static investigation on this machine.
It provides string searches, cross-references, complete function dossiers,
decompilation, assembly, callers/callees, control flow, and retained evidence.
It has already exposed:

- the native project loader entry path and holon-count loop;
- native OBJ/STL/PLY/POV export dispatch;
- distinct ASCII and binary PLY writers;
- OBJ vertex/normal/face emission;
- a binary STL writer and scale path;
- manifold-status display logic, with the underlying test still to recover;
- a built-in asynchronous batch state machine that drives model preparation,
  evaluation, optional intermediate processing, and final mesh export;
- embedded descriptions of constructor and metamorph families;
- a large plaintext preset/parameter database and a 247-file validation corpus.

These sources can reveal families of operations and metadata without one
manual sample per combination.

## 4. Disagreements

No confirmed contradiction between executable evidence and verified manual
behavior has been found in this first pass.

There are interpretation hazards that remain deliberately unresolved:

- the binary checks `NumHolons >= 1`, but this does not prove every positive
  count is structurally valid;
- `SelectionSpots` normalization is consistent with selection-list cleanup and
  no longer needs to be treated as unknown geometry state; exact slot labels
  are still unknown;
- `Manifold` is an application label, not proof that its test covers closure,
  orientation, self-intersections, or printability;
- embedded help and `XDXSystem.xmm` describe installed version 1.220 and cannot
  be projected backward onto the 1.007 sample without a version branch check;
- cube and sphere still both use `Type=1`; constructor selection remains
  unresolved despite their differing metamorph styles and payloads.

Any future `CONTRADICTS` finding must be investigated for version differences,
hidden defaults, conditional paths, and decompiler error before code changes.

## 5. What remains unknown

Highest-priority physical-geometry unknowns are:

1. which constructors, iterators, and metamorphs produce closed volumetric
   geometry rather than surfaces or render-only displacement;
2. constructor/style dispatch tables and the complete parameter descriptor
   schema: names, types, defaults, units, ranges, and constraints;
3. evaluation order and transform composition through groups, constructors,
   iterators, and metamorph stacks;
4. mesh sampling/tessellation controls, how detail influences triangle count
   and surface error, and how export dimensions map to physical units;
5. the exact manifold test and whether XenoDream detects boundaries,
   inconsistent orientation, duplicates, degeneracy, or intersections;
6. hierarchy, identity allocation, references, deletion/reorder repair, and
   arbitrary flat or nested composition;
7. loader requirements, defaults, migration paths, numeric parsing, limits,
   and error handling;
8. disconnected-component behavior, minimum feature thickness, and whether
   any native operation repairs or unions geometry;
9. automated invocation of load, evaluate, mesh generation, and export;
10. STL coordinate units and whether 3MF is supported. No `3MF` string was
    found in defined strings, so support is currently **UNRESOLVED**, not
    disproved.

## 6. Findings that can improve generation immediately

No generator change is justified yet. The immediately useful improvements are
to the knowledge pipeline:

- replace per-combination templates as the discovery strategy with recovery of
  the holon factory, constructor/metamorph registries, parameter descriptors,
  and serializer rules;
- mine `XDXSystem.xmm` and the vendor corpus to map operation names to persisted
  styles and payload widths, then confirm those mappings at binary dispatch
  functions;
- build mesh-export automation around the recovered selector and writer paths;
- use an external mesh-validation stage even if XenoDream reports `Manifold`;
- preserve the existing generator as a regression oracle until recovered rules
  reproduce all accepted outputs and pass application-level validation.

## Prioritized recovery plan

1. Trace mesh generation and export from the UI handler through tessellation,
   manifold checking, scaling, and STL/OBJ/PLY writers.
2. Recover constructor and metamorph registries, beginning with operations that
   plausibly produce closed 3D solids and the already verified Cube/Sphere
   records.
3. Reconcile registry metadata with `XDXSystem.xmm` and automatically cluster
   the 247-file corpus by Type, Style, `NumPars`, and section topology.
4. Trace model evaluation order, transforms, hierarchy, IDs, and references.
5. Trace project save paths and required/default fields, then design a general
   native writer without replacing verified code prematurely.
6. Automate application acceptance where feasible; add external mesh checks for
   closure, manifoldness, orientation, components, intersections, thickness,
   and dimensions.
7. Only then extend the generator in small, regression-protected slices.

## Manual experiments eliminated or retained

Eliminated as the normal discovery method: one sample per object combination,
one UI edit per parameter label/default/range, manual enum hunting, and manual
inference of save order or ID allocation.

Retained only as validation: a small number of automated load/evaluate/export
round trips, quantitative comparison of geometry for recovered formulas, and
human inspection when sculpture intent or fabrication aesthetics cannot be
measured automatically.

Detailed classifications and evidence links are in
`docs/rea-cross-validation.tsv`; machine-readable claims are in
`spec/xdx-knowledge.json`.

## Mesh-pipeline checkpoint

The next REA pass completed the highest-value physical-geometry trace. The
application fills a scalar volume, detects isosurface crossings on the 12 edges
of each sampled cell, builds shared indexed triangles, computes triangle
normals, and runs named de-noising, simplification, and smoothing stages before
native mesh export. This **EXTENDS** the manual open/render evidence and does
not contradict any accepted generator behavior.

The installed Batch Export form already drives repeated project evaluation and
OBJ/STL/POV/PLY export. It is GUI-configured and message-driven; no supported
headless batch switch was found. Windows UI Automation is therefore the next
safe way to eliminate routine manual acceptance work.

The installed corpus is now reproducibly inventoried by
`scripts/inventory_xdx_corpus.py`. All 247 files round-trip exactly, all
declared holon counts match, and all 953 metamorph parameter counts match their
payload token counts. Constructor/style correlations remain candidates because
most files predate 1.220 and names may be edited.

See `docs/rea-mesh-pipeline.md` and cross-validation rows R012-R017 for the
complete trace, limitations, and next automated experiment.
