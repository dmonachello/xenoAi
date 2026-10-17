"""XenoDream project state, native validation, and fabrication evidence."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sqlite3
from uuid import uuid4

from .adapter import XENODREAM_APPLICATION, XenoDreamArtifactAdapter
from .errors import WorkspaceError
from .fabrication import (
    ASSESSMENT_SCHEMA,
    WORKSPACE_POLICY,
    FabricationAssessment,
    FabricationCheck,
    FabricationConstraints,
    FabricationVerdict,
    constraints_from_dict,
    constraints_to_dict,
    derive_fabrication_verdict,
    evaluate_fabrication,
    fabrication_assessment_from_dict,
    fabrication_assessment_to_dict,
    fabrication_check_to_dict,
)
from .mesh import StlReport, basic_mesh_valid, inspect_binary_stl
from .native_export import (
    DEFAULT_XENODREAM_EXECUTABLE,
    MeshExportSettings,
    run_export,
)
from .mutation import (
    MutationResult,
    VerifiedOperation,
)
from .planning import (
    MutationPlan,
    plan_provenance_to_dict,
    validate_plan_provenance,
)
from xenosculpt.core.model import ApplyResult, ArtifactInfo, Revision
from xenosculpt.core.workspace import RevisionWorkspace


@dataclass(frozen=True, slots=True)
class WorkspaceStatus:
    root: str
    current_branch: str | None
    branches: dict[str, str]
    head: Revision
    artifact_path: str
    xdx_version: str
    constraints: FabricationConstraints
    latest_validation: NativeValidation | None
    latest_fabrication_assessment: FabricationAssessment | None


@dataclass(frozen=True, slots=True)
class NativeValidation:
    id: str
    revision_id: str
    created_at: str
    outcome: str
    settings: dict[str, object]
    report: dict[str, object]
    mesh_path: str | None
    mesh_sha256: str | None
    native_model_valid: bool
    evaluates_to_3d: bool
    basic_mesh_valid: bool
    fabrication_suitable: bool


_SCHEMA_VERSION = "3"
_DATABASE_NAME = "project.sqlite3"
_ASSESSMENT_SELECT = (
    "SELECT assessment.*, "
    "validation.revision_id AS evidence_revision_id, "
    "validation.mesh_sha256 AS evidence_mesh_sha256, "
    "revision.artifact_sha256 AS evidence_artifact_sha256 "
    "FROM fabrication_assessments AS assessment "
    "JOIN validations AS validation ON validation.id = assessment.validation_id "
    "JOIN revisions AS revision ON revision.id = validation.revision_id "
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _json_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _constraints_to_dict(value: FabricationConstraints) -> dict[str, object]:
    return constraints_to_dict(value)


def _constraints_from_dict(value: dict[str, object]) -> FabricationConstraints:
    return constraints_from_dict(value)


class ProjectWorkspace(RevisionWorkspace):
    """Add XenoDream behavior and evidence to the revision workspace."""

    adapter = XenoDreamArtifactAdapter()

    def __init__(self, root: Path) -> None:
        super().__init__(root, XENODREAM_APPLICATION)
        self.meshes = self.root / "meshes"
        self.validation_runs = self.root / "validation-runs"

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
        descriptor = workspace.adapter.inspect(data)
        version = descriptor.xdx_version
        policy = constraints if constraints is not None else FabricationConstraints()

        workspace.root.mkdir(parents=True, exist_ok=True)
        workspace.meshes.mkdir(parents=True, exist_ok=True)
        workspace.validation_runs.mkdir(parents=True, exist_ok=True)
        artifact_sha = sha256(data).hexdigest()
        details = {"source_sha256": artifact_sha}
        created_at = _now()
        temporary_database = workspace.root / f".{_DATABASE_NAME}.{uuid4().hex}.tmp"
        try:
            connection = sqlite3.connect(temporary_database)
            try:
                workspace.initialize_history(
                    connection,
                    source_data=data,
                    created_at=created_at,
                    operation="init",
                    details=details,
                    message="Import initial native project",
                    prompt=None,
                    metadata={
                        "schema_version": _SCHEMA_VERSION,
                        "created_at": created_at,
                        "source_path": str(source_path),
                        "source_sha256": artifact_sha,
                        "xdx_version": version,
                        "constraints_json": _json_bytes(
                            _constraints_to_dict(policy)
                        ).decode(),
                    },
                )
                connection.executescript(
                    """
                    CREATE TABLE validations (
                        id TEXT PRIMARY KEY,
                        request_key TEXT NOT NULL,
                        revision_id TEXT NOT NULL REFERENCES revisions(id),
                        created_at TEXT NOT NULL,
                        outcome TEXT NOT NULL,
                        settings_json TEXT NOT NULL,
                        report_json TEXT NOT NULL,
                        mesh_sha256 TEXT,
                        native_model_valid INTEGER NOT NULL,
                        evaluates_to_3d INTEGER NOT NULL,
                        basic_mesh_valid INTEGER NOT NULL,
                        fabrication_suitable INTEGER NOT NULL
                    );
                    CREATE INDEX validations_revision_created
                    ON validations(revision_id, created_at DESC);
                    CREATE TABLE fabrication_assessments (
                        id TEXT PRIMARY KEY,
                        request_key TEXT NOT NULL UNIQUE,
                        validation_id TEXT NOT NULL REFERENCES validations(id),
                        created_at TEXT NOT NULL,
                        policy_json TEXT NOT NULL,
                        constraints_json TEXT NOT NULL,
                        result_json TEXT NOT NULL
                    );
                    CREATE INDEX fabrication_assessments_validation_created
                    ON fabrication_assessments(validation_id, created_at DESC, id DESC);
                    """
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
            if row is None or row[0] not in {"1", "2", _SCHEMA_VERSION}:
                raise WorkspaceError("unsupported or missing workspace schema")
            workspace.verify_application_identity(connection, allow_unbound=True)
            if row[0] == "1":
                connection.executescript(
                    """
                    BEGIN IMMEDIATE;
                    CREATE TABLE validations (
                        id TEXT PRIMARY KEY,
                        request_key TEXT NOT NULL,
                        revision_id TEXT NOT NULL REFERENCES revisions(id),
                        created_at TEXT NOT NULL,
                        outcome TEXT NOT NULL,
                        settings_json TEXT NOT NULL,
                        report_json TEXT NOT NULL,
                        mesh_sha256 TEXT,
                        native_model_valid INTEGER NOT NULL,
                        evaluates_to_3d INTEGER NOT NULL,
                        basic_mesh_valid INTEGER NOT NULL,
                        fabrication_suitable INTEGER NOT NULL
                    );
                    CREATE INDEX validations_revision_created
                    ON validations(revision_id, created_at DESC);
                    UPDATE metadata SET value = '2' WHERE key = 'schema_version';
                    COMMIT;
                    """
                )
                row = ("2",)
            if row[0] == "2":
                connection.executescript(
                    """
                    BEGIN IMMEDIATE;
                    CREATE TABLE fabrication_assessments (
                        id TEXT PRIMARY KEY,
                        request_key TEXT NOT NULL UNIQUE,
                        validation_id TEXT NOT NULL REFERENCES validations(id),
                        created_at TEXT NOT NULL,
                        policy_json TEXT NOT NULL,
                        constraints_json TEXT NOT NULL,
                        result_json TEXT NOT NULL
                    );
                    CREATE INDEX fabrication_assessments_validation_created
                    ON fabrication_assessments(validation_id, created_at DESC, id DESC);
                    UPDATE metadata SET value = '3' WHERE key = 'schema_version';
                    COMMIT;
                    """
                )
            workspace.verify_application_identity(connection, infer_legacy=True)
            connection.commit()
        workspace.meshes.mkdir(exist_ok=True)
        workspace.validation_runs.mkdir(exist_ok=True)
        return workspace

    def _validation(self, row: sqlite3.Row) -> NativeValidation:
        mesh_sha = row["mesh_sha256"]
        return NativeValidation(
            id=row["id"],
            revision_id=row["revision_id"],
            created_at=row["created_at"],
            outcome=row["outcome"],
            settings=json.loads(row["settings_json"]),
            report=json.loads(row["report_json"]),
            mesh_path=(
                str(self.meshes / f"{mesh_sha}.stl") if mesh_sha is not None else None
            ),
            mesh_sha256=mesh_sha,
            native_model_valid=bool(row["native_model_valid"]),
            evaluates_to_3d=bool(row["evaluates_to_3d"]),
            basic_mesh_valid=bool(row["basic_mesh_valid"]),
            fabrication_suitable=bool(row["fabrication_suitable"]),
        )

    def _latest_validation(
        self, connection: sqlite3.Connection, revision_id: str
    ) -> NativeValidation | None:
        row = connection.execute(
            "SELECT * FROM validations WHERE revision_id = ? "
            "ORDER BY created_at DESC, id DESC LIMIT 1",
            (revision_id,),
        ).fetchone()
        return None if row is None else self._validation(row)

    @staticmethod
    def _assessment_request(
        assessment: FabricationAssessment,
    ) -> dict[str, object]:
        return {
            "schema": assessment.schema,
            "policy": {
                "name": assessment.policy.name,
                "version": assessment.policy.version,
            },
            "revision_id": assessment.revision_id,
            "artifact_sha256": assessment.artifact_sha256,
            "validation_id": assessment.validation_id,
            "mesh_sha256": assessment.mesh_sha256,
            "constraints": _constraints_to_dict(assessment.constraints),
        }

    @staticmethod
    def _assessment_id(
        request: dict[str, object],
        verdict: FabricationVerdict,
        checks: tuple[FabricationCheck, ...],
    ) -> str:
        identity_payload = {
            "request": request,
            "verdict": verdict.value,
            "checks": [fabrication_check_to_dict(item) for item in checks],
        }
        return sha256(_json_bytes(identity_payload)).hexdigest()

    @classmethod
    def _fabrication_assessment(cls, row: sqlite3.Row) -> FabricationAssessment:
        assessment = fabrication_assessment_from_dict(json.loads(row["result_json"]))
        request = cls._assessment_request(assessment)
        stored_policy = json.loads(row["policy_json"])
        stored_constraints = json.loads(row["constraints_json"])
        provenance_matches = all(
            (
                row["id"] == assessment.id,
                row["validation_id"] == assessment.validation_id,
                stored_policy == request["policy"],
                stored_constraints == request["constraints"],
                row["evidence_revision_id"] == assessment.revision_id,
                row["evidence_mesh_sha256"] == assessment.mesh_sha256,
                row["evidence_artifact_sha256"] == assessment.artifact_sha256,
                row["request_key"] == sha256(_json_bytes(request)).hexdigest(),
                assessment.id
                == cls._assessment_id(
                    request,
                    assessment.verdict,
                    assessment.checks,
                ),
            )
        )
        if not provenance_matches:
            raise WorkspaceError("fabrication assessment provenance is inconsistent")
        return assessment

    def _latest_fabrication_assessment(
        self, connection: sqlite3.Connection, revision_id: str
    ) -> FabricationAssessment | None:
        row = connection.execute(
            _ASSESSMENT_SELECT
            + "WHERE validation.revision_id = ? "
            + "ORDER BY assessment.created_at DESC, assessment.id DESC LIMIT 1",
            (revision_id,),
        ).fetchone()
        return None if row is None else self._fabrication_assessment(row)

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
            latest_validation = self._latest_validation(connection, revision.id)
            latest_assessment = self._latest_fabrication_assessment(
                connection, revision.id
            )
        return WorkspaceStatus(
            root=str(self.root),
            current_branch=branch,
            branches=branches,
            head=revision,
            artifact_path=str(self.artifacts / f"{revision.artifact_sha256}.xxp"),
            xdx_version=version,
            constraints=_constraints_from_dict(json.loads(raw_constraints)),
            latest_validation=latest_validation,
            latest_fabrication_assessment=latest_assessment,
        )

    def assess_fabrication(
        self,
        *,
        ref: str = "HEAD",
        validation_id: str | None = None,
    ) -> FabricationAssessment:
        """Assess an exact retained validation mesh without changing HEAD."""

        if validation_id is not None and (
            not isinstance(validation_id, str)
            or re.fullmatch(r"[0-9a-f]{64}", validation_id) is None
        ):
            raise WorkspaceError(
                "validation ID must be 64 lowercase hexadecimal characters"
            )
        with self._connect() as connection:
            revision = self._get_revision(connection, ref)
            if validation_id is None:
                row = connection.execute(
                    "SELECT * FROM validations WHERE revision_id = ? "
                    "AND outcome = 'succeeded' AND mesh_sha256 IS NOT NULL "
                    "ORDER BY created_at DESC, id DESC LIMIT 1",
                    (revision.id,),
                ).fetchone()
            else:
                row = connection.execute(
                    "SELECT * FROM validations WHERE id = ? AND revision_id = ? "
                    "AND outcome = 'succeeded' AND mesh_sha256 IS NOT NULL",
                    (validation_id, revision.id),
                ).fetchone()
            raw_constraints = connection.execute(
                "SELECT value FROM metadata WHERE key = 'constraints_json'"
            ).fetchone()["value"]
        if row is None:
            raise WorkspaceError(
                "no successful mesh-bearing validation matches the selected revision"
            )
        validation = self._validation(row)
        if validation.mesh_sha256 is None:
            raise WorkspaceError("selected validation has no retained mesh")
        mesh_path = self.meshes / f"{validation.mesh_sha256}.stl"
        if not mesh_path.is_file():
            raise WorkspaceError(f"retained validation mesh is missing: {mesh_path}")
        mesh_bytes = mesh_path.read_bytes()
        if sha256(mesh_bytes).hexdigest() != validation.mesh_sha256:
            raise WorkspaceError(f"mesh failed hash verification: {mesh_path}")
        mesh = inspect_binary_stl(mesh_path)
        if mesh.sha256 != validation.mesh_sha256:
            raise WorkspaceError("mesh inspection identity disagrees with validation")

        constraints = _constraints_from_dict(json.loads(raw_constraints))
        request = {
            "schema": ASSESSMENT_SCHEMA,
            "policy": {
                "name": WORKSPACE_POLICY.name,
                "version": WORKSPACE_POLICY.version,
            },
            "revision_id": revision.id,
            "artifact_sha256": revision.artifact_sha256,
            "validation_id": validation.id,
            "mesh_sha256": validation.mesh_sha256,
            "constraints": _constraints_to_dict(constraints),
        }
        request_key = sha256(_json_bytes(request)).hexdigest()
        with self._connect() as connection:
            cached = connection.execute(
                _ASSESSMENT_SELECT + "WHERE assessment.request_key = ?",
                (request_key,),
            ).fetchone()
        if cached is not None:
            return self._fabrication_assessment(cached)

        checks = evaluate_fabrication(
            mesh,
            constraints=constraints,
            policy=WORKSPACE_POLICY,
        )
        verdict = derive_fabrication_verdict(checks, policy=WORKSPACE_POLICY)
        assessment = FabricationAssessment(
            id=self._assessment_id(request, verdict, checks),
            created_at=_now(),
            revision_id=revision.id,
            artifact_sha256=revision.artifact_sha256,
            validation_id=validation.id,
            mesh_sha256=validation.mesh_sha256,
            policy=WORKSPACE_POLICY,
            constraints=constraints,
            verdict=verdict,
            checks=checks,
        )
        result_json = _json_bytes(fabrication_assessment_to_dict(assessment)).decode()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "INSERT OR IGNORE INTO fabrication_assessments "
                "(id, request_key, validation_id, created_at, policy_json, "
                "constraints_json, result_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    assessment.id,
                    request_key,
                    validation.id,
                    assessment.created_at,
                    _json_bytes(request["policy"]).decode(),
                    _json_bytes(request["constraints"]).decode(),
                    result_json,
                ),
            )
            stored = connection.execute(
                _ASSESSMENT_SELECT + "WHERE assessment.request_key = ?",
                (request_key,),
            ).fetchone()
            connection.commit()
        if stored is None:
            raise WorkspaceError("fabrication assessment was not recorded")
        return self._fabrication_assessment(stored)

    def validate_native(
        self,
        *,
        ref: str = "HEAD",
        executable: str | Path = DEFAULT_XENODREAM_EXECUTABLE,
        settings: MeshExportSettings = MeshExportSettings(),
        timeout_seconds: float = 600,
        poll_seconds: float = 1,
    ) -> NativeValidation:
        """Evaluate a revision in XenoDream and attach immutable mesh evidence."""

        executable_path = Path(executable).resolve(strict=True)
        with self._connect() as connection:
            revision = self._get_revision(connection, ref)
        source = self.artifacts / f"{revision.artifact_sha256}.xxp"
        executable_sha = sha256(executable_path.read_bytes()).hexdigest()
        request = {
            "revision_id": revision.id,
            "artifact_sha256": revision.artifact_sha256,
            "executable_sha256": executable_sha,
            "settings": asdict(settings),
            "runner_schema": "xenodream-batch-stl/v2",
        }
        request_key = sha256(_json_bytes(request)).hexdigest()
        with self._connect() as connection:
            cached = connection.execute(
                "SELECT * FROM validations WHERE request_key = ? AND outcome = 'succeeded' "
                "ORDER BY created_at DESC LIMIT 1",
                (request_key,),
            ).fetchone()
            if cached is not None:
                validation = self._validation(cached)
                if validation.mesh_path is None or Path(validation.mesh_path).is_file():
                    return validation

        run_directory = self.validation_runs / f"{revision.id[:12]}-{uuid4().hex}"
        report_path = run_directory / "report.json"
        report = run_export(
            executable_path,
            source,
            run_directory,
            report_path,
            timeout_seconds,
            poll_seconds,
            settings,
        )
        stl_data = report.get("stl")
        mesh_sha: str | None = None
        mesh_report: StlReport | None = None
        if isinstance(stl_data, dict) and isinstance(stl_data.get("path"), str):
            produced = Path(stl_data["path"])
            if produced.is_file():
                mesh_bytes = produced.read_bytes()
                mesh_sha = sha256(mesh_bytes).hexdigest()
                mesh_path = self.meshes / f"{mesh_sha}.stl"
                if mesh_path.exists():
                    if mesh_path.read_bytes() != mesh_bytes:
                        raise WorkspaceError("mesh hash collision or corrupted mesh")
                else:
                    temporary = self.meshes / f".{mesh_sha}.{uuid4().hex}.tmp"
                    try:
                        with temporary.open("xb") as stream:
                            stream.write(mesh_bytes)
                            stream.flush()
                            os.fsync(stream.fileno())
                        os.replace(temporary, mesh_path)
                    finally:
                        if temporary.exists():
                            temporary.unlink()
                mesh_report = StlReport(**stl_data)

        outcome = str(report.get("outcome"))
        native_model_valid = outcome == "succeeded"
        evaluates_to_3d = native_model_valid and mesh_report is not None
        mesh_valid = evaluates_to_3d and basic_mesh_valid(mesh_report)
        fabrication_suitable = False
        created_at = _now()
        validation_payload = {
            "request_key": request_key,
            "report": report,
            "mesh_sha256": mesh_sha,
            "created_at": created_at,
        }
        validation_id = sha256(_json_bytes(validation_payload)).hexdigest()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "INSERT INTO validations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    validation_id,
                    request_key,
                    revision.id,
                    created_at,
                    outcome,
                    _json_bytes(request).decode(),
                    _json_bytes(report).decode(),
                    mesh_sha,
                    int(native_model_valid),
                    int(evaluates_to_3d),
                    int(mesh_valid),
                    int(fabrication_suitable),
                ),
            )
            row = connection.execute(
                "SELECT * FROM validations WHERE id = ?", (validation_id,)
            ).fetchone()
            connection.commit()
        if row is None:
            raise WorkspaceError("validation was not recorded")
        return self._validation(row)

    def apply(
        self,
        operation: VerifiedOperation,
        *,
        message: str,
        prompt: str | None = None,
    ) -> ApplyResult:
        return self._apply_operation(
            operation,
            message=message,
            prompt=prompt,
            plan=None,
        )

    def apply_plan(self, plan: MutationPlan, *, message: str) -> ApplyResult:
        """Apply one typed plan only to the HEAD it was created for."""

        if not isinstance(plan, MutationPlan):
            raise TypeError("plan must be MutationPlan")
        validate_plan_provenance(plan)
        return self._apply_operation(
            plan.operation,
            message=message,
            prompt=plan.prompt,
            plan=plan,
        )

    def _apply_operation(
        self,
        operation: VerifiedOperation,
        *,
        message: str,
        prompt: str | None,
        plan: MutationPlan | None,
    ) -> ApplyResult:
        if not isinstance(message, str) or not message.strip():
            raise WorkspaceError("message must be a non-empty string")
        with self._connect() as connection:
            parent = self._get_revision(connection, "HEAD")
        if plan is not None and (
            parent.id != plan.base.revision_id
            or parent.artifact_sha256 != plan.base.artifact_sha256
        ):
            raise WorkspaceError("operation plan was created for a different HEAD")
        source = self._artifact_data(parent)
        mutation = self.adapter.apply(source, operation)
        changed = mutation.data != source
        if changed != mutation.result.changed:
            raise WorkspaceError("XenoDream mutation result disagrees with output bytes")
        if not changed:
            if plan is not None:
                with self._connect() as connection:
                    current = self._get_revision(connection, "HEAD")
                if current.id != parent.id:
                    raise WorkspaceError(
                        "operation plan was created for a different HEAD"
                    )
            return ApplyResult(parent, False, mutation.result)
        details = dict(mutation.details)
        if plan is not None:
            details = {
                **details,
                "planning": plan_provenance_to_dict(plan),
            }
        revision = self._record_revision(
            mutation.data,
            mutation.operation,
            details,
            message.strip(),
            prompt,
            parent.id,
        )
        return ApplyResult(revision, True, mutation.result)

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
        self.adapter.validate_import(data)
        with self._connect() as connection:
            parent = self._get_revision(connection, "HEAD")
        if data == self._artifact_data(parent):
            return ApplyResult(parent, False, None)
        details = {"type": "manual-import", "artifact_sha256": sha256(data).hexdigest()}
        revision = self._record_revision(
            data, "manual-import", details, message.strip(), prompt, parent.id
        )
        return ApplyResult(revision, True, None)

    def compare(self, before: str, after: str) -> list[dict[str, object]]:
        with self._connect() as connection:
            before_revision = self._get_revision(connection, before)
            after_revision = self._get_revision(connection, after)
        return self.adapter.compare(
            self._artifact_data(before_revision), self._artifact_data(after_revision)
        )
