# Deleting the middle cube

## Procedure

The user confirmed that `two_cubes.xxp` came from the accepted three-cube
scene after deleting one cube. The deleted object was Cube3, the middle cube.

```text
bytes: 4103
sha256: 010462dd1d78043c37ac5f306bd1ce16d167ca35b72b98b09228949023ca7809
```

## Observed result

`Header.NumHolons` changed from 4 to 3. Cube3 and its metamorph block are
absent. The surviving Cube4 moved from section path `Holon\3` to `Holon\2`,
and its metamorph moved from `Holon\3\MM\0` to `Holon\2\MM\0`.

The surviving object retained `ID=3`, `Name=Cube4`, `GroupID=0`, `Type=1`, and
position 75, 0, 0. This separates serialized section position from persisted
holon identity. `SelectionSpots.0` remained `3 1 1` even though no `Holon\3`
section remained, so the field must stay opaque.

Group1 Position changed from 0, 0, 0 to 4, 1, 0. The deletion procedure does
not establish that this was caused by deletion, so it is recorded as an
incidental change rather than deletion semantics.

## Scope

This experiment records deletion from the specific three-cube scene. It does
not provide a clean two-cube creation template and does not establish a
general ID allocation or reuse rule.
