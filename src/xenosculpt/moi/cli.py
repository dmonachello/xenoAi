"""CLI for the bounded MoI native cylinder integration."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import sys
from typing import Sequence

from xenosculpt.core import WorkspaceError

from .model import CylinderSpec
from .workspace import MoiProject


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="xenosculpt moi")
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create-cylinder")
    create.add_argument("workspace", type=Path)
    create.add_argument("--radius-mm", required=True)
    create.add_argument("--height-mm", required=True)
    create.add_argument("--moi-executable", type=Path, default=Path(r"C:\Program Files\MoI 4.0\MoI.exe"))
    create.add_argument("--timeout-seconds", type=float, default=120)
    status = commands.add_parser("status")
    status.add_argument("workspace", type=Path)
    export = commands.add_parser("export")
    export.add_argument("workspace", type=Path)
    export.add_argument("output", type=Path)
    export_stl = commands.add_parser("export-stl")
    export_stl.add_argument("workspace", type=Path)
    export_stl.add_argument("output", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "create-cylinder":
            spec = CylinderSpec(Decimal(args.radius_mm), Decimal(args.height_mm))
            project = MoiProject.create_cylinder(args.workspace, spec, moi_executable=args.moi_executable,
                                                 timeout_seconds=args.timeout_seconds)
            value = asdict(project.status())
        else:
            project = MoiProject.open(args.workspace)
            if args.command == "status":
                value = asdict(project.status())
            elif args.command == "export":
                value = asdict(project.export(args.output))
            elif args.command == "export-stl":
                value = asdict(project.export_stl(args.output))
            else:
                raise ValueError(f"unsupported MoI command: {args.command}")
        print(json.dumps(value, indent=2, sort_keys=True, default=str))
        return 0
    except (OSError, ValueError, InvalidOperation, WorkspaceError) as error:
        print(str(error), file=sys.stderr)
        return 2
