# Schema observed in `20061109Sirps08.xxp`

This document describes one XenoDream X 1.007 sample. Names are transcribed
literally. They do not establish parameter meanings, required fields, allowed
values, or compatibility with another version.

## Physical syntax

- 19,797 bytes, all in the 7-bit ASCII range.
- 1,001 physical records, all terminated by CRLF, including the last record.
- 38 section headers, 925 key/value records, and 38 empty records.
- A section is observed as `[name]`. A key/value record uses the first `=` as
  its separator.
- No key repeats within a section in this sample. The parser still preserves
  repeated keys because one sample cannot prove uniqueness.
- The longest line is 3,018 bytes: key `0` in section `Gradients`.

## Section order and keys

| Section or family | Count | Keys in observed order |
| --- | ---: | --- |
| `Header` | 1 | `Program`, `Progversion`, `Author`, `Comments`, `MaxMMPars`, `NumHolons` |
| `Holon\0` | 1 | `ID`, `GroupID`, `Type`, `Name`, `Transform`, `Density`, `MinIters`, `MaxIters`, `MaxSelf`, `ConstructorScale`, `PostMetas`, `Visible`, `Free`, `GradientID`, `GradDensity`, `GradOffset`, `GradWrap`, `UPars`, `VPars`, `WPars`, `UVBlend`, `VWBlend`, `ColorMask`, `ColorMaskMode`, `IterShift`, `InheritTag`, `InheritUVW`, `InheritGrad`, `MixDetail`, `MixResolution`, `MixMode`, `MixUVW`, `MixShiftPlus`, `MinV` |
| `Holon\1` through `Holon\25` | 25 | `ID`, `GroupID`, `Type`, `Name`, `Transform`, `Density`, `MinIters`, `MaxIters`, `MaxSelf`, `ConstructorScale`, `PostMetas`, `Visible`, `Free`, `Tag`, `CastShadow`, `GradientID`, `GradDensity`, `GradOffset`, `GradWrap`, `UPars`, `VPars`, `WPars`, `UVBlend`, `VWBlend`, `ColorMask`, `ColorMaskMode`, `IterShift`, `InheritTag`, `InheritUVW`, `InheritGrad`, `GradIters`, `ParentShift` |
| `Gradients` | 1 | `0` |
| `TagNames` | 1 | `0` |
| `HolonCamera` | 1 | `PanX`, `PanY`, `LogZoom`, `Direction` |
| `SceneCamera` | 1 | `Projection`, `AspectW`, `AspectH`, `AngleOrder`, `ClipFront`, `ClipBack`, `Position`, `Angles`, `LogZoom`, `FoV` |
| `Image Generation` | 1 | `Transparent`, `Absorption`, `TransResolution`, `Oversample`, `Margins`, `ShadowRes`, `AlphaGamma`, `AlphaLevel` |
| `Light Sources` | 1 | `NumLights`, `Ambient`, `Light\1`, `LightEx\1`, `Light\2`, `LightEx\2`, `Light\3`, `LightEx\3`, `Light\4`, `LightEx\4` |
| `Environment Background` | 1 | `PanV`, `PanH`, `Roll`, `EnvType`, `EnvMapName`, `EnvGrad`, `BackType`, `BackGrad`, `BackImgName` |
| `Materials` | 1 | `NumTagMaterials`, `TagMaterials`, `NumMaterials` |
| `Material\0` | 1 | `Name`, `NumLayers`, `NumTextures` |
| `Material\0\Layer\0` | 1 | `DiffGradMode`, `SpecGradMode`, `Diffuse`, `DiffuseColor`, `DiffuseSharp`, `Specular`, `Shininess`, `Metallic`, `SpecSharp`, `Reflection`, `IOR`, `Fresnel`, `Transparency`, `AbsorbDist`, `Translucency`, `Emission`, `EmissionContrast`, `EmissionColor`, `UseAlpha`, `Lens`, `BlendMode`, `Opacity`, `ColorSrc`, `OpacitySrc`, `BumpSrc`, `IORSrc`, `OpacityMod`, `BumpAmt`, `IORMod`, `LensWeight`, `AlphaBlendDiffuse`, `DiffFilterTrans`, `DiffGrad`, `SpecGrad`, `AbsorbGrad` |
| `SelectionSpots` | 1 | `0` |

The sample contains no `Material\1` section. This corrects the preliminary
handoff description.

## Observed multi-token values

Token counts use ASCII whitespace splitting. This describes shape only.

| Field | Occurrences | Token count |
| --- | ---: | ---: |
| `Holon\N.Transform` | 26 | 12 |
| `Holon\N.UPars` | 26 | 4 |
| `Holon\N.VPars` | 26 | 4 |
| `Holon\N.WPars` | 26 | 4 |
| `Gradients.0` | 1 | 551 |
| `SceneCamera.Position` | 1 | 3 |
| `SceneCamera.Angles` | 1 | 3 |
| `Light Sources.Ambient` | 1 | 3 |
| `Light Sources.Light\N` | 4 | 4 |
| `Light Sources.LightEx\N` | 4 | 5 |
| `Environment Background.EnvGrad` | 1 | 8 |
| `Environment Background.BackGrad` | 1 | 8 |
| `Material\0\Layer\0.DiffGrad` | 1 | 8 |
| `Material\0\Layer\0.SpecGrad` | 1 | 8 |
| `Material\0\Layer\0.AbsorbGrad` | 1 | 8 |
| `SelectionSpots.0` | 1 | 27 |

The report treats `PostMetas` as a metamorph-named field because that string is
present in the key. Its value is `0` in every holon. The file contains no
section or key named `Metamorph`, and this sample does not establish whether
`UPars`, `VPars`, or `WPars` encode metamorph data.

## Literal hierarchy report

- `Header.NumHolons` is `26`.
- Holon section suffixes and `ID` values both run from `0` through `25`.
- Every observed `GroupID` is `0`.
- `Holon\0` has `Type=0` and `Name=Group1`.
- `Holon\1` through `Holon\25` have `Type=2`; their names run from `Iter2`
  through `Iter26`.

The official current product page documents groups and iterators as holon
categories. Mapping `Type=0` to group and `Type=2` to iterator remains a
version-specific hypothesis until a controlled save test or version-matched
documentation confirms the numeric codes.

