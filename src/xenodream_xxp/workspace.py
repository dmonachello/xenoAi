"""Persistent revision workspaces for native XenoDream artifacts."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sqlite3
from typing import Iterator
from uuid import uuid4

from .diffing import diff_documents
from .document import KeyValueRecord, parse_bytes
from .generator import Vector3
from .mutation import (
    CenteredRowMutation,
    MutationResult,
    ObjectMutation,
    SeededVariation,
    VerifiedOperation,
    apply_verified_mutation,
)


class WorkspaceError(ValueError):
    """A workspace operation would violate revision or artifact invariants."""


@dataclass(frozen=True, slots=True)
class FabricationConstraints:
    process: str | None = None
    build_volume_mm: Vector3 | None = None
    min_feature_mm: Decimal | None = None

    def __post_init__(self) -> None:
        if self.process is not None and (
            not isinstance(self.process, str) or not self.process.strip()
        ):
            raise TypeError("process must be a non-empty string or None")
        if self.build_volume_mm is not None:
            if not isinstance(self.build_volume_mm, Vector3):
                raise TypeError("build_volume_mm must be Vector3 or None")
            if any(
                value <= 0
                for value in (
                    self.build_volume_mm.x,
                    self.build_volume_mm.y,
                    self.build_volume_mm.z,
                )
            ):
                raise WorkspaceError("build volume dimensions must be positive")
        if self.min_feature_mm is not None:
            if not isinstance(self.min_feature_mm, Decimal):
                raise TypeError("min_feature_mm must be Decimal or None")
            if not self.min_feature_mm.is_finite() or self.min_feature_mm <= 0:
                raise WorkspaceError("minimum feature size must be finite and positive")


@dataclass(frozen=True, slots=True)
class Revision:
    id: str
    parent_id: str | None
    artifact_sha256: str
    created_at: str
    operation: str
    message: str
    prompt: str | None
    details: dict[str, object]


@dataclass(frozen=True, slots=True)
class WorkspaceStatus:
    root: str
    current_branch: str | None
    branches: dict[str, str]
    head: Revision
    artifact_path: str
    xdx_version: str
    constraints: FabricationConstraints


@dataclass(frozen=True, slots=True)
class ApplyResult:
    revision: Revision
    created: bool
    mutation: MutationResult | None


@dataclass(frozen=True, slots=True)
class ArtifactInfo:
    path: str
    bytes: int
    sha256: str
    revision_id: str


_SCHEMA_VERSION = "1"
_DATABASE_NAME = "project.sqlite3"
_BRANCH_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _json_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _constraints_to_dict(value: FabricationConstraints) -> dict[str, object]:
    return {
        "process": value.process,
        "build_volume_mm": None
        if value.build_volume_mm is None
        else [
            str(value.build_volume_mm.x),
            str(value.build_volume_mm.y),
            str(value.build_volume_mm.z),
        ],
        "min_feature_mm": None
        if value.min_feature_mm is None
        else str(value.min_feature_mm),
    }


def _constraints_from_dict(value: dict[str, object]) -> FabricationConstraints:
    raw_volume = value.get("build_volume_mm")
    volume = None
    if raw_volume is not None:
        if not isinstance(raw_volume, list) or len(raw_volume) != 3:
            raise WorkspaceError("workspace has invalid build-volume metadata")
        volume = Vector3(*(Decimal(str(item)) for item in raw_volume))
    raw_feature = value.get("min_feature_mm")
    return FabricationConstraints(
        process=value.get("process") if isinstance(value.get("process"), str) else None,
        build_volume_mm=volume,
        min_feature_mm=None if raw_feature is None else Decimal(str(raw_feature)),
    )


def _operation_details(operation: VerifiedOperation) -> dict[str, object]:
    def vector(value: Vector3 | None) -> list[str] | None:
        return None if value is None else [str(value.x), str(value.y), str(value.z)]

    if isinstance(operation, ObjectMutation):
        return {
            "type": "object-mutation",
            "object_name": operation.object_name,
            "scale": vector(operation.scale),
            "rotation": vector(operation.rotation),
            "position": vector(operation.position),
            "color_density": None
            if operation.color_density is None
            else str(operation.color_density),
            "face_warp": None
            if operation.face_warp is None
            else str(operation.face_warp),
        }
    if isinstance(operation, CenteredRowMutation):
        return {
            "type": "centered-row",
            "spacing": str(operation.spacing),
            "center": vector(operation.center),
        }
    if isinstance(operation, SeededVariation):
        return {
            "type": "seeded-variation-v1",
            "seed": operation.seed,
            "strength": str(operation.strength),
        }
    raise TypeError("unsupported verified operation")


def _header_value(data: bytes, key: bytes) -> str:
    document = parse_bytes(data)
    if document.to_bytes() != data:
        raise WorkspaceError("artifact failed exact parser round trip")
    matches = [
        record.value
        for record in document.records
        if isinstance(record, KeyValueRecord)
        and record.section == b"Header"
        and record.section_occurrence == 0
        and record.key == key
    ]
    if len(matches) != 1:
        raise WorkspaceError(f"artifact must contain one Header.{key.decode()} value")
    try:
        return matches[0].decode("ascii")
    except UnicodeDecodeError as error:
        raise WorkspaceError(f"Header.{key.decode()} must be ASCII") from error


class ProjectWorkspace:
    """Own the revision graph and content-addressed native artifacts."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.database = self.root / _DATABASE_NAME
        self.artifacts = self.root / "artifacts"

    @classmethod
    def create(
        cls,
        root: str | Path,
        source: str | Path,
        constraints: FabricationConstraints | None = None,
    ) -> ProjectWorkspace:
        workspace = cls(Path(root))
        if workspace.database.exists():
            raise WorkspaceError(f"workspace already exists: {workspace.root}")
        source_path = Path(source).resolve()
        data = source_path.read_bytes()
        if _header_value(data, b"Program") != "XDX":
            raise WorkspaceError("source must be an XDX project")
        version = _header_value(data, b"Progversion")
        policy = constraints if constraints is not None else FabricationConstraints()

        workspace.root.mkdir(parents=True, exist_ok=True)
        workspace.artifacts.mkdir(parents=True, exist_ok=True)
        artifact_sha = workspace._store_artifact(data)
        details = {"source_sha256": artifact_sha}
        revision_id = workspace._revision_id(
            None,
            artifact_sha,
            "init",
            details,
            "Import initial native project",
            None,
        )
        created_at = _now()
        temporary_database = workspace.root / f".{_DATABASE_NAME}.{uuid4().hex}.tmp"
        try:
            connection = sqlite3.connect(temporary_database)
            try:
                connection.executescript(
                    """
                    PRAGMA foreign_keys = ON;
                    CREATE TABLE metadata (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL
                    );
                    CREATE TABLE revisions (
                        id TEXT PRIMARY KEY,
                        parent_id TEXT REFERENCES revisions(id),
                        artifact_sha256 TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        operation TEXT NOT NULL,
                        message TEXT NOT NULL,
                        prompt TEXT,
                        details_json TEXT NOT NULL
                    );
                    CREATE TABLE branches (
                        name TEXT PRIMARY KEY,
                        revision_id TEXT NOT NULL REFERENCES revisions(id)
                    );
                    CREATE TABLE state (
                        singleton INTEGER PRIMARY KEY CHECK(singleton = 1),
                        current_branch TEXT REFERENCES branches(name),
                        detached_revision TEXT REFERENCES revisions(id)
                    );
                    """
                )
                metadata = {
                    "schema_version": _SCHEMA_VERSION,
                    "created_at": created_at,
                    "source_path": str(source_path),
                    "source_sha256": artifact_sha,
                    "xdx_version": version,
                    "constraints_json": _json_bytes(
                        _constraints_to_dict(policy)
                    ).decode(),
                }
                connection.executemany(
                    "INSERT INTO metadata(key, value) VALUES (?, ?)",
                    metadata.items(),
                )
                connection.execute(
                    "INSERT INTO revisions VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        revision_id,
                        None,
                        artifact_sha,
                        created_at,
                        "init",
                        "Import initial native project",
                        None,
                        _json_bytes(details).decode(),
                    ),
                )
                connection.execute(
                    "INSERT INTO branches(name, revision_id) VALUES ('main', ?)",
                    (revision_id,),
                )
                connection.execute(
                    "INSERT INTO state(singleton, current_branch, detached_revision) "
                    "VALUES (1, 'main', NULL)"
                )
                connection.commit()
            finally:
                connection.close()
            os.replace(temporary_database, workspace.database)
        finally:
            if temporary_database.exists():
                temporary_database.unlink()
        return workspace

    @classmethod
    def open(cls, root: str | Path) -> ProjectWorkspace:
        workspace = cls(Path(root))
        if not workspace.database.is_file():
            raise WorkspaceError(f"not a project workspace: {workspace.root}")
        with workspace._connect() as connection:
            row = connection.execute(
                "SELECT value FROM metadata WHERE key = 'schema_version'"
            ).fetchone()
            if row is None or row[0] != _SCHEMA_VERSION:
                raise WorkspaceError("unsupported or missing workspace schema")
        return workspace

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
        finally:
            connection.close()

    def _store_artifact(self, data: bytes) -> str:
        digest = sha256(data).hexdigest()
        destination = self.artifacts / f"{digest}.xxp"
        if destination.exists():
            if destination.read_bytes() != data:
                raise WorkspaceError("artifact hash collision or corrupted artifact")
            return digest
        temporary = self.artifacts / f".{digest}.{uuid4().hex}.tmp"
        try:
            with temporary.open("xb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, destination)
        finally:
            if temporary.exists():
                temporary.unlink()
        return digest

    @staticmethod
    def _revision_id(
        parent_id: str | None,
        artifact_sha: str,
        operation: str,
        details: dict[str, object],
        message: str,
        prompt: str | None,
    ) -> str:
        return sha256(
            _json_bytes(
                {
                    "parent": parent_id,
                    "artifact_sha256": artifact_sha,
                    "operation": operation,
                    "details": details,
                    "message": message,
                    "prompt": prompt,
                }
            )
        ).hexdigest()

    @staticmethod
    def _revision(row: sqlite3.Row) -> Revision:
        return Revision(
            id=row["id"],
            parent_id=row["parent_id"],
            artifact_sha256=row["artifact_sha256"],
            created_at=row["created_at"],
            operation=row["operation"],
            message=row["message"],
            prompt=row["prompt"],
            details=json.loads(row["details_json"]),
        )

    def _head_id(self, connection: sqlite3.Connection) -> tuple[str, str | None]:
        row = connection.execute(
            "SELECT current_branch, detached_revision FROM state WHERE singleton = 1"
        ).fetchone()
        if row is None:
            raise WorkspaceError("workspace state is missing")
        branch = row["current_branch"]
        if branch is not None:
            target = connection.execute(
                "SELECT revision_id FROM branches WHERE name = ?", (branch,)
            ).fetchone()
            if target is None:
                raise WorkspaceError("current branch is missing")
            return target["revision_id"], branch
        if row["detached_revision"] is None:
            raise WorkspaceError("workspace HEAD has no target")
        return row["detached_revision"], None

    def _resolve(self, connection: sqlite3.Connection, ref: str) -> str:
        if ref == "HEAD":
            return self._head_id(connection)[0]
        branch = connection.execute(
            "SELECT revision_id FROM branches WHERE name = ?", (ref,)
        ).fetchone()
        if branch is not None:
            return branch["revision_id"]
        matches = connection.execute(
            "SELECT id FROM revisions WHERE id LIKE ? ORDER BY id", (f"{ref}%",)
        ).fetchall()
        if len(matches) != 1:
            raise WorkspaceError(f"reference {ref!r} matched {len(matches)} revisions")
        return matches[0]["id"]

    def _get_revision(self, connection: sqlite3.Connection, ref: str) -> Revision:
        revision_id = self._resolve(connection, ref)
        row = connection.execute(
            "SELECT * FROM revisions WHERE id = ?", (revision_id,)
        ).fetchone()
        if row is None:
            raise WorkspaceError(f"missing revision {revision_id}")
        return self._revision(row)

    def _artifact_data(self, revision: Revision) -> bytes:
        path = self.artifacts / f"{revision.artifact_sha256}.xxp"
        data = path.read_bytes()
        if sha256(data).hexdigest() != revision.artifact_sha256:
            raise WorkspaceError(f"artifact failed hash verification: {path}")
        return data

    def status(self) -> WorkspaceStatus:
        with self._connect() as connection:
            revision = self._get_revision(connection, "HEAD")
            _, branch = self._head_id(connection)
            version = connection.execute(
                "SELECT value FROM metadata WHERE key = 'xdx_version'"
            ).fetchone()["value"]
            raw_constraints = connection.execute(
                "SELECT value FROM metadata WHERE key = 'constraints_json'"
            ).fetchone()["value"]
            branches = {
                row["name"]: row["revision_id"]
                for row in connection.execute(
                    "SELECT name, revision_id FROM branches ORDER BY name"
                ).fetchall()
            }
        return WorkspaceStatus(
            root=str(self.root),
            current_branch=branch,
            branches=branches,
            head=revision,
            artifact_path=str(self.artifacts / f"{revision.artifact_sha256}.xxp"),
            xdx_version=version,
            constraints=_constraints_from_dict(json.loads(raw_constraints)),
        )

    def _record_revision(
        self,
        data: bytes,
        operation: str,
        details: dict[str, object],
        message: str,
        prompt: str | None,
        expected_parent: str,
    ) -> Revision:
        artifact_sha = self._store_artifact(data)
        revision_id = self._revision_id(
            expected_parent, artifact_sha, operation, details, message, prompt
        )
        created_at = _now()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            current, branch = self._head_id(connection)
            if current != expected_parent:
                raise WorkspaceError("workspace HEAD changed during the operation")
            connection.execute(
                "INSERT OR IGNORE INTO revisions VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    revision_id,
                    expected_parent,
                    artifact_sha,
                    created_at,
                    operation,
                    message,
                    prompt,
                    _json_bytes(details).decode(),
                ),
            )
            if branch is None:
                connection.execute(
                    "UPDATE state SET detached_revision = ? WHERE singleton = 1",
                    (revision_id,),
                )
            else:
                connection.execute(
                    "UPDATE branches SET revision_id = ? WHERE name = ?",
                    (revision_id, branch),
                )
            row = connection.execute(
                "SELECT * FROM revisions WHERE id = ?", (revision_id,)
            ).fetchone()
            connection.commit()
        if row is None:
            raise WorkspaceError("revision was not recorded")
        return self._revision(row)

    def apply(
        self,
        operation: VerifiedOperation,
        *,
        message: str,
        prompt: str | None = None,
    ) -> ApplyResult:
        if not isinstance(message, str) or not message.strip():
            raise WorkspaceError("message must be a non-empty string")
        with self._connect() as connection:
            parent = self._get_revision(connection, "HEAD")
        source = self._artifact_data(parent)
        result = apply_verified_mutation(source, operation)
        if not result.changed:
            return ApplyResult(parent, False, result)
        details = _operation_details(operation)
        revision = self._record_revision(
            result.data,
            str(details["type"]),
            details,
            message.strip(),
            prompt,
            parent.id,
        )
        return ApplyResult(revision, True, result)

    def import_artifact(
        self,
        source: str | Path,
        *,
        message: str,
        prompt: str | None = None,
    ) -> ApplyResult:
        if not isinstance(message, str) or not message.strip():
            raise WorkspaceError("message must be a non-empty string")
        source_path = Path(source).resolve()
        data = source_path.read_bytes()
        if _header_value(data, b"Program") != "XDX":
            raise WorkspaceError("import must be an XDX project")
        with self._connect() as connection:
            parent = self._get_revision(connection, "HEAD")
        if data == self._artifact_data(parent):
            return ApplyResult(parent, False, None)
        details = {"type": "manual-import", "artifact_sha256": sha256(data).hexdigest()}
        revision = self._record_revision(
            data, "manual-import", details, message.strip(), prompt, parent.id
        )
        return ApplyResult(revision, True, None)

    def create_branch(
        self, name: str, *, from_ref: str = "HEAD", checkout: bool = False
    ) -> Revision:
        if not _valid_branch_name(name):
            raise WorkspaceError(
                "branch names may contain letters, digits, dot, underscore, and hyphen"
            )
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            revision = self._get_revision(connection, from_ref)
            try:
                connection.execute(
                    "INSERT INTO branches(name, revision_id) VALUES (?, ?)",
                    (name, revision.id),
                )
            except sqlite3.IntegrityError as error:
                raise WorkspaceError(f"branch already exists: {name}") from error
            if checkout:
                connection.execute(
                    "UPDATE state SET current_branch = ?, detached_revision = NULL "
                    "WHERE singleton = 1",
                    (name,),
                )
            connection.commit()
        return revision

    def checkout(self, ref: str) -> Revision:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            branch = connection.execute(
                "SELECT revision_id FROM branches WHERE name = ?", (ref,)
            ).fetchone()
            if branch is not None:
                revision = self._get_revision(connection, ref)
                connection.execute(
                    "UPDATE state SET current_branch = ?, detached_revision = NULL "
                    "WHERE singleton = 1",
                    (ref,),
                )
            else:
                revision = self._get_revision(connection, ref)
                connection.execute(
                    "UPDATE state SET current_branch = NULL, detached_revision = ? "
                    "WHERE singleton = 1",
                    (revision.id,),
                )
            connection.commit()
        return revision

    def history(self, ref: str = "HEAD") -> tuple[Revision, ...]:
        with self._connect() as connection:
            revision = self._get_revision(connection, ref)
            history: list[Revision] = []
            while True:
                history.append(revision)
                if revision.parent_id is None:
                    break
                revision = self._get_revision(connection, revision.parent_id)
        return tuple(history)

    def compare(self, before: str, after: str) -> list[dict[str, object]]:
        with self._connect() as connection:
            before_revision = self._get_revision(connection, before)
            after_revision = self._get_revision(connection, after)
        return diff_documents(
            parse_bytes(self._artifact_data(before_revision)),
            parse_bytes(self._artifact_data(after_revision)),
        )

    def export(self, destination: str | Path, ref: str = "HEAD") -> ArtifactInfo:
        destination_path = Path(destination)
        if destination_path.exists():
            raise WorkspaceError(f"refusing to overwrite: {destination_path}")
        with self._connect() as connection:
            revision = self._get_revision(connection, ref)
        data = self._artifact_data(revision)
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        with destination_path.open("xb") as stream:
            stream.write(data)
        return ArtifactInfo(
            path=str(destination_path),
            bytes=len(data),
            sha256=revision.artifact_sha256,
            revision_id=revision.id,
        )


def _valid_branch_name(value: str) -> bool:
    if not isinstance(value, str) or not value or value in {"HEAD", ".", ".."}:
        return False
    return _BRANCH_PATTERN.fullmatch(value) is not None
