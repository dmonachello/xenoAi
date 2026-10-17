# Deterministic natural-language planning

## Result

`project prompt` translates one controlled-English sentence into one existing
typed mutation operation. The planner does not write XDX records. The existing
mutation engine still validates the target, audits the structural diff, and
round-trips the native bytes.

The planner works offline and uses only the Python standard library. It does
not call a hosted or local language model.

## Apply a prompt

Use an exact object name and absolute values:

```powershell
xenosculpt project prompt sculpture.xsp `
  "set object Cube2 position to 25 0 0" `
  --message "move Cube2"
```

Apply a measured profile:

```powershell
xenosculpt project prompt sculpture.xsp `
  "apply Cylinder profile bevel-25-front to object Cylinder2" `
  --message "apply measured front bevel"
```

The command prints the versioned plan, the revision, and the structural
differences. The revision stores the original prompt, the grammar rule, the
planner identity, and the artifact hash used during planning.

## Supported forms

Version 1 accepts these forms:

```text
set object <name> scale to <x> <y> <z>
set object <name> rotation to <x> <y> <z>
set object <name> position to <x> <y> <z>
set object <name> color density to <value>
set object <name> face warp to <value>
place objects in a centered row with spacing <value>
place objects in a centered row with spacing <value> centered at <x> <y> <z>
evolve with seed <integer>
evolve with seed <integer> and strength <value>
apply Sphere profile <profile> to object <name>
apply Cylinder profile <profile> to object <name>
```

Keywords are case-insensitive. Object and profile names retain their case.
Numbers use base-10 notation without units or exponents.

## Rejected prompts

The planner rejects requests that need a guess. Examples include:

```text
make it prettier
move Cube2 a little left
add a small bevel
set object Cube2 scale to 25 50 100 and rotate it
```

One prompt can contain only one operation. Relative edits, qualitative
language, unsupported fields, arbitrary metamorph values, and multiple actions
remain outside the verified command vocabulary.

## Revision binding

Every plan records the current revision ID and artifact SHA-256. The workspace
rejects the plan if HEAD changes before application. The database transaction
checks HEAD again before it records a changed revision.

The workspace also reparses plans that claim the built-in controlled-English
identity. It rejects a plan when its prompt, grammar rule, and typed operation
do not agree. Other planner implementations must use their own explicit name
and version, which the revision preserves.

A planned no-op creates no revision. This matches the existing explicit
mutation behavior. The command still returns the interpreted plan.

## Validation level

Planning does not establish native acceptance, mesh validity, or fabrication
suitability. Run `project validate` after a planned mutation that requires
native evaluation. Fabrication suitability remains false until the repository
implements process-specific checks.

## Packaged verification

The rebuilt standalone executable has SHA-256
`2463c19ffc25d97831af167efe15342332f9ad821cb3a58455b3fd354823e476`.
It generated a default Cylinder, created a workspace, interpreted the measured
front-bevel prompt, and exported a 3,361-byte native project. The prompt output
and the explicit `project metamorph` output both have SHA-256
`7f7c48375ecaf621e22250887538c8a67af9040611b7cca853ae465b3db618e8`.
The retained evidence is
[`m19-packaged-prompt-smoke.json`](../evidence/runtime/m19-packaged-prompt-smoke.json).

The Python suite has 206 passing tests. It covers each supported grammar form,
rejected vague and multi-action prompts, stale plans, forged built-in
provenance, alternate planner identities, CLI behavior, and artifact
equivalence with explicit typed mutation.
