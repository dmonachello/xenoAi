"""Version-pinned, owned-process MoI cylinder execution."""

from __future__ import annotations

import ctypes
from dataclasses import dataclass
from hashlib import sha256
import json
import math
from pathlib import Path
import subprocess
import tempfile
import time

from xenosculpt.core import WorkspaceError
from xenosculpt.mesh import basic_mesh_valid, inspect_binary_stl

from .model import CylinderSpec, MoiEvidence, MoiInstallation


MOI_VERSION = "4.0.2020.1222"
_MESH_OPTIONS = "NoUI=true;Angle=12;Output=triangles;MaxLength=2;MaxLengthApplyTo=all;Weld=true"
_MAX_OUTPUT_BYTES = 256 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class NativeCylinderResult:
    native_data: bytes
    stl_data: bytes
    evidence: MoiEvidence


def _canonical(value: object) -> bytes:
    return json.dumps(value, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()


def _js_string(path: Path) -> str:
    return str(path.resolve()).replace("\\", "\\\\").replace('"', '\\"')


def _write_script(path: Path, source: str) -> str:
    data = source.encode("utf-8")
    path.write_bytes(data)
    return sha256(data).hexdigest()


def _file_version(path: Path) -> str:
    version = ctypes.windll.version
    size = version.GetFileVersionInfoSizeW(str(path), None)
    if not size:
        raise WorkspaceError(f"cannot read MoI executable version: {path}")
    buffer = ctypes.create_string_buffer(size)
    if not version.GetFileVersionInfoW(str(path), 0, size, buffer):
        raise WorkspaceError(f"cannot read MoI executable version: {path}")
    pointer = ctypes.c_void_p()
    length = ctypes.c_uint()
    if not version.VerQueryValueW(buffer, "\\", ctypes.byref(pointer), ctypes.byref(length)):
        raise WorkspaceError(f"cannot read MoI executable version: {path}")
    values = ctypes.cast(pointer, ctypes.POINTER(ctypes.c_uint32))
    ms, ls = values[2], values[3]
    return f"{ms >> 16}.{ms & 0xffff}.{ls >> 16}.{ls & 0xffff}"


class MoiCylinderRuntime:
    def __init__(self, installation: MoiInstallation) -> None:
        self.installation = installation

    @classmethod
    def for_executable(cls, executable: str | Path) -> "MoiCylinderRuntime":
        path = Path(executable).resolve()
        if not path.is_file():
            raise WorkspaceError(f"MoI executable does not exist: {path}")
        file_version = _file_version(path)
        if file_version != MOI_VERSION:
            raise WorkspaceError(f"MoI version {MOI_VERSION} is required; found {file_version}")
        return cls(MoiInstallation(str(path), file_version, sha256(path.read_bytes()).hexdigest()))

    def create_and_verify(self, spec: CylinderSpec, *, timeout_seconds: float = 120) -> NativeCylinderResult:
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        with tempfile.TemporaryDirectory(prefix="xenosculpt-moi-") as temporary:
            root = Path(temporary)
            native, stl = root / "model.3dm", root / "validation.stl"
            create_script = self._create_script(spec, native)
            reopen_script = self._reopen_script(native, stl)
            create_path, reopen_path = root / "create.js", root / "reopen.js"
            create_script_sha = _write_script(create_path, create_script)
            reopen_script_sha = _write_script(reopen_path, reopen_script)
            create_ini, reopen_ini = root / "create.ini", root / "reopen.ini"
            create_ini.write_bytes(b"")
            reopen_ini.write_bytes(b"")
            create_seconds = self._run(create_path, create_ini, timeout_seconds)
            native_data = self._read_output(native, ".3dm")
            if not native_data.startswith(b"3D Geometry File Format"):
                raise WorkspaceError("MoI output is not a 3DM document")
            reopen_seconds = self._run(reopen_path, reopen_ini, timeout_seconds)
            stl_data = self._read_output(stl, ".stl")
            mesh = inspect_binary_stl(stl)
            if not basic_mesh_valid(mesh):
                raise WorkspaceError("MoI validation STL failed basic topology checks")
            expected = (float(spec.radius_mm * 2), float(spec.radius_mm * 2), float(spec.height_mm))
            if any(abs(actual - wanted) > 0.01 for actual, wanted in zip(mesh.dimensions, expected)):
                raise WorkspaceError(f"MoI validation dimensions {mesh.dimensions} do not match {expected}")
            if sha256(Path(self.installation.executable).read_bytes()).hexdigest() != self.installation.executable_sha256:
                raise WorkspaceError("MoI executable changed during native execution")
            request_sha = sha256(_canonical(spec.to_dict())).hexdigest()
            evidence = MoiEvidence(
                "xenosculpt-moi-cylinder-evidence/v1", self.installation, request_sha,
                create_script_sha, reopen_script_sha,
                sha256(native_data).hexdigest(), len(native_data), sha256(stl_data).hexdigest(),
                len(stl_data), create_seconds, reopen_seconds, mesh,
            )
            return NativeCylinderResult(native_data, stl_data, evidence)

    def _run(self, script: Path, ini: Path, timeout: float) -> float:
        startup = subprocess.STARTUPINFO()
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = subprocess.SW_HIDE
        started = time.monotonic()
        process = subprocess.Popen([self.installation.executable, str(script), str(ini)], cwd=script.parent,
                                   startupinfo=startup, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        try:
            return_code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            killed = subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True, text=True, check=False)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                raise WorkspaceError(
                    f"MoI timed out and its owned process tree could not be stopped: {killed.stderr.strip()}"
                ) from None
            if killed.returncode != 0:
                raise WorkspaceError(
                    f"MoI timed out; process cleanup reported an error: {killed.stderr.strip()}"
                ) from None
            raise WorkspaceError(f"MoI timed out after {timeout:g} seconds") from None
        if return_code != 0:
            raise WorkspaceError(f"MoI exited with code {return_code}")
        return round(time.monotonic() - started, 3)

    @staticmethod
    def _read_output(path: Path, kind: str) -> bytes:
        if not path.is_file():
            raise WorkspaceError(f"MoI did not create the expected {kind} output")
        size = path.stat().st_size
        if size == 0 or size > _MAX_OUTPUT_BYTES:
            raise WorkspaceError(f"MoI {kind} output has an invalid size: {size}")
        return path.read_bytes()

    @staticmethod
    def _create_script(spec: CylinderSpec, native: Path) -> str:
        return "\n".join((
            "moi.geometryDatabase.units = 'Millimeters';",
            "var factory = moi.command.createFactory('cylinder');",
            "factory.setInput(1, moi.vectorMath.createTopFrame());",
            f"factory.setInput(3, {format(spec.radius_mm, 'f')});",
            f"factory.setInput(4, moi.vectorMath.createPoint(0, 0, {format(spec.height_mm, 'f')}));",
            "factory.commit();", "var objects = moi.geometryDatabase.getObjects();",
            "if (objects.length == 1) objects.item(0).name = 'Cylinder1';",
            f'moi.geometryDatabase.saveAs("{_js_string(native)}", "NoUI=true");', "moi.exit(true);", ""))

    @staticmethod
    def _reopen_script(native: Path, stl: Path) -> str:
        return "\n".join((f'moi.geometryDatabase.open("{_js_string(native)}");',
                           f'moi.geometryDatabase.saveAs("{_js_string(stl)}", "{_MESH_OPTIONS}");',
                           "moi.exit(true);", ""))
