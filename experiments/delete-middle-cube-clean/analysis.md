# Clean middle-Cube deletion

## Procedure

XenoDream X 1.220 opened the accepted three-Cube project
`experiments/three-cube-positions/3_cube_positions.xxp`. The user selected
`Cube3` in the native object tree, deleted only that object, did not click the
viewport, and saved the result as `middle_deleted.xxp`.

```text
source bytes: 4826
source sha256: caff33da71c7a24e6a79a7c4448a17daeefdc3c1915d3bc7d85ab167fe05654d
target bytes: 4103
target sha256: bb980364c5281d29a24c5b72accb74d907c33fc664e660731d697aaa56555d3a
```

## Native transition

The clean save changes only the structural deletion:

- `Header.NumHolons` changes from 4 to 3.
- The complete `Holon\2` and `Holon\2\MM\0` Cube3 span is removed.
- The surviving Cube4 sections move from `Holon\3` and `Holon\3\MM\0` to
  section index 2.
- Cube4 retains persistent `ID=3`, `Name=Cube4`, `GroupID=0`, its transform,
  and every other field byte.
- Group1 and SelectionSpots remain byte-identical.

An independent record rewrite that removes Cube3, reindexes Cube4, and changes
the count produces the native target byte-for-byte. Reversing those steps
reproduces the source byte-for-byte.

## Runtime gate

The native transition closes the earlier unexplained Group1 movement in E058,
but it does not authorize a product writer. The exact native target remained
actively computing for the full 180-second preview limit. A second candidate
with the surviving cubes moved to the previously accepted -50 and +50 spacing
also timed out actively at 10 percent. The same candidate timed out actively
after 300 seconds at 1 percent density.

All three managed runs preserved the source and disposable hashes and
confirmed cleanup. None produced an STL. The known-good contiguous two-Cube
family differs materially in the survivor identity: it uses `ID=2` and
`Name=Cube3`, while native deletion preserves `ID=3` and `Name=Cube4`.
Identity is correlated with the runtime behavior, but the cause is not proven.

## Decision

Do not expose `remove-middle-cube`. Renumbering the survivor would contradict
the native deletion and could break unknown references. The exact transition
and negative runtime evidence remain available for the next identity and
reference investigation.
