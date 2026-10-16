# M15 design decision: native validation first, Cylinder second

Use Candidate A.

The existing revision database is already the authority for model identity, so validation belongs there as immutable evidence referencing a revision. Large mesh bytes remain content-addressed files. Raw run logs can remain ordinary files referenced by the database.

Implementation order:

1. Promote the supervised exporter into the package and retain the script as a thin wrapper.
2. Add the v1-to-v2 additive workspace migration, validation records, mesh storage, and `project validate`.
3. Prove the executable can run that command and that validation does not change HEAD or source bytes.
4. Recover Cylinder's current-version constructor descriptor, parameter vector, evaluator dispatch, defaults, ranges, and serialization rules with REA.
5. Cross-classify every result against the existing style-13 corpus and `XDXSystem.xmm` presets.
6. Add Cylinder only after a generated default evaluates automatically to a non-empty 3D mesh. Constructor support and printability remain distinct claims.

The Cylinder API will be descriptor-driven rather than another whole-project hardcoded combination. If static analysis does not yet establish a safe general record builder, the implementation stops at a machine-readable recovered descriptor instead of guessing.
