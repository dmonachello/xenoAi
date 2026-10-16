# Candidate A: revision-attached validation records

## Caller view

```powershell
xenosculpt project validate output/my_sculpture.xsp --stl-max-dimension-mm 120 --mesh-size-percent 60
xenosculpt project status output/my_sculpture.xsp
```

`project validate` resolves a revision, evaluates a disposable copy through the already isolated XenoDream batch exporter, imports the STL into `meshes/<sha256>.stl`, and records the complete report in SQLite. It never creates a model revision or advances HEAD.

## Types and ownership

- `native_export.py` owns `MeshExportSettings` and the supervised XenoDream export operation.
- `workspace.py` owns `NativeValidation`, schema migration, content-addressed mesh storage, and revision-to-validation relationships.
- `cli.py` owns argument parsing and exit status only.
- The validation identity hashes revision ID, executable hash, settings, report schema, and result mesh hash.

The workspace schema moves from v1 to v2 with a `validations` table. Opening v1 performs one transactional, additive migration. The original native artifact remains immutable.

## Result levels

The report keeps separate booleans for native evaluation, non-empty 3D mesh production, basic mesh validity, and fabrication suitability. STL production alone never implies printability.

## Risks

- UI automation is Windows- and XenoDream-version-specific; failures remain recorded outcomes.
- Validation can be slow, so repeat requests with the same inputs reuse a successful record.
- PyInstaller must include `pywinauto` and the promoted exporter module.

## Red-flag screen

No parallel source of revision truth, no mutable artifact replacement, no fake revision, no subprocess dependency on a repository script, and no printability overclaim.
