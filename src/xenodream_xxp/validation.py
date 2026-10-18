"""Managed XenoDream installation and validation-profile policy."""

from __future__ import annotations

from contextlib import contextmanager
import ctypes
from ctypes import wintypes
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json
import os
from pathlib import Path
from typing import Iterator

from .errors import WorkspaceError
from .metamorph import load_metamorph_registry
from .native_export import MeshExportSettings


PROFILE_SCHEMA = "xenosculpt-xenodream-validation-profile/v1"
SUPPORTED_FILE_VERSION = "1.22.0.0"
SUPPORTED_EXECUTABLE_SHA256 = str(
    load_metamorph_registry()["target"]["executable_sha256"]
)


class ValidationProfileName(str, Enum):
    PREVIEW = "preview"
    REVIEW = "review"


@dataclass(frozen=True, slots=True)
class ValidationProfile:
    name: ValidationProfileName
    version: int
    mesh_size_percent: int
    timeout_seconds: float
    poll_seconds: float
    definition_sha256: str

    def to_request_dict(self) -> dict[str, object]:
        return {
            "name": self.name.value,
            "version": self.version,
            "definition_sha256": self.definition_sha256,
            "timeout_seconds": self.timeout_seconds,
            "poll_seconds": self.poll_seconds,
        }


@dataclass(frozen=True, slots=True)
class XenoDreamInstallation:
    executable: str
    file_version: str
    executable_sha256: str

    def to_request_dict(self) -> dict[str, str]:
        return {
            "file_version": self.file_version,
            "executable_sha256": self.executable_sha256,
        }


@dataclass(frozen=True, slots=True)
class ResolvedValidationRequest:
    settings: MeshExportSettings
    timeout_seconds: float
    poll_seconds: float
    profile: ValidationProfile
    installation: XenoDreamInstallation


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, allow_nan=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _profile(
    name: ValidationProfileName,
    mesh_size_percent: int,
    timeout_seconds: float,
) -> ValidationProfile:
    definition = {
        "schema": PROFILE_SCHEMA,
        "name": name.value,
        "version": 1,
        "mesh_size_percent": mesh_size_percent,
        "timeout_seconds": timeout_seconds,
        "poll_seconds": 1.0,
    }
    return ValidationProfile(
        name=name,
        version=1,
        mesh_size_percent=mesh_size_percent,
        timeout_seconds=timeout_seconds,
        poll_seconds=1.0,
        definition_sha256=sha256(_canonical(definition)).hexdigest(),
    )


_PROFILES = {
    ValidationProfileName.PREVIEW: _profile(
        ValidationProfileName.PREVIEW, 10, 180.0
    ),
    ValidationProfileName.REVIEW: _profile(
        ValidationProfileName.REVIEW, 50, 600.0
    ),
}


def validation_profile(name: ValidationProfileName | str) -> ValidationProfile:
    try:
        key = name if isinstance(name, ValidationProfileName) else ValidationProfileName(name)
    except ValueError as error:
        raise ValueError(f"unknown XenoDream validation profile: {name}") from error
    return _PROFILES[key]


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _file_version(path: Path) -> str:
    if os.name != "nt":
        raise WorkspaceError("XenoDream installation inspection requires Windows")
    version = ctypes.windll.version
    size = version.GetFileVersionInfoSizeW(str(path), None)
    if not size:
        raise WorkspaceError(f"cannot read XenoDream executable version: {path}")
    buffer = ctypes.create_string_buffer(size)
    if not version.GetFileVersionInfoW(str(path), 0, size, buffer):
        raise WorkspaceError(f"cannot read XenoDream executable version: {path}")
    pointer = ctypes.c_void_p()
    length = ctypes.c_uint()
    if not version.VerQueryValueW(
        buffer, "\\", ctypes.byref(pointer), ctypes.byref(length)
    ):
        raise WorkspaceError(f"cannot read XenoDream executable version: {path}")
    values = ctypes.cast(pointer, ctypes.POINTER(ctypes.c_uint32))
    ms, ls = values[2], values[3]
    return f"{ms >> 16}.{ms & 0xffff}.{ls >> 16}.{ls & 0xffff}"


def resolve_xenodream_installation(
    executable: str | Path,
) -> XenoDreamInstallation:
    path = Path(executable).resolve(strict=True)
    if not path.is_file():
        raise WorkspaceError(f"XenoDream executable does not exist: {path}")
    file_version = _file_version(path)
    if file_version != SUPPORTED_FILE_VERSION:
        raise WorkspaceError(
            f"XenoDream X file version {SUPPORTED_FILE_VERSION} is required; "
            f"found {file_version}"
        )
    executable_sha256 = _file_sha256(path)
    if executable_sha256 != SUPPORTED_EXECUTABLE_SHA256:
        raise WorkspaceError(
            "the XenoDream executable does not match the supported XDX 1.220 release"
        )
    return XenoDreamInstallation(str(path), file_version, executable_sha256)


def resolve_profile_request(
    name: ValidationProfileName,
    *,
    stl_max_dimension_mm: int,
    executable: str | Path,
) -> ResolvedValidationRequest:
    profile = validation_profile(name)
    settings = MeshExportSettings(
        stl_max_dimension_mm=stl_max_dimension_mm,
        mesh_size_percent=profile.mesh_size_percent,
    )
    return ResolvedValidationRequest(
        settings=settings,
        timeout_seconds=profile.timeout_seconds,
        poll_seconds=profile.poll_seconds,
        profile=profile,
        installation=resolve_xenodream_installation(executable),
    )


class _ProcessEntry(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.c_size_t),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", wintypes.LONG),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", wintypes.WCHAR * 260),
    ]


def _discover_xenodream_pids() -> tuple[int, ...]:
    if os.name != "nt":
        raise WorkspaceError("XenoDream session inspection requires Windows")
    kernel32 = ctypes.windll.kernel32
    kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    snapshot = kernel32.CreateToolhelp32Snapshot(0x00000002, 0)
    invalid_handle = wintypes.HANDLE(-1).value
    if snapshot == invalid_handle:
        raise WorkspaceError("cannot inspect running XenoDream sessions")
    entry = _ProcessEntry()
    entry.dwSize = ctypes.sizeof(entry)
    found: list[int] = []
    try:
        kernel32.SetLastError(0)
        success = kernel32.Process32FirstW(snapshot, ctypes.byref(entry))
        if not success:
            error = kernel32.GetLastError()
            if error != 18:  # ERROR_NO_MORE_FILES
                raise WorkspaceError("cannot enumerate running XenoDream sessions")
        while success:
            if entry.szExeFile.casefold() == "xenodreamx.exe":
                found.append(int(entry.th32ProcessID))
            kernel32.SetLastError(0)
            success = kernel32.Process32NextW(snapshot, ctypes.byref(entry))
            if not success:
                error = kernel32.GetLastError()
                if error != 18:  # ERROR_NO_MORE_FILES
                    raise WorkspaceError(
                        "cannot enumerate running XenoDream sessions"
                    )
    finally:
        kernel32.CloseHandle(snapshot)
    return tuple(sorted(set(found)))


def _current_user_sid() -> str:
    if os.name != "nt":
        raise WorkspaceError("Windows user identity inspection requires Windows")
    kernel32 = ctypes.windll.kernel32
    advapi32 = ctypes.windll.advapi32
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    advapi32.OpenProcessToken.argtypes = (
        wintypes.HANDLE,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.HANDLE),
    )
    advapi32.OpenProcessToken.restype = wintypes.BOOL
    advapi32.GetTokenInformation.argtypes = (
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
    )
    advapi32.GetTokenInformation.restype = wintypes.BOOL
    advapi32.ConvertSidToStringSidW.argtypes = (
        ctypes.c_void_p,
        ctypes.POINTER(wintypes.LPWSTR),
    )
    advapi32.ConvertSidToStringSidW.restype = wintypes.BOOL
    token = wintypes.HANDLE()
    if not advapi32.OpenProcessToken(
        kernel32.GetCurrentProcess(), 0x0008, ctypes.byref(token)
    ):
        raise WorkspaceError("cannot inspect the current Windows user identity")
    try:
        needed = wintypes.DWORD()
        advapi32.GetTokenInformation(token, 1, None, 0, ctypes.byref(needed))
        if not needed.value:
            raise WorkspaceError("cannot inspect the current Windows user identity")
        buffer = ctypes.create_string_buffer(needed.value)
        if not advapi32.GetTokenInformation(
            token, 1, buffer, needed, ctypes.byref(needed)
        ):
            raise WorkspaceError("cannot inspect the current Windows user identity")
        sid_pointer = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_void_p))[0]
        sid_text = wintypes.LPWSTR()
        if not advapi32.ConvertSidToStringSidW(
            sid_pointer, ctypes.byref(sid_text)
        ):
            raise WorkspaceError("cannot inspect the current Windows user identity")
        try:
            return sid_text.value
        finally:
            kernel32.LocalFree(sid_text)
    finally:
        kernel32.CloseHandle(token)


def _mutex_name() -> str:
    user = sha256(_current_user_sid().encode("ascii")).hexdigest()[:16]
    return f"Global\\XenoSculpt.XenoDream.Validation.{user}"


def ensure_no_xenodream_sessions() -> None:
    pids = _discover_xenodream_pids()
    if pids:
        joined = ", ".join(str(pid) for pid in pids)
        raise WorkspaceError(
            f"close XenoDream before managed validation; process IDs: {joined}"
        )


@contextmanager
def pinned_executable(installation: XenoDreamInstallation) -> Iterator[Path]:
    """Hold an approved executable open without write/delete sharing."""

    if os.name != "nt":
        raise WorkspaceError("managed XenoDream validation requires Windows")
    path = Path(installation.executable)
    kernel32 = ctypes.windll.kernel32
    kernel32.CreateFileW.restype = wintypes.HANDLE
    handle = kernel32.CreateFileW(
        str(path),
        0x80000000,  # GENERIC_READ
        0x00000001,  # FILE_SHARE_READ
        None,
        3,  # OPEN_EXISTING
        0x00000080,  # FILE_ATTRIBUTE_NORMAL
        None,
    )
    invalid_handle = wintypes.HANDLE(-1).value
    if handle in (None, 0, invalid_handle):
        raise WorkspaceError("cannot lock the XenoDream executable for validation")
    try:
        current = resolve_xenodream_installation(path)
        if current != installation:
            raise WorkspaceError("the XenoDream executable changed before validation")
        yield path
    finally:
        kernel32.CloseHandle(handle)


@contextmanager
def managed_validation_session(
    installation: XenoDreamInstallation,
) -> Iterator[None]:
    del installation
    if os.name != "nt":
        raise WorkspaceError("managed XenoDream validation requires Windows")
    kernel32 = ctypes.windll.kernel32
    kernel32.CreateMutexW.restype = wintypes.HANDLE
    handle = kernel32.CreateMutexW(None, False, _mutex_name())
    if not handle:
        raise WorkspaceError("cannot create the XenoDream validation mutex")
    acquired = False
    try:
        wait = kernel32.WaitForSingleObject(handle, 0)
        if wait not in (0x00000000, 0x00000080):
            if wait == 0x00000102:
                raise WorkspaceError("another XenoSculpt XenoDream validation is running")
            raise WorkspaceError("cannot acquire the XenoDream validation mutex")
        acquired = True
        ensure_no_xenodream_sessions()
        yield
    finally:
        if acquired:
            kernel32.ReleaseMutex(handle)
        kernel32.CloseHandle(handle)
