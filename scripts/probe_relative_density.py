"""Create a controlled XDX Relative Density probe without normalizing other bytes."""

from __future__ import annotations

import argparse
from dataclasses import replace
from decimal import Decimal, DecimalException
from hashlib import sha256
import json
from pathlib import Path

from xenodream_xxp.document import Document, KeyValueRecord, parse_bytes


def _format_density(value: Decimal) -> bytes:
    if not value.is_finite():
        raise ValueError("density must be finite")
    try:
        formatted = value.quantize(Decimal("0.0001"))
    except DecimalException as error:
        raise ValueError("density cannot be represented") from error
    if formatted != value:
        raise ValueError("density exceeds the observed four-place encoding")
    return format(formatted, ".4f").encode("ascii") + b" "


def set_relative_density(data: bytes, object_name: str, value: Decimal) -> bytes:
    document = parse_bytes(data)
    name_sections = {
        record.section
        for record in document.records
        if isinstance(record, KeyValueRecord)
        and record.key == b"Name"
        and record.value.decode("ascii", "strict") == object_name
    }
    if len(name_sections) != 1:
        raise ValueError(
            f"object name {object_name!r} matched {len(name_sections)} sections"
        )
    section = name_sections.pop()
    matches = [
        (index, record)
        for index, record in enumerate(document.records)
        if isinstance(record, KeyValueRecord)
        and record.section == section
        and record.key == b"Density"
    ]
    if len(matches) != 1:
        raise ValueError(f"expected one Density field in {section!r}")
    index, record = matches[0]
    replacement = _format_density(value)
    separator = record.content.find(b"=")
    records = list(document.records)
    records[index] = replace(
        record,
        content=record.content[: separator + 1] + replacement,
        value=replacement,
    )
    output = Document(tuple(records)).to_bytes()
    if parse_bytes(output).to_bytes() != output:
        raise ValueError("probe output failed exact parser round trip")
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--object", required=True)
    parser.add_argument("--density", required=True, type=Decimal)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"refusing to overwrite {args.output}")
    source = args.input.read_bytes()
    output = set_relative_density(source, args.object, args.density)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(output)
    print(
        json.dumps(
            {
                "input_sha256": sha256(source).hexdigest(),
                "output": str(args.output),
                "output_sha256": sha256(output).hexdigest(),
                "object": args.object,
                "density": str(args.density),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
