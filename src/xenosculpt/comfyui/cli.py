"""Command-line surface for ComfyUI API-workflow projects."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
from typing import Sequence

from xenosculpt.core import WorkspaceError

from .client import ComfyClient, ComfyClientError
from .workflow import LiteralInput, NodeLink, WorkflowFormatError, parse_json_value
from .workspace import ComfyProject, RunState


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="xenosculpt comfyui")
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="create a project from API-format JSON")
    init.add_argument("workspace", type=Path)
    init.add_argument("source", type=Path)
    for name in ("status", "log"):
        command = commands.add_parser(name)
        command.add_argument("workspace", type=Path)
    edit = commands.add_parser("set-input", help="change one existing node input")
    edit.add_argument("workspace", type=Path)
    edit.add_argument("node_id")
    edit.add_argument("input_name")
    choice = edit.add_mutually_exclusive_group(required=True)
    choice.add_argument("--value-json")
    choice.add_argument("--link-node")
    edit.add_argument("--link-output", type=int)
    edit.add_argument("--message", default="Set ComfyUI node input")
    compare = commands.add_parser("compare")
    compare.add_argument("workspace", type=Path)
    compare.add_argument("before")
    compare.add_argument("after")
    export = commands.add_parser("export")
    export.add_argument("workspace", type=Path)
    export.add_argument("output", type=Path)
    export.add_argument("--ref", default="HEAD")
    branch = commands.add_parser("branch")
    branch.add_argument("workspace", type=Path)
    branch.add_argument("name")
    branch.add_argument("--from-ref", default="HEAD")
    branch.add_argument("--checkout", action="store_true")
    checkout = commands.add_parser("checkout")
    checkout.add_argument("workspace", type=Path)
    checkout.add_argument("ref")
    run = commands.add_parser("run")
    run.add_argument("workspace", type=Path)
    _server_arguments(run)
    resume = commands.add_parser("resume")
    resume.add_argument("workspace", type=Path)
    resume.add_argument("run_id")
    _server_arguments(resume)
    run_status = commands.add_parser("run-status")
    run_status.add_argument("workspace", type=Path)
    run_status.add_argument("run_id")
    return parser


def _server_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--server", default="http://127.0.0.1:8188")
    parser.add_argument("--timeout-seconds", type=float, default=600)
    parser.add_argument("--poll-seconds", type=float, default=1)
    parser.add_argument("--allow-remote", action="store_true")
    parser.add_argument("--allow-version-mismatch", action="store_true")


def _print(value: object) -> None:
    print(json.dumps(value, indent=2, sort_keys=True, default=str))


def _run_dict(run) -> dict[str, object]:
    value = asdict(run)
    value["state"] = run.state.value
    return value


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "init":
            project = ComfyProject.create(args.workspace, args.source)
            status = project.status()
            _print(asdict(status))
            return 0
        project = ComfyProject.open(args.workspace)
        if args.command == "status":
            _print(asdict(project.status()))
            return 0
        if args.command == "log":
            _print([asdict(item) for item in project.history()])
            return 0
        if args.command == "set-input":
            if args.value_json is not None:
                if args.link_output is not None:
                    raise ValueError("--link-output may only be used with --link-node")
                value = LiteralInput(parse_json_value(args.value_json))
            else:
                if args.link_output is None:
                    raise ValueError("--link-output is required with --link-node")
                value = NodeLink(args.link_node, args.link_output)
            result = project.set_input(args.node_id, args.input_name, value, message=args.message)
            _print({"created": result.created, "revision": asdict(result.revision), "mutation": asdict(result.mutation) if result.mutation else None})
            return 0
        if args.command == "compare":
            differences = project.compare(args.before, args.after)
            _print({"differences": differences})
            return 1 if differences else 0
        if args.command == "export":
            _print(asdict(project.export(args.output, args.ref)))
            return 0
        if args.command == "branch":
            _print(asdict(project.create_branch(args.name, from_ref=args.from_ref, checkout=args.checkout)))
            return 0
        if args.command == "checkout":
            _print(asdict(project.checkout(args.ref)))
            return 0
        if args.command == "run-status":
            run = project.get_run(args.run_id)
        else:
            client = ComfyClient(args.server, allow_remote=args.allow_remote)
            if args.command == "run":
                run = project.run(
                    client,
                    timeout_seconds=args.timeout_seconds,
                    poll_seconds=args.poll_seconds,
                    allow_version_mismatch=args.allow_version_mismatch,
                )
            elif args.command == "resume":
                run = project.resume(
                    args.run_id,
                    client,
                    timeout_seconds=args.timeout_seconds,
                    poll_seconds=args.poll_seconds,
                )
            else:
                raise ValueError(f"unsupported ComfyUI command: {args.command}")
        _print(_run_dict(run))
        return 0 if run.state is RunState.SUCCEEDED else 1
    except (OSError, ValueError, WorkspaceError, WorkflowFormatError, ComfyClientError) as error:
        print(str(error), file=sys.stderr)
        return 2
