# M0 and M1 workflow

## Definition of done

M0 is complete when the repository layout exists, the original sample has a
verified SHA-256 provenance record, official sources are distinguished from
sample observations, and format claims have evidence and confidence labels.

M1 is complete when all of these predicates hold:

- Parsing the supplied sample returns every physical record in source order.
- Serializing the unchanged document yields the exact original byte sequence.
- The report covers every observed section and key, including long values,
  holon identifiers and type codes, transform fields, cameras, materials, and
  fields whose names suggest metamorph data without assigning undocumented
  meanings.
- Tests cover CRLF, LF, a final line without a terminator, long values,
  repeated keys, unknown sections and keys, empty values, and malformed lines.
- The `inspect`, `roundtrip`, and `diff` CLI paths execute against real files.

Passing these checks proves syntactic preservation only. XenoDream X remains
the reference implementation for application validity.

## Scope and rigor

This iteration covers one 19,797-byte XenoDream X 1.007 sample, a standard
library Python package, a CLI, tests, and documentation. The sample cannot
establish meanings for numeric positions, enum values, compatibility with
other program versions, or whether edited output opens in XenoDream.

Rigor is high for preservation and low for semantic interpretation. Every
input byte is retained. Semantic reports use literal field names and token
counts, not inferred geometry meanings.

## Work sequence

1. Preserve and hash the original sample.
2. Record observed syntax and source-backed domain facts.
3. Add tests that fail because the parser and CLI do not exist.
4. Implement the smallest ordered-record parser and unchanged serializer.
5. Verify byte identity and CLI behavior on the real sample.
6. Audit the evidence log and request controlled one-setting experiments.

The data model owns raw bytes and parsed record boundaries in one module. A
key/value record exposes its raw key and value byte slices without normalizing
either. Reports may interpret copies of those values but never mutate the
lossless representation.

## Alternatives rejected

- `configparser` loses duplicate keys, comments, whitespace, ordering details,
  and exact line endings. Its smaller implementation would expose format loss
  to every caller.
- A typed geometry model would encode guesses before controlled diffs establish
  field meanings. It belongs after the lossless boundary is stable.
- A byte blob plus regular expressions can round-trip but gives callers no safe
  record structure for reports or later targeted edits.

