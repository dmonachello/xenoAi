# MoI native cylinder proof

Date: 2026-10-17

M23 proves that XenoSculpt's revision core can retain a native binary CAD
document authored by a third application. The integration targets the installed
stable MoI 4 build `4.0.2020.1222`. It does not target the installed MoI 5 beta
builds or write `.3dm` bytes directly.

## Supported operation

`xenosculpt moi create-cylinder` accepts a positive radius and height in
millimetres. A fixed script creates one cylinder at the world origin along
positive Z, names it `Cylinder1`, and asks MoI to save the native `.3dm`.

A second fresh MoI process reopens that exact document and saves a binary STL
with a pinned tessellation profile. Creation fails unless the STL has valid
basic topology and measures `2 × radius`, `2 × radius`, and `height` within
0.01 mm.

The operation runs in a unique temporary directory with separate INI files.
It never opens a user document or modifies the MoI installation. A timeout
terminates only the launched process tree. The workspace is published by an
atomic rename only after native creation, reopen, export, and inspection pass.
The separate INI prevents reuse of the user's ordinary settings file; it does
not virtualize MoI licensing or every possible AppData plugin location.

## Retained evidence

The `.3dm` is the primary content-addressed revision artifact. The derived STL
is stored separately under `run-artifacts` by SHA-256. The MoI-owned evidence
record includes:

- the executable path, exact file version, and executable SHA-256;
- the canonical cylinder request and its hash;
- both generated script hashes and process durations;
- the native and STL hashes and byte lengths; and
- the full binary-STL inspection report.

Every `status` or `export-stl` call rechecks the revision binding, evidence
hash, native artifact hash and header, retained STL path containment, STL hash
and length, and the measured mesh report.

## Live verification

The initial capability probe created a 15 mm radius by 40 mm high cylinder with
MoI 4.0.2020.1222. A fresh process reopened the 18,206-byte `.3dm` and produced
a 260,884-byte binary STL with 5,216 triangles. Its measured dimensions were
30 × 30 × 40 mm, it had one connected component, and the current topology
predicate passed.

The packaged executable repeated the request twice outside the repository. The
native files were both 18,207 bytes with different hashes, while both STL
exports had the same hash and measurements. This confirms that native byte
determinism must not be treated as CAD semantic equality. The retained record is
[`m23-moi-packaged-smoke.json`](../evidence/runtime/m23-moi-packaged-smoke.json).

The first probe used MoI's `fileExport` method and produced an empty STL because
that method exports the selected objects. The corrected unattended path uses
`saveAs`, which exports the whole reopened document without relying on selection
state.

## Limits

- M23 creates one cylinder; it does not revise an existing CAD object.
- Arbitrary `.3dm` import, semantic comparison, booleans, and general CAD scene
  modelling are not supported.
- The STL report does not check self-intersections, minimum feature thickness,
  supports, tolerances, or process suitability.
- Native `.3dm` byte equality between repeated equivalent runs is observed but
  is not required.

The detailed design is in
[`.architect/m23-moi-cylinder/design.md`](../.architect/m23-moi-cylinder/design.md).
