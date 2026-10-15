# M3 generated cube acceptance

## Provenance

The compiler created `m3_generated_cube.xxp` on 2026-10-15 with profile
`xdx-1.220-cube-evidence-2026-10-15`. The user opened it in XenoDream X,
rendered it, and saved `m3_generated_cube_resaved.xxp`.

The supplied screenshot shows a rendered cube and a structure tree with
Group1 containing Cube2.

## Comparison

The generated and resaved files are both 3,377 bytes. They have the same
SHA-256:

```text
fcba6d61f2af4cf79c1e86a20b570a0bb0039db3fb79c9d73c84e842430fc7a0
```

They are byte-identical. XenoDream did not rewrite any section, value,
whitespace, line ending, or selection record during this open-and-save check.

## Outcome

Accepted by the reference application. The first generated M3 project opens,
has the expected Group1 and Cube2 structure, renders a cube, and survives a
XenoDream save without byte changes.

This result applies to the default cube project generated from the pinned XDX
1.220 profile. It does not yet establish acceptance for modified fields or
multi-object projects.
