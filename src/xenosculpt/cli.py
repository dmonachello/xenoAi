"""Top-level application dispatcher."""

from __future__ import annotations

import sys
from typing import Sequence

from xenodream_xxp.cli import main as xenodream_main

from .comfyui.cli import main as comfyui_main


_HELP = """usage: xenosculpt [-h] {comfyui,XenoDream-command} ...

Revision and execution tools for creative applications.

applications:
  comfyui             revise and run ComfyUI API workflows
  XenoDream-command   any existing XenoDream command (inspect, project, etc.)

Run `xenosculpt comfyui --help` for ComfyUI commands.
Run `xxp --help` or `xenosculpt project --help` for XenoDream commands.
"""


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not arguments or arguments in (["-h"], ["--help"]):
        print(_HELP)
        return 0
    if arguments and arguments[0] == "comfyui":
        return comfyui_main(arguments[1:])
    return xenodream_main(arguments)


if __name__ == "__main__":
    raise SystemExit(main())
