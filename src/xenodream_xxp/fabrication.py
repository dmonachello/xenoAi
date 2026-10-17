"""Versioned fabrication assessment over retained mesh evidence."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import StrEnum
import re

from .generator import Vector3
from .mesh import StlReport, basic_mesh_valid
from .errors import WorkspaceError


ASSESSMENT_SCHEMA = "xenosculpt-fabrication-assessment/v1"


class FabricationError(WorkspaceError):
    """A fabrication policy or assessment invariant was violated."""


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
                raise FabricationError("build volume dimensions must be positive")
        if self.min_feature_mm is not None:
            if not isinstance(self.min_feature_mm, Decimal):
                raise TypeError("min_feature_mm must be Decimal or None")
            if not self.min_feature_mm.is_finite() or self.min_feature_mm <= 0:
                raise FabricationError(
                    "minimum feature size must be finite and positive"
                )


@dataclass(frozen=True, slots=True)
class PolicyIdentity:
    name: str
    version: str

    def __post_init__(self) -> None:
        for label, value in (("policy name", self.name), ("policy version", self.version)):
            if not isinstance(value, str) or not value or not value.isascii():
                raise FabricationError(f"{label} must be non-empty ASCII text")


WORKSPACE_POLICY = PolicyIdentity("workspace-constraints", "1")


class CheckStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    NOT_EVALUATED = "not_evaluated"
    NOT_APPLICABLE = "not_applicable"


class FabricationVerdict(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    INCOMPLETE = "incomplete"


class CheckCode(StrEnum):
    BASIC_MESH = "basic-mesh"
    BUILD_VOLUME = "build-volume"
    SELF_INTERSECTIONS = "self-intersections"
    MINIMUM_FEATURE = "minimum-feature"
    PROCESS = "process"


WORKSPACE_POLICY_V1_CHECKS = (
    CheckCode.BASIC_MESH,
    CheckCode.BUILD_VOLUME,
    CheckCode.SELF_INTERSECTIONS,
    CheckCode.MINIMUM_FEATURE,
    CheckCode.PROCESS,
)


@dataclass(frozen=True, slots=True)
class FabricationCheck:
    code: CheckCode
    status: CheckStatus
    summary: str
    measured_mm: tuple[float, float, float] | None = None
    limit_mm: tuple[Decimal, Decimal, Decimal] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.code, CheckCode):
            raise TypeError("code must be CheckCode")
        if not isinstance(self.status, CheckStatus):
            raise TypeError("status must be CheckStatus")
        if not isinstance(self.summary, str) or not self.summary:
            raise FabricationError("check summary must be non-empty text")
        has_measurement = self.measured_mm is not None or self.limit_mm is not None
        if has_measurement and (
            self.code is not CheckCode.BUILD_VOLUME
            or self.measured_mm is None
            or self.limit_mm is None
        ):
            raise FabricationError(
                "only a measured build-volume check may carry dimensions"
            )
        if (
            self.code is CheckCode.BUILD_VOLUME
            and self.status in {CheckStatus.PASS, CheckStatus.FAIL}
            and not has_measurement
        ):
            raise FabricationError(
                "an evaluated build-volume check requires measured and limit dimensions"
            )


@dataclass(frozen=True, slots=True)
class FabricationAssessment:
    id: str
    created_at: str
    revision_id: str
    artifact_sha256: str
    validation_id: str
    mesh_sha256: str
    policy: PolicyIdentity
    constraints: FabricationConstraints
    verdict: FabricationVerdict
    checks: tuple[FabricationCheck, ...]
    schema: str = ASSESSMENT_SCHEMA

    def __post_init__(self) -> None:
        for label, value in (
            ("assessment ID", self.id),
            ("revision ID", self.revision_id),
            ("artifact SHA-256", self.artifact_sha256),
            ("validation ID", self.validation_id),
            ("mesh SHA-256", self.mesh_sha256),
        ):
            if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
                raise FabricationError(
                    f"{label} must be 64 lowercase hexadecimal characters"
                )
        if not isinstance(self.created_at, str) or not self.created_at:
            raise FabricationError("created_at must be non-empty text")
        if not isinstance(self.policy, PolicyIdentity):
            raise TypeError("policy must be PolicyIdentity")
        if not isinstance(self.constraints, FabricationConstraints):
            raise TypeError("constraints must be FabricationConstraints")
        if not isinstance(self.verdict, FabricationVerdict):
            raise TypeError("verdict must be FabricationVerdict")
        expected = derive_fabrication_verdict(self.checks, policy=self.policy)
        if self.verdict is not expected:
            raise FabricationError("fabrication verdict disagrees with its checks")
        if self.schema != ASSESSMENT_SCHEMA:
            raise FabricationError(f"unsupported fabrication assessment schema {self.schema!r}")

    @property
    def fabrication_suitable(self) -> bool:
        return self.verdict is FabricationVerdict.PASS


def evaluate_fabrication(
    mesh: StlReport,
    *,
    constraints: FabricationConstraints,
    policy: PolicyIdentity = WORKSPACE_POLICY,
) -> tuple[FabricationCheck, ...]:
    """Evaluate or account for every workspace-policy check."""

    if not isinstance(mesh, StlReport):
        raise TypeError("mesh must be StlReport")
    if not isinstance(constraints, FabricationConstraints):
        raise TypeError("constraints must be FabricationConstraints")
    if policy != WORKSPACE_POLICY:
        raise FabricationError(f"unsupported fabrication policy {policy!r}")

    basic_valid = basic_mesh_valid(mesh)
    checks = [
        FabricationCheck(
            CheckCode.BASIC_MESH,
            CheckStatus.PASS if basic_valid else CheckStatus.FAIL,
            "mesh passes the current basic topology predicate"
            if basic_valid
            else "mesh fails the current basic topology predicate",
        )
    ]

    volume = constraints.build_volume_mm
    if volume is None:
        checks.append(
            FabricationCheck(
                CheckCode.BUILD_VOLUME,
                CheckStatus.NOT_APPLICABLE,
                "no build volume is recorded for this workspace",
            )
        )
    else:
        limit = (volume.x, volume.y, volume.z)
        fits = all(
            Decimal.from_float(measured) <= allowed
            for measured, allowed in zip(mesh.dimensions, limit)
        )
        checks.append(
            FabricationCheck(
                CheckCode.BUILD_VOLUME,
                CheckStatus.PASS if fits else CheckStatus.FAIL,
                "measured dimensions fit the configured axes in the current orientation"
                if fits
                else "measured dimensions exceed a configured axis in the current orientation",
                measured_mm=mesh.dimensions,
                limit_mm=limit,
            )
        )

    checks.append(
        FabricationCheck(
            CheckCode.SELF_INTERSECTIONS,
            CheckStatus.NOT_EVALUATED,
            "no exact self-intersection analyzer is implemented",
        )
    )

    if constraints.min_feature_mm is None:
        checks.append(
            FabricationCheck(
                CheckCode.MINIMUM_FEATURE,
                CheckStatus.NOT_APPLICABLE,
                "no minimum feature is recorded for this workspace",
            )
        )
    else:
        checks.append(
            FabricationCheck(
                CheckCode.MINIMUM_FEATURE,
                CheckStatus.NOT_EVALUATED,
                "the recorded minimum feature has no verified measurement semantics",
            )
        )

    if constraints.process is None:
        checks.append(
            FabricationCheck(
                CheckCode.PROCESS,
                CheckStatus.NOT_APPLICABLE,
                "no fabrication process is recorded for this workspace",
            )
        )
    else:
        checks.append(
            FabricationCheck(
                CheckCode.PROCESS,
                CheckStatus.NOT_EVALUATED,
                f"{constraints.process} is a recorded label, not a versioned process profile",
            )
        )

    result = tuple(checks)
    derive_fabrication_verdict(result, policy=policy)
    return result


def derive_fabrication_verdict(
    checks: tuple[FabricationCheck, ...],
    *,
    policy: PolicyIdentity = WORKSPACE_POLICY,
) -> FabricationVerdict:
    """Derive one verdict from a complete workspace-policy check set."""

    if not isinstance(checks, tuple) or not all(
        isinstance(item, FabricationCheck) for item in checks
    ):
        raise TypeError("checks must be a tuple of FabricationCheck values")
    if policy != WORKSPACE_POLICY:
        raise FabricationError(f"unsupported fabrication policy {policy!r}")
    codes = tuple(item.code for item in checks)
    if (
        len(codes) != len(WORKSPACE_POLICY_V1_CHECKS)
        or set(codes) != set(WORKSPACE_POLICY_V1_CHECKS)
    ):
        raise FabricationError("assessment requires exactly one result per check code")
    allowed_statuses = {
        CheckCode.BASIC_MESH: {CheckStatus.PASS, CheckStatus.FAIL},
        CheckCode.BUILD_VOLUME: {
            CheckStatus.PASS,
            CheckStatus.FAIL,
            CheckStatus.NOT_APPLICABLE,
        },
        CheckCode.SELF_INTERSECTIONS: {CheckStatus.NOT_EVALUATED},
        CheckCode.MINIMUM_FEATURE: {
            CheckStatus.NOT_EVALUATED,
            CheckStatus.NOT_APPLICABLE,
        },
        CheckCode.PROCESS: {
            CheckStatus.NOT_EVALUATED,
            CheckStatus.NOT_APPLICABLE,
        },
    }
    for check in checks:
        if check.status not in allowed_statuses[check.code]:
            raise FabricationError(
                f"{check.code.value} status {check.status.value} is invalid for "
                f"policy {policy.name}/{policy.version}"
            )
    if any(item.status is CheckStatus.FAIL for item in checks):
        return FabricationVerdict.FAIL
    return FabricationVerdict.INCOMPLETE


def constraints_to_dict(value: FabricationConstraints) -> dict[str, object]:
    if not isinstance(value, FabricationConstraints):
        raise TypeError("value must be FabricationConstraints")
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


def constraints_from_dict(value: object) -> FabricationConstraints:
    if not isinstance(value, dict):
        raise FabricationError("fabrication constraints must be an object")
    raw_volume = value.get("build_volume_mm")
    volume = None
    try:
        if raw_volume is not None:
            if not isinstance(raw_volume, list) or len(raw_volume) != 3:
                raise FabricationError("build_volume_mm must contain three values")
            volume = Vector3(*(Decimal(str(item)) for item in raw_volume))
        raw_feature = value.get("min_feature_mm")
        feature = None if raw_feature is None else Decimal(str(raw_feature))
    except InvalidOperation as error:
        raise FabricationError(
            "fabrication constraints contain an invalid numeric value"
        ) from error
    raw_process = value.get("process")
    if raw_process is not None and not isinstance(raw_process, str):
        raise FabricationError("process must be text or null")
    return FabricationConstraints(
        process=raw_process,
        build_volume_mm=volume,
        min_feature_mm=feature,
    )


def fabrication_check_to_dict(check: FabricationCheck) -> dict[str, object]:
    if not isinstance(check, FabricationCheck):
        raise TypeError("check must be FabricationCheck")
    result: dict[str, object] = {
        "code": check.code.value,
        "status": check.status.value,
        "summary": check.summary,
    }
    if check.measured_mm is not None:
        result["measured_mm"] = list(check.measured_mm)
    if check.limit_mm is not None:
        result["limit_mm"] = [str(value) for value in check.limit_mm]
    return result


def _fabrication_check_from_dict(value: object) -> FabricationCheck:
    if not isinstance(value, dict):
        raise FabricationError("fabrication check must be an object")
    try:
        code = CheckCode(value["code"])
        status = CheckStatus(value["status"])
        summary = value["summary"]
    except (KeyError, TypeError, ValueError) as error:
        raise FabricationError("fabrication check has invalid identity fields") from error
    raw_measured = value.get("measured_mm")
    measured = None
    if raw_measured is not None:
        if not isinstance(raw_measured, list) or len(raw_measured) != 3:
            raise FabricationError("measured_mm must contain three values")
        measured = tuple(float(item) for item in raw_measured)
    raw_limit = value.get("limit_mm")
    limit = None
    if raw_limit is not None:
        if not isinstance(raw_limit, list) or len(raw_limit) != 3:
            raise FabricationError("limit_mm must contain three values")
        limit = tuple(Decimal(str(item)) for item in raw_limit)
    return FabricationCheck(code, status, summary, measured, limit)


def fabrication_assessment_to_dict(
    assessment: FabricationAssessment,
) -> dict[str, object]:
    if not isinstance(assessment, FabricationAssessment):
        raise TypeError("assessment must be FabricationAssessment")
    return {
        "id": assessment.id,
        "created_at": assessment.created_at,
        "schema": assessment.schema,
        "revision_id": assessment.revision_id,
        "artifact_sha256": assessment.artifact_sha256,
        "validation_id": assessment.validation_id,
        "mesh_sha256": assessment.mesh_sha256,
        "policy": {
            "name": assessment.policy.name,
            "version": assessment.policy.version,
        },
        "constraints": constraints_to_dict(assessment.constraints),
        "verdict": assessment.verdict.value,
        "fabrication_suitable": assessment.fabrication_suitable,
        "checks": [fabrication_check_to_dict(item) for item in assessment.checks],
    }


def fabrication_assessment_from_dict(value: object) -> FabricationAssessment:
    if not isinstance(value, dict):
        raise FabricationError("fabrication assessment must be an object")
    raw_policy = value.get("policy")
    raw_checks = value.get("checks")
    if not isinstance(raw_policy, dict) or not isinstance(raw_checks, list):
        raise FabricationError("fabrication assessment is missing policy or checks")
    try:
        assessment = FabricationAssessment(
            id=value["id"],
            created_at=value["created_at"],
            revision_id=value["revision_id"],
            artifact_sha256=value["artifact_sha256"],
            validation_id=value["validation_id"],
            mesh_sha256=value["mesh_sha256"],
            policy=PolicyIdentity(raw_policy["name"], raw_policy["version"]),
            constraints=constraints_from_dict(value["constraints"]),
            verdict=FabricationVerdict(value["verdict"]),
            checks=tuple(_fabrication_check_from_dict(item) for item in raw_checks),
            schema=value["schema"],
        )
    except (KeyError, TypeError, ValueError) as error:
        if isinstance(error, FabricationError):
            raise
        raise FabricationError("fabrication assessment has invalid fields") from error
    if value.get("fabrication_suitable") is not assessment.fabrication_suitable:
        raise FabricationError("fabrication suitability disagrees with verdict")
    return assessment
