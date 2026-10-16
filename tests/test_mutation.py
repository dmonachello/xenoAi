from __future__ import annotations

from decimal import Decimal as D

import pytest

from xenodream_xxp.diffing import diff_documents
from xenodream_xxp.document import parse_bytes
from xenodream_xxp.generator import (
    CubeSpec,
    ProjectSpec,
    SphereSpec,
    Vector3,
    compile_cube,
    compile_project,
)
from xenodream_xxp.mutation import (
    CenteredRowMutation,
    MutationError,
    ObjectMutation,
    SeededVariation,
    apply_verified_mutation,
)


def test_mutates_only_verified_cube_fields() -> None:
    source = compile_cube()
    result = apply_verified_mutation(
        source,
        ObjectMutation(
            "Cube2",
            scale=Vector3(D("25"), D("50"), D("100")),
            rotation=Vector3(D("10"), D("20"), D("30")),
            position=Vector3(D("-5"), D("0"), D("5")),
            color_density=D("0.5"),
            face_warp=D("0.25"),
        ),
    )

    assert result.changed is True
    assert parse_bytes(result.data).to_bytes() == result.data
    assert [
        (item["section"], item["key"], item.get("token_index"))
        for item in diff_documents(parse_bytes(source), parse_bytes(result.data))
    ] == [
        ("Holon\\1", "Transform", 0),
        ("Holon\\1", "Transform", 2),
        ("Holon\\1", "Transform", 6),
        ("Holon\\1", "Transform", 7),
        ("Holon\\1", "Transform", 8),
        ("Holon\\1", "Transform", 9),
        ("Holon\\1", "Transform", 11),
        ("Holon\\1", "GradDensity", None),
        ("Holon\\1\\MM\\0", "Pars", 0),
    ]


def test_reapplying_same_value_is_byte_identical() -> None:
    source = compile_cube(CubeSpec(position=Vector3(D("25"), D("0"), D("0"))))
    result = apply_verified_mutation(
        source,
        ObjectMutation("Cube2", position=Vector3(D("25"), D("0"), D("0"))),
    )

    assert result.changed is False
    assert result.data == source
    assert result.differences == ()


def test_sphere_rejects_unverified_properties() -> None:
    source = compile_project(ProjectSpec(objects=(SphereSpec(),)))

    with pytest.raises(MutationError, match="only scale and position"):
        apply_verified_mutation(
            source,
            ObjectMutation("Sphere2", rotation=Vector3(D("10"), D("0"), D("0"))),
        )


def test_requires_unique_name_and_verified_precision() -> None:
    source = compile_cube()

    with pytest.raises(MutationError, match="matched 0 objects"):
        apply_verified_mutation(source, ObjectMutation("missing", face_warp=D("0.1")))
    with pytest.raises(MutationError, match="5-place precision"):
        apply_verified_mutation(
            source,
            ObjectMutation(
                "Cube2", position=Vector3(D("0.000001"), D("0"), D("0"))
            ),
        )


def test_row_mutation_positions_supported_objects_and_preserves_other_fields() -> None:
    source = compile_project(
        ProjectSpec(
            objects=(
                CubeSpec(face_warp=D("0.25")),
                SphereSpec(scale=Vector3(D("40"), D("40"), D("40"))),
            )
        )
    )
    result = apply_verified_mutation(
        source,
        CenteredRowMutation(
            spacing=D("90"), center=Vector3(D("10"), D("5"), D("-2"))
        ),
    )

    assert b"-35.00000 5.00000 -2.00000 " in result.data
    assert b"55.00000 5.00000 -2.00000 " in result.data
    assert b"0.2500 0 0.0000" in result.data
    assert b"40.00000 40.00000 40.00000" in result.data
    assert all(item["key"] == "Transform" for item in result.differences)


def test_seeded_variation_is_repeatable_and_changes_only_physical_fields() -> None:
    source = compile_project(
        ProjectSpec(objects=(CubeSpec(), SphereSpec()))
    )
    operation = SeededVariation(seed=20261016, strength=D("0.5"))

    first = apply_verified_mutation(source, operation)
    second = apply_verified_mutation(source, operation)

    assert first.changed is True
    assert first.data == second.data
    assert first.differences == second.differences
    assert first.object_names == ("Cube2", "Sphere3")
    assert parse_bytes(first.data).to_bytes() == first.data
    assert {
        (item["section"], item["key"], item.get("token_index"))
        for item in first.differences
    } <= {
        *{
            (section, "Transform", token)
            for section in ("Holon\\1", "Holon\\2")
            for token in range(12)
            if token in (0, 1, 2, 6, 7, 8, 9, 10, 11)
        },
        ("Holon\\1\\MM\\0", "Pars", 0),
    }
    assert all(item["key"] != "GradDensity" for item in first.differences)


def test_seeded_variation_validates_seed_and_strength() -> None:
    with pytest.raises(MutationError, match="seed"):
        SeededVariation(seed=-1)
    with pytest.raises(MutationError, match="strength"):
        SeededVariation(seed=1, strength=D("0"))
    with pytest.raises(MutationError, match="strength"):
        SeededVariation(seed=1, strength=D("1.01"))
