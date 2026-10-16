# M6 persistent revisions and controlled mutations

## Result

The project now preserves an existing native XDX artifact in a persistent
workspace and applies evidence-backed changes as new revisions. The original
file is never modified.

A workspace contains:

- `project.sqlite3`, which stores metadata, fabrication constraints, revisions,
  parent relationships, prompts, operations, branches, and HEAD state; and
- `artifacts/<sha256>.xxp`, which stores directly accessible native projects by
  content hash.

Artifact bytes are written and verified before a SQLite transaction records a
revision and advances its branch. An interrupted operation therefore cannot
leave a branch pointing to a missing artifact. Reapplying an operation that
does not change any bytes creates no revision.

## Mutation boundary

The mutation engine accepts XDX 1.220 files, identifies unambiguous verified
Cube and Sphere records, and replaces only established fields:

- Cube scale, rotation, position, color density, and Face Warp;
- Sphere scale and position; and
- centered X-axis row placement for the five supported object sequences.

It rejects unsupported versions, ambiguous names, unknown object signatures,
unverified Sphere controls, excessive numeric precision, and unexpected diffs.
Every result must pass an exact parser round trip.

## Verification

The complete suite passes: 124 tests.

The rebuilt `dist/xenosculpt.exe` has SHA-256
`c035fa63de707169d343910d17c66d7901b66b7376504a0c73651e8b7a3c0ad1`.
An end-to-end executable run performed these operations:

1. generated a native cube;
2. initialized an FDM workspace with build-volume and feature-size constraints;
3. recorded a prompted scale mutation on `main`;
4. created and checked out an `alternate` branch;
5. recorded a Face Warp mutation on that branch;
6. compared `main` with `alternate`;
7. checked out `main`; and
8. exported the active artifact.

The exported project is 3,378 bytes with SHA-256
`a8b5b9d5963f5f1ef424d224871e00dd8c8391059e9117ca4579d3035159024d`.
That is byte-identical to the previously XenoDream-opened, rendered, and
byte-identically resaved elongated-cube acceptance artifact. This confirms
that revision operations preserved the accepted native output. It does not
establish printability or validate the alternate branch in XenoDream.

## Remaining work

The workspace records prompts but does not yet translate unrestricted natural
language into operation plans. It also does not enforce recorded fabrication
constraints. Those capabilities build on this typed, auditable revision
boundary.
