# Metamorph descriptor recovery design

Date: 2026-10-16

## Problem

XenoDream's active-metamorph controls are populated from operation metadata in
the executable. The current registry knows displayed Sphere and Cube labels,
but it deliberately does not equate panel order with persisted `Pars` order.
We need a repeatable extractor that recovers that relationship without making
the generator trust unreviewed binary output.

## Usage

```powershell
python scripts/recover_metamorph_descriptors.py `
  "C:\Program Files (x86)\XenoDream Software\XenoDreamX\XenoDreamX.exe"
```

The command prints deterministic JSON for the pinned XenoDream X 1.220
executable. It never edits the executable or the runtime registry.

## Shape

The recovery script owns PE address translation and the two observed Delphi
attribute payload formats. `OperationProfile` supplies only the operation Style,
name, expected descriptor count, and the bounded class-metadata range. The
extractor returns immutable `NumericDescriptor` and `ChoiceDescriptor` values.

The checked-in runtime registry remains a separately reviewed artifact. Binary
recovery can propose facts, but it cannot authorize generator writes. Promotion
requires a matching executable hash, successful extraction, agreement with
existing experiments, and explicit evidence-log entries.

This keeps the interface narrow. Callers provide one executable path and receive
one JSON document. PE layout, marker scanning, payload decoding, ordering, and
validation remain inside the script.

## Synthesis decision

The chosen design uses a bounded static extractor rather than a general Delphi
RTTI library. The evidence currently establishes two descriptor attribute
classes and two operation ranges. A general RTTI model would expose many
unverified layouts and make failures harder to audit. The extractor fails closed
on executable hash, range, payload, duplicate slot, and count mismatches.

## Tradeoffs accepted

- We accept an executable-specific profile in exchange for deterministic,
  reviewable evidence.
- We accept a separate promotion step in exchange for keeping recovered guesses
  out of generator write permissions.
- We preserve undecoded descriptor tails in hexadecimal instead of assigning
  meanings before their consumers are traced.

## Alternatives considered

Executing XenoDream's RTTI helper functions would reuse native parsing, but it
would require process injection or an in-process harness. That is unnecessary
for immutable metadata and adds runtime risk.

A general scanner over the whole executable would find many descriptor-looking
records, but it would lose reliable ownership by Style. Bounded class ranges
make provenance explicit.

## Open questions and risks

- Which fields in the undecoded numeric and choice tails control display width,
  randomization, and UI behavior?
- Do all 246 operation classes use the same two descriptor attribute layouts?
- Which constructors generate closed geometry under their default settings?

## Implemented checkpoint

The hash-pinned extractor, focused parser tests, reviewed runtime-registry
promotion, and read-only inspection projection are implemented. Cube slot zero
matches the verified Face Warp experiment, while all remaining Sphere and Cube
slots now have explicit binary indexes and descriptor domains. See
`docs/rea-metamorph-descriptors.md` for the reconciliation result and next
investigation boundary.
