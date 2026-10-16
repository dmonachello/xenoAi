"""Run one isolated XenoDream X 1.220 batch export to binary STL.

This is an experimental acceptance runner. It drives only the process that it
creates and records enough state to distinguish slow evaluation from a stalled
run. It does not change the native project generator.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import shutil
import sys
import time
from typing import Callable, Iterator

from xenodream_xxp.mesh import StlReport, inspect_binary_stl


@dataclass(frozen=True, slots=True)
class MeshExportSettings:
    """Evidence-backed controls on XenoDream X's batch mesh export form."""

    stl_max_dimension_mm: int = 250
    mesh_size_percent: int = 50

    def __post_init__(self) -> None:
        if isinstance(self.stl_max_dimension_mm, bool) or not isinstance(
            self.stl_max_dimension_mm, int
        ):
            raise TypeError("stl_max_dimension_mm must be an integer")
        if not 10 <= self.stl_max_dimension_mm <= 10_000:
            raise ValueError("stl_max_dimension_mm must be between 10 and 10000")
        if isinstance(self.mesh_size_percent, bool) or not isinstance(
            self.mesh_size_percent, int
        ):
            raise TypeError("mesh_size_percent must be an integer")
        if not 1 <= self.mesh_size_percent <= 100:
            raise ValueError("mesh_size_percent must be between 1 and 100")


def _hash_path(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def classify_timeout(samples: list[dict[str, object]], window_seconds: float = 60) -> str:
    if not samples:
        return "timed_out_stalled"
    cutoff = float(samples[-1]["elapsed_seconds"]) - window_seconds
    recent = [sample for sample in samples if float(sample["elapsed_seconds"]) >= cutoff]
    if len(recent) < 2:
        return "timed_out_stalled"
    cpu_delta = float(recent[-1]["cpu_seconds"]) - float(recent[0]["cpu_seconds"])
    status_changed = len({str(sample.get("status_text")) for sample in recent}) > 1
    output_changed = len({str(sample.get("outputs")) for sample in recent}) > 1
    return (
        "timed_out_active"
        if cpu_delta >= 0.1 or status_changed or output_changed
        else "timed_out_stalled"
    )


if os.name == "nt":
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    user32 = ctypes.WinDLL("user32", use_last_error=True)

    CREATE_SUSPENDED = 0x00000004
    CREATE_NEW_PROCESS_GROUP = 0x00000200
    JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
    JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9
    STILL_ACTIVE = 259
    WAIT_OBJECT_0 = 0
    WM_CLOSE = 0x0010
    WM_COMMAND = 0x0111
    WM_LBUTTONDOWN = 0x0201
    WM_LBUTTONUP = 0x0202
    BM_CLICK = 0x00F5
    CB_GETCOUNT = 0x0146
    CB_GETCURSEL = 0x0147
    CB_SETCURSEL = 0x014E
    CBN_SELCHANGE = 1
    TCM_GETITEMRECT = 0x130A
    MEM_COMMIT = 0x1000
    MEM_RESERVE = 0x2000
    MEM_RELEASE = 0x8000
    PAGE_READWRITE = 0x04
    SW_MINIMIZE = 6
    SMTO_ABORTIFHUNG = 0x0002

    class STARTUPINFOW(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("lpReserved", wintypes.LPWSTR),
            ("lpDesktop", wintypes.LPWSTR),
            ("lpTitle", wintypes.LPWSTR),
            ("dwX", wintypes.DWORD),
            ("dwY", wintypes.DWORD),
            ("dwXSize", wintypes.DWORD),
            ("dwYSize", wintypes.DWORD),
            ("dwXCountChars", wintypes.DWORD),
            ("dwYCountChars", wintypes.DWORD),
            ("dwFillAttribute", wintypes.DWORD),
            ("dwFlags", wintypes.DWORD),
            ("wShowWindow", wintypes.WORD),
            ("cbReserved2", wintypes.WORD),
            ("lpReserved2", ctypes.POINTER(ctypes.c_ubyte)),
            ("hStdInput", wintypes.HANDLE),
            ("hStdOutput", wintypes.HANDLE),
            ("hStdError", wintypes.HANDLE),
        ]

    class PROCESS_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("hProcess", wintypes.HANDLE),
            ("hThread", wintypes.HANDLE),
            ("dwProcessId", wintypes.DWORD),
            ("dwThreadId", wintypes.DWORD),
        ]

    class IO_COUNTERS(ctypes.Structure):
        _fields_ = [(name, ctypes.c_ulonglong) for name in (
            "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
            "ReadTransferCount", "WriteTransferCount", "OtherTransferCount",
        )]

    class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_longlong),
            ("PerJobUserTimeLimit", ctypes.c_longlong),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        ]

    class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
            ("IoInfo", IO_COUNTERS),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    class FILETIME(ctypes.Structure):
        _fields_ = [("dwLowDateTime", wintypes.DWORD), ("dwHighDateTime", wintypes.DWORD)]

    class RECT(ctypes.Structure):
        _fields_ = [("left", wintypes.LONG), ("top", wintypes.LONG),
                    ("right", wintypes.LONG), ("bottom", wintypes.LONG)]

    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    kernel32.VirtualAllocEx.restype = wintypes.LPVOID
    kernel32.CreateProcessW.argtypes = [
        wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.LPVOID, wintypes.LPVOID,
        wintypes.BOOL, wintypes.DWORD, wintypes.LPVOID, wintypes.LPCWSTR,
        ctypes.POINTER(STARTUPINFOW), ctypes.POINTER(PROCESS_INFORMATION),
    ]
    kernel32.CreateProcessW.restype = wintypes.BOOL
    user32.SendMessageTimeoutW.restype = wintypes.LPARAM


    def _check(value: object, operation: str) -> object:
        if not value:
            raise OSError(ctypes.get_last_error(), operation)
        return value


    def _text(hwnd: int) -> str:
        length = user32.GetWindowTextLengthW(hwnd)
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, len(buffer))
        return buffer.value


    def _class_name(hwnd: int) -> str:
        buffer = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, buffer, len(buffer))
        return buffer.value


    def _pid(hwnd: int) -> int:
        value = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(value))
        return value.value


    def _visible(hwnd: int) -> bool:
        return bool(user32.IsWindowVisible(hwnd))


    def _top_windows(pid: int) -> list[int]:
        result: list[int] = []

        @WNDENUMPROC
        def callback(hwnd: int, _parameter: int) -> bool:
            if _pid(hwnd) == pid and _visible(hwnd):
                result.append(hwnd)
            return True

        user32.EnumWindows(callback, 0)
        return result


    def _children(parent: int) -> list[int]:
        result: list[int] = []

        @WNDENUMPROC
        def callback(hwnd: int, _parameter: int) -> bool:
            result.append(hwnd)
            return True

        user32.EnumChildWindows(parent, callback, 0)
        return result


    def _owned(hwnd: int, pid: int) -> int:
        if not hwnd or _pid(hwnd) != pid:
            raise RuntimeError("refusing to use a window not owned by the automation PID")
        return hwnd


    def _find(
        windows: Iterator[int] | list[int],
        pid: int,
        *,
        class_name: str | None = None,
        caption: str | None = None,
        visible: bool | None = True,
        predicate: Callable[[int], bool] | None = None,
    ) -> int:
        matches = []
        for hwnd in windows:
            if _pid(hwnd) != pid:
                continue
            if class_name is not None and _class_name(hwnd) != class_name:
                continue
            if caption is not None and _text(hwnd) != caption:
                continue
            if visible is not None and _visible(hwnd) != visible:
                continue
            if predicate is not None and not predicate(hwnd):
                continue
            matches.append(hwnd)
        if len(matches) != 1:
            raise RuntimeError(
                f"expected one owned control, found {len(matches)} "
                f"for class={class_name!r} caption={caption!r}"
            )
        return matches[0]


    def _wait_for(function: Callable[[], object | None], timeout: float, label: str):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            value = function()
            if value:
                return value
            time.sleep(0.1)
        raise TimeoutError(f"timed out waiting for {label}")


    def _send(hwnd: int, message: int, wparam: int = 0, lparam: int = 0) -> int:
        result = wintypes.LPARAM()
        ok = user32.SendMessageTimeoutW(
            hwnd, message, wparam, lparam, SMTO_ABORTIFHUNG, 5000, ctypes.byref(result)
        )
        if not ok:
            raise TimeoutError(f"window message 0x{message:x} timed out")
        return int(result.value)


    def _click(hwnd: int) -> None:
        _send(hwnd, BM_CLICK)


    def _choose_file_with_controls(dialog: int, source: Path, pid: int) -> None:
        from pywinauto import Desktop
        from win32api import GetCursorPos, SetCursorPos

        _owned(dialog, pid)
        window = Desktop(backend="win32").window(handle=dialog)
        edit = window.child_window(class_name="Edit", control_id=1148).wrapper_object()
        open_button = window.child_window(
            class_name="Button", title="&Open"
        ).wrapper_object()
        cursor = GetCursorPos()
        try:
            edit.click_input()
            edit.type_keys("^a{BACKSPACE}")
            edit.type_keys(str(source), with_spaces=True, pause=0.01)
            _wait_for(
                lambda: edit if edit.window_text() == str(source) else None,
                10,
                "complete source path entry",
            )
            open_button.click()
        finally:
            SetCursorPos(cursor)


    class OwnedProcess:
        def __init__(self, executable: Path, source: Path, cwd: Path):
            self.process_handle = 0
            self.job_handle = 0
            self.pid = 0
            startup = STARTUPINFOW(cb=ctypes.sizeof(STARTUPINFOW))
            process = PROCESS_INFORMATION()
            command = ctypes.create_unicode_buffer(
                f'"{executable}" "{source}"'
            )
            job = _check(kernel32.CreateJobObjectW(None, None), "CreateJobObjectW")
            limits = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
            limits.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            try:
                _check(
                    kernel32.SetInformationJobObject(
                        job, JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
                        ctypes.byref(limits), ctypes.sizeof(limits)
                    ),
                    "SetInformationJobObject",
                )
                _check(
                    kernel32.CreateProcessW(
                        str(executable), command, None, None, False,
                        CREATE_SUSPENDED | CREATE_NEW_PROCESS_GROUP,
                        None, str(cwd), ctypes.byref(startup), ctypes.byref(process),
                    ),
                    "CreateProcessW",
                )
                self.process_handle = process.hProcess
                self.pid = process.dwProcessId
                _check(
                    kernel32.AssignProcessToJobObject(job, process.hProcess),
                    "AssignProcessToJobObject",
                )
                _check(kernel32.ResumeThread(process.hThread) != 0xFFFFFFFF, "ResumeThread")
                kernel32.CloseHandle(process.hThread)
                self.job_handle = job
            except BaseException:
                if process.hProcess:
                    kernel32.TerminateProcess(process.hProcess, 1)
                    kernel32.CloseHandle(process.hProcess)
                kernel32.CloseHandle(job)
                raise

        def active(self) -> bool:
            code = wintypes.DWORD()
            _check(kernel32.GetExitCodeProcess(self.process_handle, ctypes.byref(code)), "GetExitCodeProcess")
            return code.value == STILL_ACTIVE

        def cpu_seconds(self) -> float:
            created, exited, kernel, user = FILETIME(), FILETIME(), FILETIME(), FILETIME()
            _check(
                kernel32.GetProcessTimes(
                    self.process_handle, ctypes.byref(created), ctypes.byref(exited),
                    ctypes.byref(kernel), ctypes.byref(user)
                ),
                "GetProcessTimes",
            )

            def ticks(value: FILETIME) -> int:
                return value.dwLowDateTime | value.dwHighDateTime << 32

            return (ticks(kernel) + ticks(user)) / 10_000_000

        def close(self, main_window: int | None, grace_seconds: float = 5) -> bool:
            if main_window and _pid(main_window) == self.pid:
                user32.PostMessageW(main_window, WM_CLOSE, 0, 0)
                kernel32.WaitForSingleObject(self.process_handle, int(grace_seconds * 1000))
            if self.job_handle:
                kernel32.CloseHandle(self.job_handle)
                self.job_handle = 0
            kernel32.WaitForSingleObject(self.process_handle, 5000)
            stopped = not self.active()
            if self.process_handle:
                kernel32.CloseHandle(self.process_handle)
                self.process_handle = 0
            return stopped


    def _tab_rect(process: OwnedProcess, tab: int, index: int) -> RECT:
        remote = kernel32.VirtualAllocEx(
            process.process_handle, None, ctypes.sizeof(RECT),
            MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE
        )
        _check(remote, "VirtualAllocEx")
        try:
            _send(tab, TCM_GETITEMRECT, index, remote)
            rect = RECT()
            read = ctypes.c_size_t()
            _check(
                kernel32.ReadProcessMemory(
                    process.process_handle, remote, ctypes.byref(rect),
                    ctypes.sizeof(rect), ctypes.byref(read)
                ),
                "ReadProcessMemory",
            )
            return rect
        finally:
            kernel32.VirtualFreeEx(process.process_handle, remote, 0, MEM_RELEASE)


    def _choose_mesh_export(process: OwnedProcess, main: int) -> None:
        tab = _find(_children(main), process.pid, class_name="TTabControl")
        rect = _tab_rect(process, tab, 3)
        x = (rect.left + rect.right) // 2
        y = (rect.top + rect.bottom) // 2
        packed = (y << 16) | (x & 0xFFFF)
        _send(tab, WM_LBUTTONDOWN, 1, packed)
        _send(tab, WM_LBUTTONUP, 0, packed)


    def _replace_spin_value(hwnd: int, value: int, label: str) -> int:
        from pywinauto import Desktop
        from win32api import GetCursorPos, SetCursorPos

        control = Desktop(backend="win32").window(handle=hwnd)
        cursor = GetCursorPos()
        try:
            control.click_input()
            control.type_keys("^a{BACKSPACE}")
            control.type_keys(str(value))
            control.type_keys("{TAB}")
        finally:
            SetCursorPos(cursor)
        observed_text = _text(hwnd).strip()
        try:
            observed = int(observed_text)
        except ValueError as exception:
            raise RuntimeError(
                f"XenoDream returned non-integer {label}: {observed_text!r}"
            ) from exception
        # TDragSpinEdit updates its Value property from keyboard input but can
        # leave its HWND text stale until the form is recreated. The persisted
        # values are checked after the owned process closes.
        return observed


    def _configure_and_start(
        process: OwnedProcess,
        main: int,
        output: Path,
        source: Path,
        settings: MeshExportSettings,
    ) -> tuple[int, dict[str, int]]:
        _choose_mesh_export(process, main)

        def mesh_room() -> int | None:
            matches = [
                hwnd for hwnd in _children(main)
                if _pid(hwnd) == process.pid and _class_name(hwnd) == "TfmMeshExpRm"
                and _visible(hwnd)
            ]
            return matches[0] if len(matches) == 1 else None

        room = int(_wait_for(mesh_room, 10, "Mesh Export room"))
        saving_group = _find(
            _children(room), process.pid,
            class_name="TGroupBox", caption="Saving Files",
        )
        stl_dimension = _find(
            _children(saving_group), process.pid, class_name="TDragSpinEdit"
        )
        batch_header = _find(
            _children(room), process.pid, class_name="TPanel", caption=" Batch"
        )
        batch = _owned(user32.GetParent(batch_header), process.pid)
        controls = _children(batch)
        destination = _find(controls, process.pid, class_name="TLabeledEdit")
        formats = [
            hwnd for hwnd in controls
            if _pid(hwnd) == process.pid and _class_name(hwnd) == "TComboBox"
            and _send(hwnd, CB_GETCOUNT) == 4
        ]
        if len(formats) != 1:
            raise RuntimeError(f"expected one export-format combo, found {len(formats)}")
        format_combo = formats[0]
        source_button = _find(
            controls, process.pid, class_name="TToggleButton", caption="Select Files..."
        )
        mesh_size = _find(
            controls, process.pid, class_name="TDragSpinEdit"
        )

        observed_settings = {
            "stl_max_dimension_mm": _replace_spin_value(
                stl_dimension,
                settings.stl_max_dimension_mm,
                "STL maximum dimension (mm)",
            ),
            "mesh_size_percent": _replace_spin_value(
                mesh_size,
                settings.mesh_size_percent,
                "batch mesh size (%)",
            ),
        }

        output_text = str(output.resolve()) + os.sep
        from pywinauto import Desktop
        from win32api import GetCursorPos, SetCursorPos

        cursor = GetCursorPos()
        try:
            destination_edit = Desktop(backend="win32").window(
                handle=destination
            )
            _check(
                user32.SetWindowTextW(destination, output_text),
                "SetWindowTextW destination",
            )
            destination_edit.click_input()
            destination_edit.type_keys("{END} {BACKSPACE}")
            _wait_for(
                lambda: destination if _text(destination) == output_text else None,
                10,
                "complete destination entry",
            )
        finally:
            SetCursorPos(cursor)
        _send(format_combo, CB_SETCURSEL, 1, 0)
        control_id = user32.GetDlgCtrlID(format_combo)
        _send(
            user32.GetParent(format_combo), WM_COMMAND,
            (CBN_SELCHANGE << 16) | (control_id & 0xFFFF), format_combo,
        )
        if _send(format_combo, CB_GETCURSEL) != 1:
            raise RuntimeError("XenoDream did not retain the binary STL selection")

        user32.PostMessageW(source_button, BM_CLICK, 0, 0)

        def chooser() -> int | None:
            matches = [
                hwnd for hwnd in _top_windows(process.pid)
                if _class_name(hwnd) == "#32770"
                and _text(hwnd) == "Files for batch export"
            ]
            return matches[0] if len(matches) == 1 else None

        dialog = int(_wait_for(chooser, 10, "batch source chooser"))
        _choose_file_with_controls(dialog, source.resolve(), process.pid)
        _wait_for(
            lambda: True if not user32.IsWindow(dialog) or not _visible(dialog) else None,
            15,
            "batch source chooser close",
        )
        try:
            _wait_for(
                lambda: source_button if _text(source_button) == "Cancel Batch" else None,
                15,
                "batch start",
            )
        except TimeoutError as exception:
            top_state = [
                {"class": _class_name(hwnd), "caption": _text(hwnd)}
                for hwnd in _top_windows(process.pid)
            ]
            raise TimeoutError(
                f"timed out waiting for batch start; owned top windows: {top_state!r}"
            ) from exception
        user32.ShowWindow(main, SW_MINIMIZE)
        return source_button, observed_settings


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _read_mesh_export_preferences() -> dict[str, int] | None:
    path = Path.home() / "Documents" / "XenoDreamX" / "XenoDreamX.ini"
    if not path.is_file():
        return None
    wanted = {"STLMaxDim": "stl_max_dimension_mm", "BatchProgSize": "mesh_size_percent"}
    found: dict[str, int] = {}
    for line in path.read_text(encoding="latin-1").splitlines():
        key, separator, value = line.partition("=")
        if separator and key in wanted:
            try:
                found[wanted[key]] = int(value.strip())
            except ValueError:
                return None
    return found if set(found) == set(wanted.values()) else None


def run_export(
    executable: Path,
    source: Path,
    run_directory: Path,
    report_path: Path,
    timeout_seconds: float,
    poll_seconds: float,
    settings: MeshExportSettings = MeshExportSettings(),
) -> dict[str, object]:
    if os.name != "nt":
        raise RuntimeError("XenoDream automation requires Windows")
    executable = executable.resolve(strict=True)
    source = source.resolve(strict=True)
    if run_directory.exists() and any(run_directory.iterdir()):
        raise ValueError(f"run directory must be new or empty: {run_directory}")
    run_directory.mkdir(parents=True, exist_ok=True)
    output_directory = run_directory / "mesh"
    output_directory.mkdir()
    run_stem = re.sub(r"[^A-Za-z0-9_-]", "_", run_directory.name)[:20]
    if not run_stem:
        run_stem = "run"
    disposable = run_directory / f"xdx_{run_stem}.xxp"
    shutil.copy2(source, disposable)
    disposable = disposable.resolve()
    source_before = _hash_path(source)
    disposable_before = _hash_path(disposable)
    progress_path = run_directory / "progress.jsonl"
    default_output = Path.home() / "Documents" / "XenoDreamX" / f"{disposable.stem}.stl"
    if default_output.exists():
        raise ValueError(f"refusing to overwrite default XenoDream output: {default_output}")
    # EnumWindows cannot filter all process names without opening foreign
    # processes. Record only visible XenoDream main-window PIDs and never act on
    # them.
    visible_preexisting: list[int] = []

    @WNDENUMPROC
    def collect(hwnd: int, _parameter: int) -> bool:
        if _visible(hwnd) and _class_name(hwnd) == "TfmMain":
            visible_preexisting.append(_pid(hwnd))
        return True

    user32.EnumWindows(collect, 0)
    preexisting = sorted(set(visible_preexisting))

    process: OwnedProcess | None = None
    main: int | None = None
    samples: list[dict[str, object]] = []
    completion_windows: list[dict[str, str]] = []
    outcome = "start_failed"
    error: str | None = None
    stl: StlReport | None = None
    relocated_from: str | None = None
    observed_settings: dict[str, int] | None = None
    cleanup_confirmed = False
    persisted_settings_before = _read_mesh_export_preferences()
    started = time.monotonic()
    try:
        process = OwnedProcess(executable, disposable, run_directory)

        def main_window() -> int | None:
            matches = [
                hwnd for hwnd in _top_windows(process.pid)
                if _class_name(hwnd) == "TfmMain"
            ]
            return matches[0] if len(matches) == 1 else None

        main = int(_wait_for(main_window, 30, "owned XenoDream main window"))
        time.sleep(2)
        tip_matches = [
            hwnd for hwnd in _top_windows(process.pid)
            if _class_name(hwnd) == "TfmTipoftheday" and _visible(hwnd)
        ]
        if tip_matches:
            close = _find(
                _children(tip_matches[0]), process.pid,
                class_name="TButton", caption="Close", visible=True,
            )
            _click(close)
            _wait_for(lambda: main if user32.IsWindowEnabled(main) else None, 10, "tip close")

        run_button, observed_settings = _configure_and_start(
            process, main, output_directory, disposable, settings
        )
        outcome = "running"
        stable_signature: tuple[int, int] | None = None
        stable_polls = 0
        deadline = started + timeout_seconds
        while time.monotonic() < deadline:
            if not process.active():
                outcome = "application_exited"
                break
            outputs = sorted(output_directory.glob("*.stl"))
            output_state = [
                {"name": path.name, "bytes": path.stat().st_size,
                 "mtime_ns": path.stat().st_mtime_ns}
                for path in outputs
            ]
            status_controls = [
                hwnd for hwnd in _children(main)
                if _class_name(hwnd) == "TStatusBar" and _visible(hwnd)
            ]
            sample = {
                "elapsed_seconds": round(time.monotonic() - started, 3),
                "cpu_seconds": round(process.cpu_seconds(), 3),
                "responding": not bool(user32.IsHungAppWindow(main)),
                "batch_caption": _text(run_button),
                "status_text": _text(status_controls[0]) if status_controls else None,
                "outputs": output_state,
            }
            samples.append(sample)
            with progress_path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(sample, sort_keys=True) + "\n")

            if len(outputs) == 1:
                stat = outputs[0].stat()
                signature = (stat.st_size, stat.st_mtime_ns)
                stable_polls = stable_polls + 1 if signature == stable_signature else 1
                stable_signature = signature
            else:
                stable_signature = None
                stable_polls = 0

            if _text(run_button) != "Cancel Batch":
                if stable_polls >= 3:
                    stl = inspect_binary_stl(outputs[0])
                    outcome = "succeeded"
                    break
                if not outputs:
                    if default_output.is_file():
                        relocated_from = str(default_output.resolve())
                        relocated = output_directory / default_output.name
                        shutil.move(str(default_output), relocated)
                        stl = inspect_binary_stl(relocated)
                        outcome = "succeeded"
                        break
                    completion_windows = [
                        {"class": _class_name(hwnd), "caption": _text(hwnd)}
                        for hwnd in _top_windows(process.pid)
                    ]
                    outcome = "completed_without_output"
                    break
            time.sleep(poll_seconds)
        else:
            outcome = classify_timeout(samples)
            outputs = sorted(output_directory.glob("*.stl"))
            if len(outputs) == 1:
                try:
                    stl = inspect_binary_stl(outputs[0])
                    outcome = "output_valid_completion_unconfirmed"
                except ValueError:
                    pass
    except BaseException as exception:
        error = f"{type(exception).__name__}: {exception}"
        if outcome in {"start_failed", "running"}:
            outcome = "automation_failed"
    finally:
        if process is not None:
            try:
                cleanup_confirmed = process.close(main)
            except BaseException as cleanup_error:
                cleanup_confirmed = False
                cleanup_text = f"{type(cleanup_error).__name__}: {cleanup_error}"
                error = f"{error}; cleanup: {cleanup_text}" if error else cleanup_text

    source_after = _hash_path(source)
    disposable_after = _hash_path(disposable)
    persisted_settings_after = _read_mesh_export_preferences()
    if source_after != source_before or disposable_after != disposable_before:
        outcome = "source_changed"
    if not cleanup_confirmed:
        outcome = "cleanup_failed"
    if outcome == "succeeded" and persisted_settings_after != asdict(settings):
        outcome = "settings_not_applied"
    report: dict[str, object] = {
        "schema": "xenodream-batch-stl/v2",
        "outcome": outcome,
        "error": error,
        "owned_pid": process.pid if process is not None else None,
        "preexisting_visible_xenodream_pids": preexisting,
        "input": {
            "source": str(source),
            "disposable": str(disposable),
            "source_sha256_before": source_before,
            "source_sha256_after": source_after,
            "disposable_sha256_before": disposable_before,
            "disposable_sha256_after": disposable_after,
        },
        "output_directory": str(output_directory.resolve()),
        "mesh_export_settings": {
            "requested": asdict(settings),
            "control_display_after_input": observed_settings,
            "persisted_before": persisted_settings_before,
            "persisted_after": persisted_settings_after,
            "coordinate_unit": "millimetre",
        },
        "stl": asdict(stl) if stl is not None else None,
        "relocated_from": relocated_from,
        "samples": samples,
        "completion_windows": completion_windows,
        "progress_log": str(progress_path.resolve()),
        "cleanup_confirmed": cleanup_confirmed,
        "elapsed_seconds": round(time.monotonic() - started, 3),
    }
    _write_json(report_path.resolve(), report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("run_directory", type=Path)
    parser.add_argument(
        "--executable",
        type=Path,
        default=Path(r"C:\Program Files (x86)\XenoDream Software\XenoDreamX\XenoDreamX.exe"),
    )
    parser.add_argument("--timeout-seconds", type=float, default=600)
    parser.add_argument("--poll-seconds", type=float, default=1)
    parser.add_argument("--stl-max-dimension-mm", type=int, default=250)
    parser.add_argument("--mesh-size-percent", type=int, default=50)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        settings = MeshExportSettings(
            stl_max_dimension_mm=args.stl_max_dimension_mm,
            mesh_size_percent=args.mesh_size_percent,
        )
        report = run_export(
            args.executable,
            args.source,
            args.run_directory,
            args.report,
            args.timeout_seconds,
            args.poll_seconds,
            settings,
        )
    except (OSError, RuntimeError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2
    summary = {
        "cleanup_confirmed": report["cleanup_confirmed"],
        "elapsed_seconds": report["elapsed_seconds"],
        "error": report["error"],
        "outcome": report["outcome"],
        "owned_pid": report["owned_pid"],
        "report": str(args.report.resolve()),
        "sample_count": len(report["samples"]),
        "stl": report["stl"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if report["outcome"] == "succeeded" else 1


if __name__ == "__main__":
    raise SystemExit(main())
