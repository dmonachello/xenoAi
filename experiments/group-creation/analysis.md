# Empty group creation experiment 015

## Provenance

The user supplied `cube_two_groups.xxp` in `output/` on 2026-10-15 after
starting from `cube_base.xxp` and adding one empty group. Both files were
copied here without modification. `SHA256SUMS` records their hashes.

The supplied screenshot shows `Group1` with `Cube2` beneath it and a separate
empty `Group3`. `Group3` is selected, and the Active Holon name is `Group3`.

## Static comparison

`Header.NumHolons` changed from 2 to 3. The variant adds one section,
`Holon\2`, with 34 fields. Key identifying values are:

```text
ID=2
GroupID=2
Type=0
Name=Group3
```

The existing `Holon\0` Group1 and `Holon\1` Cube2 records did not change.
Cube2 retains `GroupID=0`. No selection, camera, material, or other persisted
value changed.

The baseline is 3,377 bytes. The variant is 3,982 bytes. Both use CRLF line
endings and round-trip byte for byte through the parser.

## Experiment outcome

Verified for this XenoDream X 1.220 sample. Adding an empty group increments
`Header.NumHolons` and appends a holon record. The new group has `Type=0` and
uses its own numeric ID as `GroupID` in this sample.

The unchanged Cube2 record has `GroupID=0` and appears beneath Group1, whose
`ID` is 0. This supports a group-membership relationship between child
`GroupID` and group `ID` in the tested structure. More samples are required
before treating that as a universal hierarchy rule.
