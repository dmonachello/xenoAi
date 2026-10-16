# M5 physical scale and mesh-resolution calibration

## Outcome

XenoDream X 1.220's native STL exporter has two recovered and runtime-verified
controls that are directly useful for physical sculpture:

- **STL Max Size (mm)** sets the maximum physical export dimension.
- **Mesh Size (%)** sets linear sampling resolution. Triangle count for the
  tested cube grows approximately with the square of this percentage.

The supervised exporter can now set both values through the owned XenoDream
process, verify the persisted application settings, and include them in its
machine-readable report. The generator itself was not changed.

## Static evidence

The Delphi form resource `TFMMESHEXPRM` contains these component definitions:

| Component | Caption | Minimum | Maximum | Default |
| --- | --- | ---: | ---: | ---: |
| `dseSTLMaxDim` | `STL Max Size (mm)` | 10 | 10,000 | 250 |
| `dseBatchProgsize` | `Mesh Size (%)` | 1 | 100 | 50 |

Export dispatcher `0x7d9054` reads the STL dimension field and stores it in the
global consumed by binary STL writer `0x7d0220`. The writer scales coordinates
by that value divided by the evaluated mesh's maximum extent. Batch initializer
`0x7da8e0` reads the batch mesh-size control. Grid calibration routine
`0x6e74ac` derives X/Y/Z sample counts and spacing from the requested resolution
and the model bounds.

This extends the earlier isosurface-pipeline evidence. It does not establish a
minimum printable feature size or prove that every object occupies the entire
requested envelope.

## Runtime calibration

All runs used the same accepted, XenoDream-resaved cube project. Each run used
a disposable project copy in a fresh process assigned to a kill-on-close Job
Object. Original and disposable hashes remained unchanged and owned-process
cleanup succeeded.

| Maximum | Mesh size | Measured span | Triangles | Basic topology |
| ---: | ---: | ---: | ---: | --- |
| 125 mm | 50% | 119.881 mm | 110,588 | closed, one component |
| 250 mm | 25% | 239.762 mm | 27,644 | closed, one component |
| 250 mm | 50% | 239.762 mm | 110,588 | closed, one component |
| 250 mm | 100% | 239.762 mm | 442,364 | closed, one component |

Doubling the requested maximum from 125 to 250 mm doubled the measured span
exactly while leaving triangle count unchanged. Doubling Mesh Size from 25% to
50%, and again from 50% to 100%, multiplied triangle count by approximately
four while leaving physical dimensions unchanged. The complete derived report
is `evidence/runtime/m5-cube-calibration-summary.json`.

The approximately 4.1% gap between requested maximum and the cube's measured
span is stable across scale settings. It is consistent with the sampled
isosurface not reaching the full evaluation envelope. Therefore callers should
distinguish the exporter envelope from the measured mesh bounds.

## Automation finding

`TDragSpinEdit` has separate displayed text and persisted `Value` behavior.
Programmatic `SetWindowText` changed the visible value but did not change the
export setting. Real keyboard input changed the application value, although
the HWND text could remain stale until the form was recreated. The runner now:

1. sends keyboard input to each owned spin control;
2. records the immediate control display separately;
3. reads only `STLMaxDim` and `BatchProgSize` from XenoDream's configuration
   after the owned process closes; and
4. changes a nominal success to `settings_not_applied` if persisted values do
   not equal the request.

The batch file chooser now receives the full disposable source path in one
operation. This replaced a flaky directory-navigation/list-selection sequence.

## Validation boundary

These runs establish:

1. a structurally valid native model;
2. successful native evaluation into three-dimensional geometry;
3. a binary STL with finite vertices and basic closed-manifold edge checks; and
4. deterministic relationships between physical scale, sampling resolution,
   and triangle count for the tested cube.

They do not establish self-intersection freedom, minimum wall thickness,
unsupported overhangs, process tolerances, or fabrication suitability. Those
remain separate validation stages.

## Reproduction

```powershell
python scripts/run_xenodream_batch_stl.py output/m3_generated_cube_resaved.xxp output/cal-250-50 `
  --stl-max-dimension-mm 250 --mesh-size-percent 50 `
  --report evidence/runtime/cal-250-50.json

python scripts/calibrate_xenodream_mesh.py `
  evidence/runtime/m5-cube-125mm-50pct-b.json `
  evidence/runtime/m5-cube-250mm-25pct-c.json `
  evidence/runtime/m5-cube-250mm-50pct.json `
  evidence/runtime/m5-cube-250mm-100pct-c.json `
  --output evidence/runtime/m5-cube-calibration-summary.json
```
