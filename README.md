# XenoDream X `.xxp` tools

This repository starts with a conservative reader and writer for XenoDream X
parameter files. The current milestone preserves observed syntax. It does not
claim that static parsing proves XenoDream accepts a file.

The supplied reference is preserved at
`samples/originals/20061109Sirps08.xxp`. Its provenance and hash are recorded in
`samples/SHA256SUMS` and `docs/format-evidence.tsv`.

## Development

```powershell
python -m pip install -e .
pytest
python scripts/verify_reference.py
xxp inspect samples/originals/20061109Sirps08.xxp
xxp roundtrip samples/originals/20061109Sirps08.xxp output/roundtrip.xxp
xxp diff samples/originals/20061109Sirps08.xxp output/roundtrip.xxp
```

Generated files belong under `output/`. Never overwrite files under
`samples/originals/`.
