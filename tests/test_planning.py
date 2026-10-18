from __future__ import annotations

from decimal import Decimal as D

import pytest

from xenodream_xxp.composition import AddCube, AddSphere
from xenodream_xxp.generator import Vector3
from xenodream_xxp.mutation import (
    CenteredRowMutation,
    CylinderMetamorphMutation,
    ObjectMutation,
    SeededVariation,
    SphereMetamorphMutation,
)
from xenodream_xxp.planning import (
    PLAN_SCHEMA,
    CONTROLLED_ENGLISH_PLANNER,
    HeadBinding,
    MutationPlan,
    OperationSequencePlan,
    PlannerIdentity,
    PlanningError,
    mutation_plan_to_dict,
    plan_provenance_to_dict,
    plan_prompt,
    plan_request,
    workspace_plan_to_dict,
    validate_plan_provenance,
    validate_workspace_plan_provenance,
)


BASE = HeadBinding("a" * 64, "b" * 64)


@pytest.mark.parametrize(
    ("prompt", "expected_rule", "expected_operation"),
    [
        (
            "set object Cube2 scale to 25 50 100",
            "set-scale-v1",
            ObjectMutation("Cube2", scale=Vector3(D("25"), D("50"), D("100"))),
        ),
        (
            "set object Cube2 rotation to 10 20 30",
            "set-rotation-v1",
            ObjectMutation("Cube2", rotation=Vector3(D("10"), D("20"), D("30"))),
        ),
        (
            "set object Sphere2 position to -5 0 5",
            "set-position-v1",
            ObjectMutation("Sphere2", position=Vector3(D("-5"), D("0"), D("5"))),
        ),
        (
            "set object Cube2 color density to 0.5",
            "set-color-density-v1",
            ObjectMutation("Cube2", color_density=D("0.5")),
        ),
        (
            "set object Cube2 face warp to 0.25",
            "set-face-warp-v1",
            ObjectMutation("Cube2", face_warp=D("0.25")),
        ),
        (
            "place objects in a centered row with spacing 90",
            "centered-row-v1",
            CenteredRowMutation(D("90")),
        ),
        (
            "place objects in a centered row with spacing 90 centered at 10 5 -2",
            "centered-row-v1",
            CenteredRowMutation(D("90"), Vector3(D("10"), D("5"), D("-2"))),
        ),
        (
            "evolve with seed 17",
            "seeded-variation-v1",
            SeededVariation(17),
        ),
        (
            "evolve with seed 17 and strength 0.5",
            "seeded-variation-v1",
            SeededVariation(17, D("0.5")),
        ),
        (
            "apply Sphere profile cushion-core to object Sphere2",
            "apply-sphere-profile-v1",
            SphereMetamorphMutation("Sphere2", "cushion-core"),
        ),
        (
            "apply Cylinder profile bevel-25-front to object Cylinder2",
            "apply-cylinder-profile-v1",
            CylinderMetamorphMutation("Cylinder2", "bevel-25-front"),
        ),
        (
            "add Cube at 75 0 0",
            "add-cube-v1",
            AddCube(Vector3(D("75"), D("0"), D("0"))),
        ),
        (
            "add Sphere at 55 0 0",
            "add-sphere-v1",
            AddSphere(Vector3(D("55"), D("0"), D("0"))),
        ),
    ],
)
def test_plan_prompt_maps_controlled_language_to_one_typed_operation(
    prompt, expected_rule, expected_operation
) -> None:
    plan = plan_prompt(prompt, base=BASE)

    assert plan.schema == PLAN_SCHEMA
    assert plan.planner == CONTROLLED_ENGLISH_PLANNER
    assert plan.prompt == prompt
    assert plan.rule == expected_rule
    assert plan.base == BASE
    assert plan.operation == expected_operation
    assert plan_prompt(prompt, base=BASE) == plan


@pytest.mark.parametrize(
    "prompt",
    [
        "",
        "   ",
        "make it prettier",
        "move Cube2 a little left",
        "set object Cube2 scale to 25 50",
        "set object Cube2 scale to 25mm 50mm 100mm",
        "set object Cube2 scale to 2.5e1 50 100",
        "set object Cube2 scale to 25 50 100 and rotate it",
        "set object Cube2 scale to 25 50 100\nset object Cube2 position to 0 0 0",
        "apply Sphere profile invented to object Sphere2",
        "apply profile cushion-core to object Sphere2",
    ],
)
def test_plan_prompt_rejects_language_that_is_not_one_exact_operation(prompt) -> None:
    with pytest.raises(PlanningError):
        plan_prompt(prompt, base=BASE)


def test_mutation_plan_serialization_is_complete_and_stable() -> None:
    plan = plan_prompt(
        "apply Cylinder profile bevel-25-front to object Cylinder2",
        base=BASE,
    )

    assert mutation_plan_to_dict(plan) == {
        "schema": "xenosculpt-operation-plan/v1",
        "planner": {
            "name": "xenosculpt-controlled-english",
            "version": "1",
        },
        "rule": "apply-cylinder-profile-v1",
        "prompt": "apply Cylinder profile bevel-25-front to object Cylinder2",
        "base": {
            "revision_id": "a" * 64,
            "artifact_sha256": "b" * 64,
        },
        "operation": {
            "type": "cylinder-metamorph-profile-v1",
            "object_name": "Cylinder2",
            "profile": "bevel-25-front",
            "evidence": ["R036"],
            "native_validation_required": True,
            "fabrication_suitable": False,
        },
    }


def test_mutation_plan_rejects_an_unverified_operation() -> None:
    with pytest.raises(TypeError, match="verified operation"):
        MutationPlan(
            prompt="set object Cube2 position to 25 0 0",
            rule="set-position-v1",
            base=BASE,
            operation=object(),
            planner=CONTROLLED_ENGLISH_PLANNER,
        )


def test_plan_serialization_preserves_an_explicit_planner_identity() -> None:
    planner = PlannerIdentity("test-planner", "2")
    plan = MutationPlan(
        prompt="structured input",
        rule="test-position-v2",
        base=BASE,
        operation=ObjectMutation(
            "Cube2", position=Vector3(D("25"), D("0"), D("0"))
        ),
        planner=planner,
    )

    serialized = mutation_plan_to_dict(plan)
    assert serialized["planner"] == {"name": "test-planner", "version": "2"}
    assert plan_provenance_to_dict(plan) == {
        "schema": PLAN_SCHEMA,
        "planner": {"name": "test-planner", "version": "2"},
        "rule": "test-position-v2",
        "base_artifact_sha256": "b" * 64,
    }


def test_plan_request_builds_a_bounded_operation_sequence() -> None:
    prompt = (
        "add Sphere at 55 0 0; "
        "apply Sphere profile cushion-core to object Sphere3"
    )
    plan = plan_request(prompt, base=BASE)

    assert isinstance(plan, OperationSequencePlan)
    assert [step.rule for step in plan.steps] == [
        "add-sphere-v1",
        "apply-sphere-profile-v1",
    ]
    assert plan.steps[0].operation == AddSphere(Vector3(D("55"), D("0"), D("0")))
    serialized = workspace_plan_to_dict(plan)
    assert serialized["schema"] == "xenosculpt-operation-sequence-plan/v1"
    assert len(serialized["steps"]) == 2


@pytest.mark.parametrize(
    "prompt",
    [
        "add Sphere at 55 0 0;",
        "; add Sphere at 55 0 0",
        "add Sphere at 55 0 0;; set object Sphere3 scale to 40 40 40",
        "add Sphere at 55 0 0\nset object Sphere3 scale to 40 40 40",
        ";".join(["add Sphere at 55 0 0"] * 6),
    ],
)
def test_plan_request_rejects_invalid_sequences(prompt) -> None:
    with pytest.raises(PlanningError):
        plan_request(prompt, base=BASE)


def test_signed_zero_cannot_forge_single_plan_provenance() -> None:
    plan = MutationPlan(
        prompt="set object Cube2 position to 0 0 0",
        rule="set-position-v1",
        base=BASE,
        operation=ObjectMutation(
            "Cube2", position=Vector3(D("-0"), D("0"), D("0"))
        ),
        planner=CONTROLLED_ENGLISH_PLANNER,
    )

    with pytest.raises(PlanningError, match="does not match"):
        validate_plan_provenance(plan)


def test_signed_zero_cannot_forge_sequence_plan_provenance() -> None:
    parsed = plan_request(
        "add Sphere at 0 0 0; apply Sphere profile cushion-core to object Sphere3",
        base=BASE,
    )
    assert isinstance(parsed, OperationSequencePlan)
    forged = OperationSequencePlan(
        prompt=parsed.prompt,
        base=parsed.base,
        steps=(
            type(parsed.steps[0])(
                parsed.steps[0].rule,
                AddSphere(Vector3(D("-0"), D("0"), D("0"))),
            ),
            parsed.steps[1],
        ),
        planner=parsed.planner,
    )

    with pytest.raises(PlanningError, match="does not match"):
        validate_workspace_plan_provenance(forged)
