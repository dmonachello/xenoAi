# M3 generated cube acceptance

## Static result

The compiler generated `output/m3_generated_cube.xxp` on 2026-10-15 with
profile `xdx-1.220-cube-evidence-2026-10-15`.

```text
bytes: 3377
sha256: fcba6d61f2af4cf79c1e86a20b570a0bb0039db3fb79c9d73c84e842430fc7a0
```

The output is byte-identical to the controlled `cube_base.xxp`. Structural
diff reports no differences, and the parser serializes it without changing a
byte.

This proves deterministic construction and static equivalence to the verified
template. It does not prove XenoDream accepts the generated path.

## XenoDream check

Open `output/m3_generated_cube.xxp` in XenoDream X and record:

- whether the project opens without an error;
- whether the tree shows Group1 containing Cube2;
- whether Cube2 displays Scale 50, 50, 50 and Rotation and Position 0, 0, 0;
- whether the cube renders;
- whether saving a reopened copy changes any bytes.

## Application result

Accepted on 2026-10-15. The user opened the generated project in XenoDream X.
The structure tree showed Group1 containing Cube2, and the preview rendered a
cube. The user then saved `m3_generated_cube_resaved.xxp`.

The resaved file is byte-identical to the generated file. Both are 3,377 bytes
and have SHA-256
`fcba6d61f2af4cf79c1e86a20b570a0bb0039db3fb79c9d73c84e842430fc7a0`.
XenoDream performed no observable file normalization in this check.

Application status: accepted for the default generated cube. Modified and
multi-object generated projects remain untested in XenoDream.
