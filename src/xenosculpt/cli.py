"""Top-level application dispatcher."""

from __future__ import annotations

import sys
from typing import Sequence

from xenodream_xxp.cli import main as xenodream_main
from xenosculpt_openai.cli import main as auth_main

from .comfyui.cli import main as comfyui_main
from .moi.cli import main as moi_main


_HELP = """usage: xenosculpt [-h] {auth,comfyui,moi,create,XenoDream-command} ...

Revision and execution tools for creative applications.

applications:
  auth                connect an eligible ChatGPT plan
  comfyui             revise and run ComfyUI API workflows
  moi                  create verified native MoI CAD projects
  create              create a verified XenoDream project from natural language
  XenoDream-command   any XenoDream command (create, inspect, project, etc.)

Run `xenosculpt comfyui --help` for ComfyUI commands.
Run `xenosculpt auth --help` for ChatGPT account commands.
Run `xenosculpt moi --help` for MoI commands.
Run `xenosculpt create --help` for hosted natural-language creation.
Run `xxp --help` or `xenosculpt project --help` for other XenoDream commands.
"""


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not arguments or arguments in (["-h"], ["--help"]):
        print(_HELP)
        return 0
    if arguments and arguments[0] == "comfyui":
        return comfyui_main(arguments[1:])
    if arguments and arguments[0] == "moi":
        return moi_main(arguments[1:])
    if arguments and arguments[0] == "auth":
        return auth_main(arguments[1:])
    return xenodream_main(arguments)


if __name__ == "__main__":
    raise SystemExit(main())
