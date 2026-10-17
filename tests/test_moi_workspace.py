from __future__ import annotations

from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
import struct
from dataclasses import asdict

import pytest

from xenosculpt.core import WorkspaceError
from xenosculpt.mesh import inspect_binary_stl
from xenosculpt.moi import CylinderSpec, MoiProject
from xenosculpt.moi.model import MoiEvidence, MoiInstallation
from xenosculpt.moi.runtime import NativeCylinderResult
from xenosculpt.moi.workspace import _decode_evidence


def _tetrahedron() -> bytes:
    vertices = ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
    faces = ((0, 2, 1), (0, 1, 3), (0, 3, 2), (1, 2, 3))
    data = bytearray(80)
    data.extend(struct.pack("<I", len(faces)))
    for face in faces:
        coordinates = tuple(value for index in face for value in vertices[index])
        data.extend(struct.pack("<12fH", 0, 0, 0, *coordinates, 0))
    return bytes(data)


class _FakeRuntime:
    def __init__(self, tmp_path: Path) -> None:
        self.tmp_path = tmp_path

    def create_and_verify(self, spec, *, timeout_seconds):
        stl = _tetrahedron()
        path = self.tmp_path / "fake.stl"
        path.write_bytes(stl)
        mesh = inspect_binary_stl(path)
        native = b"3D Geometry File Format       50\0fake"
        evidence = MoiEvidence(
            "xenosculpt-moi-cylinder-evidence/v1",
            MoiInstallation("C:/MoI.exe", "4.0.2020.1222", "a" * 64),
            sha256(json.dumps(spec.to_dict(), sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
            "c" * 64,
            "d" * 64,
            sha256(native).hexdigest(),
            len(native),
            sha256(stl).hexdigest(),
            len(stl),
            0.1,
            0.1,
            mesh,
        )
        return NativeCylinderResult(native, stl, evidence)


def test_moi_workspace_retains_native_and_verified_stl(tmp_path, monkeypatch) -> None:
    fake = _FakeRuntime(tmp_path)
    monkeypatch.setattr("xenosculpt.moi.workspace.MoiCylinderRuntime.for_executable", lambda _: fake)
    root = tmp_path / "cylinder.msp"

    project = MoiProject.create_cylinder(
        root, CylinderSpec(Decimal("0.5"), Decimal("1")), moi_executable="ignored"
    )
    status = project.status()
    native = project.export(tmp_path / "cylinder.3dm")
    mesh = project.export_stl(tmp_path / "cylinder.stl")

    assert status.application_id == "moi3d"
    assert status.head.operation == "moi-create-cylinder-v1"
    assert native.sha256 == status.head.artifact_sha256
    assert mesh.sha256 == status.evidence.stl_sha256


def test_moi_workspace_rejects_tampered_stl(tmp_path, monkeypatch) -> None:
    fake = _FakeRuntime(tmp_path)
    monkeypatch.setattr("xenosculpt.moi.workspace.MoiCylinderRuntime.for_executable", lambda _: fake)
    project = MoiProject.create_cylinder(
        tmp_path / "cylinder.msp", CylinderSpec(Decimal("0.5"), Decimal("1")), moi_executable="ignored"
    )
    retained = Path(project.status().evidence.mesh.path)
    retained.write_bytes(retained.read_bytes() + b"tampered")

    with pytest.raises((WorkspaceError, ValueError), match="length mismatch|verification"):
        project.status()


def test_failed_native_run_does_not_publish_workspace(tmp_path, monkeypatch) -> None:
    class FailedRuntime:
        def create_and_verify(self, spec, *, timeout_seconds):
            raise WorkspaceError("native failure")

    monkeypatch.setattr("xenosculpt.moi.workspace.MoiCylinderRuntime.for_executable", lambda _: FailedRuntime())
    root = tmp_path / "failed.msp"

    with pytest.raises(WorkspaceError, match="native failure"):
        MoiProject.create_cylinder(
            root, CylinderSpec(Decimal("1"), Decimal("1")), moi_executable="ignored"
        )

    assert not root.exists()


def test_moi_open_rejects_foreign_application_identity(tmp_path, monkeypatch) -> None:
    import sqlite3

    fake = _FakeRuntime(tmp_path)
    monkeypatch.setattr("xenosculpt.moi.workspace.MoiCylinderRuntime.for_executable", lambda _: fake)
    project = MoiProject.create_cylinder(
        tmp_path / "cylinder.msp", CylinderSpec(Decimal("0.5"), Decimal("1")), moi_executable="ignored"
    )
    with sqlite3.connect(project.database) as connection:
        connection.execute("UPDATE metadata SET value = 'comfyui' WHERE key = 'application_id'")
        connection.commit()

    with pytest.raises(WorkspaceError, match="application identity"):
        MoiProject.open(project.root)


def test_evidence_decoder_rejects_unknown_fields_and_path_escape(tmp_path, monkeypatch) -> None:
    fake = _FakeRuntime(tmp_path)
    value = asdict(fake.create_and_verify(CylinderSpec(Decimal("0.5"), Decimal("1")), timeout_seconds=1).evidence)
    value["mesh"]["path"] = f"run-artifacts/{value['stl_sha256']}.stl"
    value["unexpected"] = True
    with pytest.raises(WorkspaceError, match="evidence is invalid"):
        _decode_evidence(value, tmp_path)

    value.pop("unexpected")
    value["mesh"]["path"] = "../outside.stl"
    with pytest.raises(WorkspaceError, match="evidence is invalid"):
        _decode_evidence(value, tmp_path)
