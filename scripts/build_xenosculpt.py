"""Build the standalone Windows xenosculpt command."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys


def main() -> int:
    root = Path(__file__).parents[1]
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--name",
        "xenosculpt",
        "--paths",
        str(root / "src"),
        "--collect-data",
        "xenodream_xxp",
        "--add-data",
        f"{root / 'LICENSE'};.",
        "--exclude-module",
        "torch",
        "--exclude-module",
        "torchvision",
        "--exclude-module",
        "pandas",
        "--exclude-module",
        "pyarrow",
        "--exclude-module",
        "matplotlib",
        "--exclude-module",
        "sklearn",
        "--exclude-module",
        "numba",
        "--exclude-module",
        "pytest",
        "--exclude-module",
        "IPython",
        "--distpath",
        str(root / "dist"),
        "--workpath",
        str(root / "build" / "pyinstaller"),
        "--specpath",
        str(root / "build"),
        str(root / "scripts" / "xenosculpt_entry.py"),
    ]
    completed = subprocess.run(command, cwd=root, check=False)
    if completed.returncode:
        return completed.returncode
    executable = root / "dist" / "xenosculpt.exe"
    if not executable.is_file():
        print(f"build completed without expected executable: {executable}", file=sys.stderr)
        return 1
    print(executable)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
