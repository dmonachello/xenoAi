"""Redacted command line for ChatGPT-plan account management."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import sys
from typing import Sequence

from .auth import AuthError, ChatGPTPlanAuth
from .oidc import OidcError
from .responses import OpenAITransportError
from .storage import AuthStorageError


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="xenosculpt auth",
        description="Use an eligible ChatGPT plan for XenoSculpt model requests.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    login = commands.add_parser("login", help="continue with ChatGPT in your browser")
    login_group = login.add_mutually_exclusive_group()
    login_group.add_argument("--new", action="store_true", help="register another account")
    login_group.add_argument("--account", help="reauthorize a saved account")
    login.add_argument("--timeout-seconds", type=float, default=180)
    commands.add_parser("status", help="show redacted saved account state")
    commands.add_parser("models", help="list models available to the active account")
    use = commands.add_parser("use", help="select the active saved account")
    use.add_argument("account")
    logout = commands.add_parser("logout", help="revoke and clear a saved session")
    logout.add_argument("--account")
    return parser


def _print(value: object) -> None:
    print(json.dumps(value, indent=2))


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    auth = ChatGPTPlanAuth()
    try:
        if args.command == "login":
            print("Continue with ChatGPT in your browser...", file=sys.stderr)
            _print(
                {
                    "schema": "xenosculpt-chatgpt-account/v1",
                    "account": asdict(
                        auth.login(
                            args.account,
                            new=args.new,
                            timeout_seconds=args.timeout_seconds,
                        )
                    ),
                }
            )
            return 0
        if args.command == "status":
            accounts = auth.accounts()
            _print(
                {
                    "schema": "xenosculpt-chatgpt-accounts/v1",
                    "accounts": [asdict(item) for item in accounts],
                }
            )
            return 0
        if args.command == "models":
            _print(
                {
                    "schema": "xenosculpt-chatgpt-models/v1",
                    "models": list(auth.models()),
                }
            )
            return 0
        if args.command == "use":
            _print({"schema": "xenosculpt-chatgpt-account/v1", "account": asdict(auth.select(args.account))})
            return 0
        if args.command == "logout":
            _print({"schema": "xenosculpt-chatgpt-logout/v1", **asdict(auth.logout(args.account))})
            return 0
        raise ValueError(f"unsupported auth command: {args.command}")
    except (AuthError, AuthStorageError, OidcError, OpenAITransportError, OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2
