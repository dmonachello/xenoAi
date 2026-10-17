"""Content-addressed artifacts and immutable revision history."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sqlite3
from typing import Iterator
from uuid import uuid4

from .errors import WorkspaceError
from .model import ApplicationIdentity, ArtifactInfo, Revision


_BRANCH_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )


def _json_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


class RevisionWorkspace:
    """Own content-addressed artifacts, revisions, refs, and atomic commits."""

    def __init__(self, root: Path, application: ApplicationIdentity) -> None:
        self.root = root.resolve()
        self.database = self.root / "project.sqlite3"
        self.artifacts = self.root / "artifacts"
        self.application = application

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
        finally:
            connection.close()

    def initialize_history(
        self,
        connection: sqlite3.Connection,
        *,
        source_data: bytes,
        created_at: str,
        operation: str,
        details: dict[str, object],
        message: str,
        prompt: str | None,
        metadata: dict[str, str],
    ) -> Revision:
        """Create the shared schema and its first content-addressed revision."""

        connection.row_factory = sqlite3.Row
        self.root.mkdir(parents=True, exist_ok=True)
        self.artifacts.mkdir(parents=True, exist_ok=True)
        artifact_sha = self._store_artifact(source_data)
        revision_id = self._revision_id(
            None, artifact_sha, operation, details, message, prompt
        )
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
        identity_metadata = {
            "application_id": self.application.name,
            "document_kind": self.application.document_kind,
            "artifact_suffix": self.application.artifact_suffix,
        }
        overlap = identity_metadata.keys() & metadata.keys()
        if overlap:
            raise WorkspaceError(
                f"application metadata keys are reserved: {', '.join(sorted(overlap))}"
            )
        connection.executemany(
            "INSERT INTO metadata(key, value) VALUES (?, ?)",
            {**identity_metadata, **metadata}.items(),
        )
        connection.execute(
            "INSERT INTO revisions VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                revision_id,
                None,
                artifact_sha,
                created_at,
                operation,
                message,
                prompt,
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
        row = connection.execute(
            "SELECT * FROM revisions WHERE id = ?", (revision_id,)
        ).fetchone()
        if row is None:
            raise WorkspaceError("initial revision was not recorded")
        return self._revision(row)

    def verify_application_identity(
        self,
        connection: sqlite3.Connection,
        *,
        infer_legacy: bool = False,
        allow_unbound: bool = False,
    ) -> None:
        """Bind history to one document family and reject mismatched readers."""

        expected = {
            "application_id": self.application.name,
            "document_kind": self.application.document_kind,
            "artifact_suffix": self.application.artifact_suffix,
        }
        stored = {
            row["key"]: row["value"]
            for row in connection.execute(
                "SELECT key, value FROM metadata WHERE key IN (?, ?, ?)",
                tuple(expected),
            )
        }
        if not stored and infer_legacy:
            connection.executemany(
                "INSERT INTO metadata(key, value) VALUES (?, ?)", expected.items()
            )
            return
        if not stored and allow_unbound:
            return
        if stored != expected:
            raise WorkspaceError("workspace application identity does not match")

    def _store_artifact(self, data: bytes) -> str:
        digest = sha256(data).hexdigest()
        destination = self.artifacts / f"{digest}{self.application.artifact_suffix}"
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
        path = self.artifacts / (
            f"{revision.artifact_sha256}{self.application.artifact_suffix}"
        )
        data = path.read_bytes()
        if sha256(data).hexdigest() != revision.artifact_sha256:
            raise WorkspaceError(f"artifact failed hash verification: {path}")
        return data

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
