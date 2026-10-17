"""MoI project facade over the shared immutable revision core."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import re
import shutil
import sqlite3
from uuid import uuid4

from xenosculpt.core import ApplicationIdentity, ArtifactInfo, RevisionWorkspace, WorkspaceError
from xenosculpt.mesh import StlReport, basic_mesh_valid, inspect_binary_stl

from .model import CylinderSpec, MoiEvidence, MoiInstallation, MoiStatus
from .runtime import MoiCylinderRuntime


MOI_APPLICATION = ApplicationIdentity("moi3d", "moi3d/3dm-v5", ".3dm")
_SCHEMA_VERSION = "1"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _json(value: object) -> str:
    return json.dumps(value, allow_nan=False, sort_keys=True, separators=(",", ":"))


class MoiProject(RevisionWorkspace):
    def __init__(self, root: Path) -> None:
        super().__init__(root, MOI_APPLICATION)
        self.run_artifacts = self.root / "run-artifacts"

    @classmethod
    def create_cylinder(cls, root: str | Path, spec: CylinderSpec, *, moi_executable: str | Path,
                        timeout_seconds: float = 120) -> "MoiProject":
        destination = Path(root).resolve()
        if destination.exists():
            raise WorkspaceError(f"refusing to overwrite: {destination}")
        runtime = MoiCylinderRuntime.for_executable(moi_executable)
        result = runtime.create_and_verify(spec, timeout_seconds=timeout_seconds)
        staging = destination.parent / f".{destination.name}.{uuid4().hex}.tmp"
        workspace = cls(staging)
        try:
            workspace.root.mkdir(parents=True)
            workspace.run_artifacts.mkdir()
            stl_relative = f"run-artifacts/{result.evidence.stl_sha256}.stl"
            stl_path = workspace.root / stl_relative
            stl_path.write_bytes(result.stl_data)
            evidence_value = asdict(result.evidence)
            evidence_value["mesh"]["path"] = stl_relative
            evidence_json = _json(evidence_value)
            evidence_id = sha256(evidence_json.encode()).hexdigest()
            temporary_database = workspace.root / f".project.{uuid4().hex}.tmp"
            connection = sqlite3.connect(temporary_database)
            try:
                created_at = _now()
                revision = workspace.initialize_history(
                    connection, source_data=result.native_data, created_at=created_at,
                    operation="moi-create-cylinder-v1",
                    details={"cylinder": spec.to_dict(), "evidence_id": evidence_id},
                    message="Create native MoI cylinder", prompt=None,
                    metadata={"schema_version": _SCHEMA_VERSION, "created_at": created_at},
                )
                connection.executescript("""
                    CREATE TABLE moi_evidence (
                        id TEXT PRIMARY KEY,
                        revision_id TEXT NOT NULL UNIQUE REFERENCES revisions(id),
                        evidence_sha256 TEXT NOT NULL,
                        evidence_json TEXT NOT NULL,
                        stl_relative_path TEXT NOT NULL
                    );
                """)
                connection.execute("INSERT INTO moi_evidence VALUES (?, ?, ?, ?, ?)",
                                   (evidence_id, revision.id, sha256(evidence_json.encode()).hexdigest(),
                                    evidence_json, stl_relative))
                connection.commit()
            finally:
                connection.close()
            os.replace(temporary_database, workspace.database)
            os.replace(staging, destination)
        except Exception:
            if staging.exists():
                shutil.rmtree(staging)
            raise
        return cls.open(destination)

    @classmethod
    def open(cls, root: str | Path) -> "MoiProject":
        workspace = cls(Path(root))
        if not workspace.database.is_file():
            raise WorkspaceError(f"not a project workspace: {workspace.root}")
        with workspace._connect() as connection:
            row = connection.execute("SELECT value FROM metadata WHERE key = 'schema_version'").fetchone()
            if row is None or row[0] != _SCHEMA_VERSION:
                raise WorkspaceError("unsupported or missing MoI workspace schema")
            workspace.verify_application_identity(connection)
            if connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='moi_evidence'").fetchone() is None:
                raise WorkspaceError("MoI evidence table is missing")
        return workspace

    def status(self) -> MoiStatus:
        with self._connect() as connection:
            head = self._get_revision(connection, "HEAD")
            row = connection.execute("SELECT * FROM moi_evidence WHERE revision_id = ?", (head.id,)).fetchone()
        if row is None:
            raise WorkspaceError("MoI revision evidence is missing")
        if sha256(row["evidence_json"].encode()).hexdigest() != row["evidence_sha256"] or row["id"] != row["evidence_sha256"]:
            raise WorkspaceError("stored MoI evidence failed hash verification")
        try:
            raw_evidence = json.loads(
                row["evidence_json"],
                parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
            )
        except (json.JSONDecodeError, ValueError) as error:
            raise WorkspaceError("stored MoI evidence is invalid") from error
        if not isinstance(raw_evidence, dict) or not isinstance(raw_evidence.get("mesh"), dict):
            raise WorkspaceError("stored MoI evidence is invalid")
        if raw_evidence["mesh"].get("path") != row["stl_relative_path"]:
            raise WorkspaceError("stored MoI STL evidence path is inconsistent")
        evidence = _decode_evidence(raw_evidence, self.root)
        if head.details.get("evidence_id") != row["id"]:
            raise WorkspaceError("MoI evidence is not bound to its revision")
        if evidence.native_sha256 != head.artifact_sha256:
            raise WorkspaceError("MoI evidence does not match its native revision")
        native = self._artifact_data(head)
        if len(native) != evidence.native_bytes or not native.startswith(b"3D Geometry File Format"):
            raise WorkspaceError("retained MoI native artifact length is inconsistent")
        stl_path = Path(evidence.mesh.path)
        expected_root = self.run_artifacts.resolve()
        if not stl_path.resolve().is_relative_to(expected_root):
            raise WorkspaceError("retained MoI STL path escapes run-artifacts")
        actual = inspect_binary_stl(stl_path)
        if actual.sha256 != evidence.stl_sha256 or actual.bytes != evidence.stl_bytes or not basic_mesh_valid(actual):
            raise WorkspaceError("retained MoI STL failed verification")
        cylinder_value = head.details.get("cylinder")
        if not isinstance(cylinder_value, dict):
            raise WorkspaceError("MoI revision cylinder details are invalid")
        cylinder = CylinderSpec.from_dict(cylinder_value)
        if sha256(_json(cylinder.to_dict()).encode()).hexdigest() != evidence.request_sha256:
            raise WorkspaceError("MoI evidence request does not match its revision")
        if evidence.mesh.sha256 != evidence.stl_sha256 or evidence.mesh.bytes != evidence.stl_bytes:
            raise WorkspaceError("stored MoI mesh report is inconsistent")
        recorded_mesh = asdict(evidence.mesh)
        actual_mesh = asdict(actual)
        recorded_mesh.pop("path")
        actual_mesh.pop("path")
        if recorded_mesh != actual_mesh:
            raise WorkspaceError("retained MoI STL report does not match the mesh")
        evidence = MoiEvidence(evidence.schema, evidence.installation, evidence.request_sha256,
                               evidence.create_script_sha256, evidence.reopen_script_sha256,
                               evidence.native_sha256, evidence.native_bytes, evidence.stl_sha256,
                               evidence.stl_bytes, evidence.create_seconds, evidence.reopen_seconds, actual)
        return MoiStatus(str(self.root), self.application.name, self.application.document_kind, head, cylinder, evidence)

    def export_stl(self, destination: str | Path) -> ArtifactInfo:
        status = self.status()
        output = Path(destination)
        if output.exists():
            raise WorkspaceError(f"refusing to overwrite: {output}")
        data = Path(status.evidence.mesh.path).read_bytes()
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("xb") as stream:
            stream.write(data)
        return ArtifactInfo(str(output), len(data), status.evidence.stl_sha256, status.head.id)


def _decode_evidence(value: object, root: Path) -> MoiEvidence:
    try:
        evidence_keys = {
            "schema", "installation", "request_sha256", "create_script_sha256",
            "reopen_script_sha256", "native_sha256", "native_bytes", "stl_sha256",
            "stl_bytes", "create_seconds", "reopen_seconds", "mesh",
        }
        mesh_keys = set(StlReport.__dataclass_fields__)
        if not isinstance(value, dict) or set(value) != evidence_keys or value.get("schema") != "xenosculpt-moi-cylinder-evidence/v1":
            raise ValueError
        installation_value = value["installation"]
        if not isinstance(installation_value, dict) or set(installation_value) != {"executable", "file_version", "executable_sha256"}:
            raise ValueError
        installation = MoiInstallation(**installation_value)
        if not installation.executable or installation.file_version != "4.0.2020.1222":
            raise ValueError
        for digest in (installation.executable_sha256, value["request_sha256"], value["create_script_sha256"],
                       value["reopen_script_sha256"], value["native_sha256"], value["stl_sha256"]):
            if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
                raise ValueError
        if type(value["native_bytes"]) is not int or value["native_bytes"] <= 0 or type(value["stl_bytes"]) is not int or value["stl_bytes"] <= 0:
            raise ValueError
        if any(type(value[field]) not in (int, float) or not math.isfinite(value[field]) or value[field] < 0
               for field in ("create_seconds", "reopen_seconds")):
            raise ValueError
        if not isinstance(value["mesh"], dict) or set(value["mesh"]) != mesh_keys:
            raise ValueError
        mesh_value = dict(value["mesh"])
        if not isinstance(mesh_value["path"], str):
            raise ValueError
        relative = Path(mesh_value["path"])
        if relative.is_absolute() or ".." in relative.parts or relative.parts != ("run-artifacts", f'{value["stl_sha256"]}.stl'):
            raise ValueError
        mesh_value["path"] = str(root / relative)
        for field in ("bounds_min", "bounds_max", "dimensions"):
            if not isinstance(mesh_value[field], list) or len(mesh_value[field]) != 3 or any(type(item) not in (int, float) or not math.isfinite(item) for item in mesh_value[field]):
                raise ValueError
            mesh_value[field] = tuple(mesh_value[field])
        for field in ("bytes", "triangle_count", "degenerate_triangles", "boundary_edges", "non_manifold_edges", "inconsistent_winding_edges", "connected_components"):
            if type(mesh_value[field]) is not int or mesh_value[field] < 0:
                raise ValueError
        for field in ("max_dimension", "signed_volume"):
            if type(mesh_value[field]) not in (int, float) or not math.isfinite(mesh_value[field]):
                raise ValueError
        if not isinstance(mesh_value["sha256"], str) or re.fullmatch(r"[0-9a-f]{64}", mesh_value["sha256"]) is None:
            raise ValueError
        mesh = StlReport(**mesh_value)
        return MoiEvidence(value["schema"], installation, value["request_sha256"],
                           value["create_script_sha256"], value["reopen_script_sha256"],
                           value["native_sha256"], value["native_bytes"], value["stl_sha256"],
                           value["stl_bytes"], value["create_seconds"], value["reopen_seconds"], mesh)
    except (KeyError, TypeError, ValueError) as error:
        raise WorkspaceError("stored MoI evidence is invalid") from error
