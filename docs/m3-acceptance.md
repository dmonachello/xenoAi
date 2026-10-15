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

Application status: accepted for the default generated cube. The elongated
result is recorded below. Multi-object generation remains untested.

## Elongated cube result

Accepted on 2026-10-15. The generator changed Cube2 Scale from `50, 50, 50`
to `25, 50, 100`. XenoDream displayed those values and rendered the elongated
geometry shown in the user's screenshot.

The resaved file is byte-identical to the generated file. Both are 3,378 bytes
and have SHA-256
`a8b5b9d5963f5f1ef424d224871e00dd8c8391059e9117ca4579d3035159024d`.

Application status: accepted for the default and elongated generated cubes.

## Three-cube static result

The `xdx-1.220-three-cube-evidence-2026-10-15` profile reproduces the
controlled three-cube reference byte for byte:

```text
bytes: 4826
sha256: caff33da71c7a24e6a79a7c4448a17daeefdc3c1915d3bc7d85ab167fe05654d
```

The output has Group1 with Cube2, Cube3, and Cube4 at X positions -75, 0, and
75. Static tests verify exact section order, identities, group links,
per-sibling field isolation, deterministic output, and lossless parser round
trip.

## Three-cube application result

Accepted on 2026-10-15. XenoDream opened the generated project and showed
Group1 containing Cube2, Cube3, and Cube4. The scene view showed three
positioned cube bounds, and the preview rendered three objects.

The resaved file is byte-identical to the generated file. Both are 4,826 bytes
and have SHA-256
`caff33da71c7a24e6a79a7c4448a17daeefdc3c1915d3bc7d85ab167fe05654d`.
XenoDream performed no observable file normalization.

Application status: accepted for the observed Group1 plus three cube sibling
profile. Other object counts and group shapes remain untested.

## Two-cube static result

The `xdx-1.220-two-cube-evidence-2026-10-15` profile reproduces the clean
two-cube reference byte for byte:

```text
bytes: 4103
sha256: 7b0f0b57d82feb0200b320befb179143804b0d75aca85908b809d9d684ac1e2a
```

The output has Group1 with Cube2 and Cube3 at X positions -50 and 50. Static
tests verify the exact reference bytes, identities, group links, per-cube
field isolation, deterministic output, and parser round trip.

## Two-cube application result

Accepted on 2026-10-15. XenoDream opened the generated project and showed
Group1 containing Cube2 and Cube3. With Cube2 selected, its controls displayed
Scale 50, 50, 50 and Position -50, 0, 0. The preview rendered two objects.

The resaved file is byte-identical to the generated file. Both are 4,103 bytes
and have SHA-256
`7b0f0b57d82feb0200b320befb179143804b0d75aca85908b809d9d684ac1e2a`.
XenoDream performed no observable file normalization.

Application status: generated counts one, two, and three are accepted for the
flat Group1 cube-sibling profiles. Counts zero and four or greater remain
unsupported.
