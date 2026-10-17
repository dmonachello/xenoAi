"""Prove the installed MoI 4 native cylinder/save/reopen/STL path.

This is a disposable capability probe. It writes only beneath the requested
output directory and never opens a user document.
"""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import tempfile
import time

from xenosculpt.mesh import basic_mesh_valid, inspect_binary_stl


def _js_string(path: Path) -> str:
    return str(path.resolve()).replace("\\", "\\\\").replace('"', '\\"')


def _run(executable: Path, script: Path, ini: Path, timeout: float) -> dict[str, object]:
    started = time.monotonic()
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = subprocess.SW_HIDE
    process = subprocess.Popen(
        [str(executable), str(script), str(ini)],
        cwd=script.parent,
        startupinfo=startup,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
    )
    try:
        return_code = process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            capture_output=True,
            check=False,
        )
        raise RuntimeError(f"MoI timed out after {timeout:g} seconds") from None
    return {
        "pid": process.pid,
        "return_code": return_code,
        "duration_seconds": round(time.monotonic() - started, 3),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--moi-executable",
        type=Path,
        default=Path(r"C:\Program Files\MoI 4.0\MoI.exe"),
    )
    parser.add_argument("--timeout-seconds", type=float, default=120)
    args = parser.parse_args()

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    native = output / "model.3dm"
    stl = output / "validation.stl"
    create_script = output / "create.js"
    reopen_script = output / "reopen.js"
    create_ini = output / "create.ini"
    reopen_ini = output / "reopen.ini"

    create_script.write_text(
        "\n".join(
            (
                "var factory = moi.command.createFactory('cylinder');",
                "factory.setInput(1, moi.vectorMath.createTopFrame());",
                "factory.setInput(3, 15.0);",
                "factory.setInput(4, moi.vectorMath.createPoint(0.0, 0.0, 40.0));",
                "factory.commit();",
                "var objects = moi.geometryDatabase.getObjects();",
                "if (objects.length == 1) objects.item(0).name = 'Cylinder1';",
                f'moi.geometryDatabase.saveAs("{_js_string(native)}", "NoUI=true");',
                "moi.exit(true);",
            )
        ),
        encoding="utf-8",
    )
    reopen_script.write_text(
        "\n".join(
            (
                f'moi.geometryDatabase.open("{_js_string(native)}");',
                f'moi.geometryDatabase.saveAs("{_js_string(stl)}", '
                '"NoUI=true;Angle=12;Output=triangles;MaxLength=2;MaxLengthApplyTo=all;Weld=true");',
                "moi.exit(true);",
            )
        ),
        encoding="utf-8",
    )
    create_ini.write_text("", encoding="utf-8")
    reopen_ini.write_text("", encoding="utf-8")

    create_run = _run(args.moi_executable.resolve(), create_script, create_ini, args.timeout_seconds)
    if not native.is_file():
        raise RuntimeError(f"MoI did not create {native}")
    reopen_run = _run(args.moi_executable.resolve(), reopen_script, reopen_ini, args.timeout_seconds)
    if not stl.is_file():
        raise RuntimeError(f"MoI did not create {stl}")
    mesh = inspect_binary_stl(stl)
    report = {
        "schema": "xenosculpt-moi-cylinder-probe/v1",
        "executable": str(args.moi_executable.resolve()),
        "create": create_run,
        "reopen_export": reopen_run,
        "native": {
            "path": str(native),
            "bytes": native.stat().st_size,
            "sha256": sha256(native.read_bytes()).hexdigest(),
        },
        "stl": {
            "path": mesh.path,
            "bytes": mesh.bytes,
            "sha256": mesh.sha256,
            "triangle_count": mesh.triangle_count,
            "dimensions": mesh.dimensions,
            "basic_topology_valid": basic_mesh_valid(mesh),
        },
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if basic_mesh_valid(mesh) else 1


if __name__ == "__main__":
    raise SystemExit(main())
