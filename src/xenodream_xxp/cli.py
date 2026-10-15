"""Command-line interface for `.xxp` inspection and preservation checks."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
from typing import Sequence

from .diffing import diff_documents
from .document import parse_bytes
from .report import inspect_document


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="xxp")
    commands = parser.add_subparsers(dest="command", required=True)

    inspect_command = commands.add_parser("inspect", help="print a JSON structure report")
    inspect_command.add_argument("input", type=Path)

    roundtrip = commands.add_parser(
        "roundtrip", help="parse and write an unchanged byte-identical copy"
    )
    roundtrip.add_argument("input", type=Path)
    roundtrip.add_argument("output", type=Path)

    diff = commands.add_parser("diff", help="compare keys and value tokens")
    diff.add_argument("before", type=Path)
    diff.add_argument("after", type=Path)
    return parser


def _print_json(value: object) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "inspect":
            document = parse_bytes(args.input.read_bytes())
            _print_json(inspect_document(document))
            return 0

        if args.command == "roundtrip":
            if args.output.exists():
                print(f"refusing to overwrite: {args.output} already exists", file=sys.stderr)
                return 2
            source = args.input.read_bytes()
            output = parse_bytes(source).to_bytes()
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_bytes(output)
            _print_json(
                {
                    "input": str(args.input),
                    "output": str(args.output),
                    "bytes": len(output),
                    "sha256": sha256(output).hexdigest(),
                    "byte_identical": source == output,
                }
            )
            return 0 if source == output else 1

        before = parse_bytes(args.before.read_bytes())
        after = parse_bytes(args.after.read_bytes())
        differences = diff_documents(before, after)
        _print_json(
            {
                "before": str(args.before),
                "after": str(args.after),
                "byte_identical": before.to_bytes() == after.to_bytes(),
                "differences": differences,
            }
        )
        return 1 if differences else 0
    except OSError as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

