"""Command-line interface for `.xxp` inspection and preservation checks."""

from __future__ import annotations

import argparse
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
import sys
from typing import Sequence

from .diffing import diff_documents
from .document import parse_bytes
from .generator import (
    COMPILER_PROFILE,
    CubeSpec,
    GenerationError,
    Vector3,
    compile_cube,
)
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

    generate = commands.add_parser(
        "generate-cube", help="create a deterministic XDX 1.220 cube project"
    )
    generate.add_argument("output", type=Path)
    generate.add_argument(
        "--scale",
        nargs=3,
        type=Decimal,
        metavar=("X", "Y", "Z"),
        default=(Decimal("50"), Decimal("50"), Decimal("50")),
    )
    generate.add_argument(
        "--rotation",
        nargs=3,
        type=Decimal,
        metavar=("X", "Y", "Z"),
        default=(Decimal("0"), Decimal("0"), Decimal("0")),
    )
    generate.add_argument(
        "--position",
        nargs=3,
        type=Decimal,
        metavar=("X", "Y", "Z"),
        default=(Decimal("0"), Decimal("0"), Decimal("0")),
    )
    generate.add_argument("--color-density", type=Decimal, default=Decimal("1"))
    generate.add_argument("--face-warp", type=Decimal, default=Decimal("0"))
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

        if args.command == "generate-cube":
            if args.output.exists():
                print(
                    f"refusing to overwrite: {args.output} already exists",
                    file=sys.stderr,
                )
                return 2
            output = compile_cube(
                CubeSpec(
                    scale=Vector3(*args.scale),
                    rotation=Vector3(*args.rotation),
                    position=Vector3(*args.position),
                    color_density=args.color_density,
                    face_warp=args.face_warp,
                )
            )
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_bytes(output)
            _print_json(
                {
                    "output": str(args.output),
                    "bytes": len(output),
                    "sha256": sha256(output).hexdigest(),
                    "compiler_profile": COMPILER_PROFILE,
                }
            )
            return 0

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
    except (OSError, GenerationError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
