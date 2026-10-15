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
xxp generate-cube output/generated_cube.xxp
```

`generate-cube` uses the evidence-gated XDX 1.220 compiler. It refuses to
overwrite an existing path. Verified controls can be supplied explicitly:

```powershell
xxp generate-cube output/elongated_cube.xxp --scale 25 50 100
xxp generate-cube output/rotated_cube.xxp --rotation 10 20 30
```

Generated files still require an open-and-render check in XenoDream. Static
parsing and byte comparisons do not prove application acceptance.

Generated files belong under `output/`. Never overwrite files under
`samples/originals/`.
