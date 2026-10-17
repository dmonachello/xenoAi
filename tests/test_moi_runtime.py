from decimal import Decimal
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest

from xenosculpt.moi import CylinderSpec
from xenosculpt.core import WorkspaceError
from xenosculpt.moi.model import MoiInstallation
from xenosculpt.moi.runtime import MoiCylinderRuntime, _write_script


def test_create_script_sets_document_units_and_uses_fixed_factory_inputs() -> None:
    script = MoiCylinderRuntime._create_script(
        CylinderSpec(Decimal("15"), Decimal("40")), Path(r"C:\run\model.3dm")
    )

    assert "moi.geometryDatabase.units = 'Millimeters';" in script
    assert "factory.setInput(3, 15);" in script
    assert "createPoint(0, 0, 40)" in script
    assert "saveAs" in script


def test_script_hash_identifies_exact_written_bytes(tmp_path) -> None:
    path = tmp_path / "script.js"
    digest = _write_script(path, "one\ntwo\n")

    from hashlib import sha256

    assert digest == sha256(path.read_bytes()).hexdigest()
    assert path.read_bytes() == b"one\ntwo\n"


@pytest.mark.parametrize("timeout", [float("nan"), float("inf"), float("-inf"), 0])
def test_runtime_rejects_unbounded_timeout(timeout: float) -> None:
    runtime = MoiCylinderRuntime.__new__(MoiCylinderRuntime)
    with pytest.raises(ValueError, match="positive"):
        runtime.create_and_verify(CylinderSpec(Decimal("1"), Decimal("1")), timeout_seconds=timeout)


def test_timeout_confirms_owned_process_tree_stopped(monkeypatch, tmp_path) -> None:
    class Process:
        pid = 1234
        waits = 0

        def wait(self, timeout):
            self.waits += 1
            if self.waits == 1:
                raise subprocess.TimeoutExpired("MoI", timeout)
            return 1

    process = Process()
    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: process)
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stderr=""),
    )
    runtime = MoiCylinderRuntime(MoiInstallation("C:/MoI.exe", "4.0.2020.1222", "a" * 64))

    with pytest.raises(WorkspaceError, match="timed out after"):
        runtime._run(tmp_path / "script.js", tmp_path / "isolated.ini", 0.01)

    assert process.waits == 2
