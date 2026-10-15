# Clean two-cube project

## Controlled result

The XDX 1.220 project was created from the one-cube baseline by adding one
cube without deleting any holons. Group1 remained at Position 0, 0, 0. The
cubes were placed at X positions -50 and 50.

```text
bytes: 4103
sha256: 7b0f0b57d82feb0200b320befb179143804b0d75aca85908b809d9d684ac1e2a
line endings: 233 CRLF records; no bare CR or LF
```

`Header.NumHolons=3`. Cube2 uses section `Holon\1`, ID 1, GroupID 0, Type 1,
and position -50, 0, 0. Cube3 uses section `Holon\2`, ID 2, GroupID 0, Type 1,
and position 50, 0, 0. Each cube is followed by its own `MM\0` block with
`Style=5`.

The Group1 block and all bytes from `[Gradients]` to end of file match the
one-cube and three-cube references. This clean creation result differs from
the deletion experiment, where surviving Cube4 retained ID 3 and its name
after moving to section `Holon\2`.

## Scope

Together, the controlled files establish the flat Group1 plus cube-sibling
shape for one, two, and three cubes. They do not establish zero cubes, four or
more cubes, nested groups, mixed constructor types, or custom identities.
