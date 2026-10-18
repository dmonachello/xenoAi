"""Deterministic controlled-language plans for verified workspace mutations."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, DecimalException
import re
from typing import Callable, Match, TypeAlias

from .composition import AddCube, AddSphere
from .generator import Vector3
from .mutation import (
    CenteredRowMutation,
    CylinderMetamorphMutation,
    MutationError,
    ObjectMutation,
    SeededVariation,
    SphereMetamorphMutation,
    VerifiedOperation,
    verified_operation_details,
)


PLAN_SCHEMA = "xenosculpt-operation-plan/v1"
SEQUENCE_PLAN_SCHEMA = "xenosculpt-operation-sequence-plan/v1"


class PlanningError(ValueError):
    """A prompt does not identify one supported absolute operation."""


@dataclass(frozen=True, slots=True)
class PlannerIdentity:
    name: str
    version: str

    def __post_init__(self) -> None:
        for label, value in (("planner name", self.name), ("planner version", self.version)):
            if not isinstance(value, str) or not value or not value.isascii():
                raise PlanningError(f"{label} must be non-empty ASCII text")


CONTROLLED_ENGLISH_PLANNER = PlannerIdentity(
    "xenosculpt-controlled-english",
    "1",
)


@dataclass(frozen=True, slots=True)
class HeadBinding:
    revision_id: str
    artifact_sha256: str

    def __post_init__(self) -> None:
        for label, value in (
            ("revision ID", self.revision_id),
            ("artifact SHA-256", self.artifact_sha256),
        ):
            if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
                raise PlanningError(f"{label} must be 64 lowercase hexadecimal characters")

    @classmethod
    def from_revision(cls, revision: object) -> "HeadBinding":
        try:
            revision_id = revision.id
            artifact_sha256 = revision.artifact_sha256
        except AttributeError as error:
            raise TypeError("revision must provide id and artifact_sha256") from error
        return cls(revision_id, artifact_sha256)


@dataclass(frozen=True, slots=True)
class MutationPlan:
    prompt: str
    rule: str
    base: HeadBinding
    operation: VerifiedOperation
    planner: PlannerIdentity
    schema: str = field(default=PLAN_SCHEMA, init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.prompt, str) or not self.prompt.strip():
            raise PlanningError("prompt must be non-empty text")
        if not isinstance(self.rule, str) or not self.rule:
            raise PlanningError("plan rule must be non-empty text")
        if not isinstance(self.base, HeadBinding):
            raise TypeError("base must be HeadBinding")
        if not isinstance(
            self.operation,
            (
                ObjectMutation,
                CenteredRowMutation,
                SeededVariation,
                SphereMetamorphMutation,
                CylinderMetamorphMutation,
                AddCube,
                AddSphere,
            ),
        ):
            raise TypeError("operation must be a verified operation")
        if not isinstance(self.planner, PlannerIdentity):
            raise TypeError("planner must be PlannerIdentity")


@dataclass(frozen=True, slots=True)
class PlannedStep:
    rule: str
    operation: VerifiedOperation

    def __post_init__(self) -> None:
        if not isinstance(self.rule, str) or not self.rule:
            raise PlanningError("step rule must be non-empty text")
        if not isinstance(self.operation, (
            ObjectMutation,
            CenteredRowMutation,
            SeededVariation,
            SphereMetamorphMutation,
            CylinderMetamorphMutation,
            AddCube,
            AddSphere,
        )):
            raise TypeError("step operation must be a verified operation")


@dataclass(frozen=True, slots=True)
class OperationSequencePlan:
    prompt: str
    base: HeadBinding
    steps: tuple[PlannedStep, ...]
    planner: PlannerIdentity
    schema: str = field(default=SEQUENCE_PLAN_SCHEMA, init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.prompt, str) or not self.prompt.strip():
            raise PlanningError("prompt must be non-empty text")
        if not isinstance(self.base, HeadBinding):
            raise TypeError("base must be HeadBinding")
        if not isinstance(self.steps, tuple) or not 2 <= len(self.steps) <= 5:
            raise PlanningError("operation sequence must contain two through five steps")
        if any(not isinstance(step, PlannedStep) for step in self.steps):
            raise TypeError("steps must contain PlannedStep values")
        if not isinstance(self.planner, PlannerIdentity):
            raise TypeError("planner must be PlannerIdentity")


WorkspacePlan: TypeAlias = MutationPlan | OperationSequencePlan


_NUMBER = r"[+-]?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?"
_IDENTIFIER = r"[A-Za-z0-9][A-Za-z0-9._-]*"


def _decimal(value: str) -> Decimal:
    try:
        result = Decimal(value)
    except DecimalException as error:
        raise PlanningError(f"invalid decimal value {value!r}") from error
    if not result.is_finite():
        raise PlanningError(f"invalid decimal value {value!r}")
    return result


def _vector(match: Match[str]) -> Vector3:
    return Vector3(
        _decimal(match.group("x")),
        _decimal(match.group("y")),
        _decimal(match.group("z")),
    )


def _object_vector(field_name: str) -> Callable[[Match[str]], VerifiedOperation]:
    def build(match: Match[str]) -> VerifiedOperation:
        return ObjectMutation(match.group("object"), **{field_name: _vector(match)})

    return build


def _object_decimal(field_name: str) -> Callable[[Match[str]], VerifiedOperation]:
    def build(match: Match[str]) -> VerifiedOperation:
        return ObjectMutation(
            match.group("object"),
            **{field_name: _decimal(match.group("value"))},
        )

    return build


_GRAMMAR: tuple[
    tuple[str, re.Pattern[str], Callable[[Match[str]], VerifiedOperation]], ...
] = (
    (
        "add-cube-v1",
        re.compile(
            rf"add Cube at (?P<x>{_NUMBER}) (?P<y>{_NUMBER}) (?P<z>{_NUMBER})",
            re.IGNORECASE | re.ASCII,
        ),
        lambda match: AddCube(_vector(match)),
    ),
    (
        "add-sphere-v1",
        re.compile(
            rf"add Sphere at (?P<x>{_NUMBER}) (?P<y>{_NUMBER}) (?P<z>{_NUMBER})",
            re.IGNORECASE | re.ASCII,
        ),
        lambda match: AddSphere(_vector(match)),
    ),
    (
        "set-scale-v1",
        re.compile(
            rf"set object (?P<object>{_IDENTIFIER}) scale to "
            rf"(?P<x>{_NUMBER}) (?P<y>{_NUMBER}) (?P<z>{_NUMBER})",
            re.IGNORECASE | re.ASCII,
        ),
        _object_vector("scale"),
    ),
    (
        "set-rotation-v1",
        re.compile(
            rf"set object (?P<object>{_IDENTIFIER}) rotation to "
            rf"(?P<x>{_NUMBER}) (?P<y>{_NUMBER}) (?P<z>{_NUMBER})",
            re.IGNORECASE | re.ASCII,
        ),
        _object_vector("rotation"),
    ),
    (
        "set-position-v1",
        re.compile(
            rf"set object (?P<object>{_IDENTIFIER}) position to "
            rf"(?P<x>{_NUMBER}) (?P<y>{_NUMBER}) (?P<z>{_NUMBER})",
            re.IGNORECASE | re.ASCII,
        ),
        _object_vector("position"),
    ),
    (
        "set-color-density-v1",
        re.compile(
            rf"set object (?P<object>{_IDENTIFIER}) color density to "
            rf"(?P<value>{_NUMBER})",
            re.IGNORECASE | re.ASCII,
        ),
        _object_decimal("color_density"),
    ),
    (
        "set-face-warp-v1",
        re.compile(
            rf"set object (?P<object>{_IDENTIFIER}) face warp to "
            rf"(?P<value>{_NUMBER})",
            re.IGNORECASE | re.ASCII,
        ),
        _object_decimal("face_warp"),
    ),
    (
        "centered-row-v1",
        re.compile(
            rf"place objects in a centered row with spacing (?P<spacing>{_NUMBER})"
            rf"(?: centered at (?P<x>{_NUMBER}) (?P<y>{_NUMBER}) (?P<z>{_NUMBER}))?",
            re.IGNORECASE | re.ASCII,
        ),
        lambda match: CenteredRowMutation(
            _decimal(match.group("spacing")),
            Vector3() if match.group("x") is None else _vector(match),
        ),
    ),
    (
        "seeded-variation-v1",
        re.compile(
            rf"evolve with seed (?P<seed>[0-9]+)"
            rf"(?: and strength (?P<strength>{_NUMBER}))?",
            re.IGNORECASE | re.ASCII,
        ),
        lambda match: SeededVariation(
            int(match.group("seed")),
            Decimal("0.35")
            if (strength := match.group("strength")) is None
            else _decimal(strength),
        ),
    ),
    (
        "apply-sphere-profile-v1",
        re.compile(
            rf"apply Sphere profile (?P<profile>{_IDENTIFIER}) "
            rf"to object (?P<object>{_IDENTIFIER})",
            re.IGNORECASE | re.ASCII,
        ),
        lambda match: SphereMetamorphMutation(
            match.group("object"), match.group("profile")
        ),
    ),
    (
        "apply-cylinder-profile-v1",
        re.compile(
            rf"apply Cylinder profile (?P<profile>{_IDENTIFIER}) "
            rf"to object (?P<object>{_IDENTIFIER})",
            re.IGNORECASE | re.ASCII,
        ),
        lambda match: CylinderMetamorphMutation(
            match.group("object"), match.group("profile")
        ),
    ),
)


def plan_prompt(prompt: str, *, base: HeadBinding) -> MutationPlan:
    """Parse one controlled-language prompt into one verified operation."""

    if not isinstance(prompt, str) or not prompt.strip():
        raise PlanningError("prompt must be non-empty text")
    if "\n" in prompt or "\r" in prompt:
        raise PlanningError("prompt must be one line")
    if not isinstance(base, HeadBinding):
        raise TypeError("base must be HeadBinding")
    text = prompt.strip()
    for rule, pattern, builder in _GRAMMAR:
        match = pattern.fullmatch(text)
        if match is None:
            continue
        try:
            operation = builder(match)
        except (MutationError, TypeError, ValueError) as error:
            raise PlanningError(str(error)) from error
        return MutationPlan(prompt, rule, base, operation, CONTROLLED_ENGLISH_PLANNER)
    raise PlanningError(
        "prompt must match one supported absolute operation; "
        "use explicit object names and values"
    )


def plan_request(prompt: str, *, base: HeadBinding) -> WorkspacePlan:
    """Parse one operation or a bounded semicolon-separated operation sequence."""

    if not isinstance(prompt, str) or not prompt.strip():
        raise PlanningError("prompt must be non-empty text")
    if "\n" in prompt or "\r" in prompt:
        raise PlanningError("prompt must be one line")
    if ";" not in prompt:
        return plan_prompt(prompt, base=base)
    clauses = tuple(part.strip() for part in prompt.split(";"))
    if any(not clause for clause in clauses):
        raise PlanningError("operation sequence cannot contain an empty step")
    if not 2 <= len(clauses) <= 5:
        raise PlanningError("operation sequence must contain two through five steps")
    plans = tuple(plan_prompt(clause, base=base) for clause in clauses)
    return OperationSequencePlan(
        prompt=prompt,
        base=base,
        steps=tuple(PlannedStep(plan.rule, plan.operation) for plan in plans),
        planner=CONTROLLED_ENGLISH_PLANNER,
    )


def mutation_plan_to_dict(plan: MutationPlan) -> dict[str, object]:
    """Return the complete JSON-compatible representation of one plan."""

    if not isinstance(plan, MutationPlan):
        raise TypeError("plan must be MutationPlan")
    provenance = plan_provenance_to_dict(plan)
    return {
        "schema": provenance["schema"],
        "planner": provenance["planner"],
        "rule": provenance["rule"],
        "prompt": plan.prompt,
        "base": {
            "revision_id": plan.base.revision_id,
            "artifact_sha256": plan.base.artifact_sha256,
        },
        "operation": verified_operation_details(plan.operation),
    }


def workspace_plan_to_dict(plan: WorkspacePlan) -> dict[str, object]:
    if isinstance(plan, MutationPlan):
        return mutation_plan_to_dict(plan)
    if not isinstance(plan, OperationSequencePlan):
        raise TypeError("plan must be MutationPlan or OperationSequencePlan")
    return {
        "schema": plan.schema,
        "planner": {"name": plan.planner.name, "version": plan.planner.version},
        "prompt": plan.prompt,
        "base": {
            "revision_id": plan.base.revision_id,
            "artifact_sha256": plan.base.artifact_sha256,
        },
        "steps": [
            {"rule": step.rule, "operation": verified_operation_details(step.operation)}
            for step in plan.steps
        ],
    }


def plan_provenance_to_dict(plan: MutationPlan) -> dict[str, object]:
    """Return the plan fields persisted with a workspace revision."""

    if not isinstance(plan, MutationPlan):
        raise TypeError("plan must be MutationPlan")
    return {
        "schema": plan.schema,
        "planner": {
            "name": plan.planner.name,
            "version": plan.planner.version,
        },
        "rule": plan.rule,
        "base_artifact_sha256": plan.base.artifact_sha256,
    }


def workspace_plan_provenance_to_dict(plan: WorkspacePlan) -> dict[str, object]:
    if isinstance(plan, MutationPlan):
        return plan_provenance_to_dict(plan)
    if not isinstance(plan, OperationSequencePlan):
        raise TypeError("plan must be MutationPlan or OperationSequencePlan")
    return {
        "schema": plan.schema,
        "planner": {"name": plan.planner.name, "version": plan.planner.version},
        "base_artifact_sha256": plan.base.artifact_sha256,
        "steps": [
            {"rule": step.rule, "operation": verified_operation_details(step.operation)}
            for step in plan.steps
        ],
    }


def validate_plan_provenance(plan: MutationPlan) -> None:
    """Reject forged provenance for the built-in controlled-English planner."""

    if not isinstance(plan, MutationPlan):
        raise TypeError("plan must be MutationPlan")
    if plan.planner != CONTROLLED_ENGLISH_PLANNER:
        return
    expected = plan_prompt(plan.prompt, base=plan.base)
    if (
        plan.rule != expected.rule
        or verified_operation_details(plan.operation)
        != verified_operation_details(expected.operation)
    ):
        raise PlanningError(
            "controlled-English plan does not match its prompt and grammar rule"
        )


def validate_workspace_plan_provenance(plan: WorkspacePlan) -> None:
    if isinstance(plan, MutationPlan):
        validate_plan_provenance(plan)
        return
    if not isinstance(plan, OperationSequencePlan):
        raise TypeError("plan must be MutationPlan or OperationSequencePlan")
    if plan.planner != CONTROLLED_ENGLISH_PLANNER:
        return
    expected = plan_request(plan.prompt, base=plan.base)
    matches = isinstance(expected, OperationSequencePlan) and len(plan.steps) == len(
        expected.steps
    )
    if matches:
        matches = all(
            actual.rule == wanted.rule
            and verified_operation_details(actual.operation)
            == verified_operation_details(wanted.operation)
            for actual, wanted in zip(plan.steps, expected.steps, strict=True)
        )
    if not matches:
        raise PlanningError(
            "controlled-English sequence does not match its prompt and grammar rules"
        )
