# M28–M29: discoverable additions and atomic controlled recipes

`project additions` reports only structural additions admitted by the exact
revision bytes. It calls the same admission rules as `add-cube` and
`add-sphere`; it does not infer support from object names.

```powershell
xenosculpt project additions .\sculpture.xsp
```

The controlled planner also accepts exact addition rules:

```text
add Cube at 75 0 0
add Sphere at 55 0 0
```

Two through five rules can be separated with semicolons. Every clause must be
a complete existing controlled-English operation with explicit object names
and absolute values. Pronouns, relative edits, conditions, loops, empty steps,
and unrestricted natural language are rejected.

Use `--dry-run` to parse and evaluate a recipe against the current revision
without changing the workspace:

```powershell
xenosculpt project prompt .\sculpture.xsp `
  "add Sphere at 55 0 0; apply Sphere profile cushion-core to object Sphere3" `
  --message "add and shape sphere" `
  --dry-run
```

Omit `--dry-run` to apply the same recipe. All steps run against transient
bytes. The workspace publishes one final artifact and one revision only after
every step passes its native byte audit. A failed later step cannot expose an
earlier structural edit. Plans remain bound to the exact HEAD revision and
artifact hash, so a stale plan is rejected.

Dry-run is a preview, not an authorization token. A later invocation creates a
fresh plan bound to the then-current HEAD. Native validation remains an
explicit separate command, and recipe results remain fabrication-unsuitable.
