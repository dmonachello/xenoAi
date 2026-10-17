from __future__ import annotations

from decimal import Decimal as D

import pytest

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
    PlannerIdentity,
    PlanningError,
    mutation_plan_to_dict,
    plan_provenance_to_dict,
    plan_prompt,
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
