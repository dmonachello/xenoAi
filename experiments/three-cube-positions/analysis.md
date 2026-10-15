# Three positioned cube siblings

## Controlled result

The XDX 1.220 project contains Group1 and three Cube constructor holons. The
application tree and rendered preview are visible in the user-supplied
screenshot from 2026-10-15.

```text
bytes: 4826
sha256: caff33da71c7a24e6a79a7c4448a17daeefdc3c1915d3bc7d85ab167fe05654d
line endings: 272 CRLF records; no bare CR or LF
```

`Header.NumHolons=4`. The observed children are:

| Section | ID | GroupID | Type | Name | Position |
| --- | ---: | ---: | ---: | --- | --- |
| `Holon\1` | 1 | 0 | 1 | Cube2 | -75, 0, 0 |
| `Holon\2` | 2 | 0 | 1 | Cube3 | 0, 0, 0 |
| `Holon\3` | 3 | 0 | 1 | Cube4 | 75, 0, 0 |

Each cube holon is followed immediately by its own `MM\0` block with
`Style=5`. After normalizing the section path, ID, name, and X position, the
three cube-plus-metamorph blocks are byte-identical. The group block and all
bytes from `[Gradients]` to end of file are unchanged from the one-cube
baseline.

## Scope

This sample verifies the persisted shape of this one three-sibling project.
It does not establish arbitrary cube counts, custom IDs or names, nested
groups, or the meaning of `SelectionSpots`. Generated three-cube output still
requires a separate XenoDream open, render, and resave check.
