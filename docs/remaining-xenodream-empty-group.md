# Add the evidenced empty XenoDream group

`project add-empty-group` reproduces one exact XenoDream X 1.220 transition:
the verified `Group1, Cube2` scene gains the empty, self-referencing `Group3`
record family observed in the retained native before-and-after pair.

```powershell
xenosculpt project add-empty-group .\sculpture.xsp `
  --message "add empty Group3"
```

The operation changes `Header.NumHolons` from 2 to 3 and inserts the exact
36-record `Holon\2` span. It preserves every other source byte, including
admitted prior edits to Cube2. A reverse audit removes the inserted records,
restores the count, and requires the original bytes exactly before a revision
can be committed.

This is not a general grouping feature. The command does not move an object
into Group3, accept a custom group name, create nested groups, add a second
empty group, reparent nodes, or establish parent-child semantics. Group3 is
reported as a literal native record with no writable operations.

The new revision requires native validation and never implies fabrication
suitability. Validate it with the managed profiles at an explicit physical
maximum:

```powershell
xenosculpt project validate .\sculpture.xsp --profile preview --stl-max-dimension-mm 120
xenosculpt project validate .\sculpture.xsp --profile review --stl-max-dimension-mm 120
```

The insertion is backed by evidence E050 and E051. Unsupported scene shapes
are rejected before the workspace records a revision or moves HEAD.
