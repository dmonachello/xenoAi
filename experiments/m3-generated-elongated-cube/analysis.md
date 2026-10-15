# M3 generated elongated cube acceptance

## Provenance

The compiler created `m3_generated_elongated_cube.xxp` on 2026-10-15 with
Cube2 Scale `25, 50, 100`. The user opened it in XenoDream X, rendered it, and
saved `m3_generated_elongated_cube_resaved.xxp`.

The supplied screenshot shows Cube2 selected, Scale values `25, 50, 100`, and
the elongated rendered geometry.

## Comparison

The generated and resaved files are both 3,378 bytes and have SHA-256:

```text
a8b5b9d5963f5f1ef424d224871e00dd8c8391059e9117ca4579d3035159024d
```

They are byte-identical. Relative to the accepted default cube, the elongated
file changes only `Holon\1.Transform` token 0 from 50 to 25 and token 2 from
50 to 100.

## Outcome

Accepted by the reference application. The generated scale values appear in
the Cube2 controls, produce the expected elongated geometry, and survive a
XenoDream save without byte changes.
