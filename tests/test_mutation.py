from __future__ import annotations

from decimal import Decimal as D

import pytest

from xenodream_xxp.composition import AddCube, AddEmptyGroup, AddSphere
from xenodream_xxp.diffing import diff_documents
from xenodream_xxp.document import parse_bytes
from xenodream_xxp.generator import (
    CubeSpec,
    ProjectSpec,
    SphereSpec,
    Vector3,
    compile_cube,
    compile_cylinder,
    compile_project,
    compile_sphere,
)
from xenodream_xxp.mutation import (
    CenteredRowMutation,
    CylinderMetamorphMutation,
    MutationError,
    ObjectMutation,
    SeededVariation,
    SphereMetamorphMutation,
    apply_verified_mutation,
    cylinder_metamorph_profile_evidence,
    cylinder_metamorph_profiles,
    sphere_metamorph_profile_evidence,
    sphere_metamorph_profiles,
    verified_operation_details,
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


def test_add_cube_is_a_verified_structural_mutation() -> None:
    result = apply_verified_mutation(
        compile_cube(),
        AddCube(position=Vector3(D("75"), D("0"), D("0"))),
    )

    assert result.changed is True
    assert result.object_names == ("Cube3",)
    assert result.added is not None
    assert result.added.name == "Cube3"
    assert result.structural_changes[0].section == "Holon\\2"
    assert result.native_validation_required is True
    assert result.fabrication_suitable is False
    assert verified_operation_details(
        AddCube(position=Vector3(D("75"), D("0"), D("0")))
    ) == {
        "type": "add-cube-v1",
        "position": ["75", "0", "0"],
        "evidence": ["E055", "E056", "E057", "E060", "E061", "E062"],
        "native_validation_required": True,
        "fabrication_suitable": False,
    }


def test_add_sphere_is_a_verified_structural_mutation() -> None:
    result = apply_verified_mutation(
        compile_cube(),
        AddSphere(position=Vector3(D("75"), D("0"), D("0"))),
    )

    assert result.changed is True
    assert result.object_names == ("Sphere3",)
    assert result.added is not None
    assert result.added.name == "Sphere3"
    assert result.native_validation_required is True
    assert result.fabrication_suitable is False
    assert verified_operation_details(
        AddSphere(position=Vector3(D("75"), D("0"), D("0")))
    ) == {
        "type": "add-sphere-v1",
        "position": ["75", "0", "0"],
        "evidence": [
            "E063",
            "E064",
            "E066",
            "E069",
            "E085",
            "E106",
            "E108",
        ],
        "native_validation_required": True,
        "fabrication_suitable": False,
    }


def test_add_empty_group_is_a_verified_structural_mutation() -> None:
    result = apply_verified_mutation(compile_cube(), AddEmptyGroup())

    assert result.changed is True
    assert result.object_names == ()
    assert result.added is not None
    assert result.added.name == "Group3"
    assert result.native_validation_required is True
    assert result.fabrication_suitable is False
    assert verified_operation_details(AddEmptyGroup()) == {
        "type": "add-empty-group-v1",
        "evidence": ["E050", "E051"],
        "native_validation_required": True,
        "fabrication_suitable": False,
    }


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


def test_sphere_metamorph_profiles_are_measured_and_replace_complete_state() -> None:
    profiles = sphere_metamorph_profiles()
    assert len(profiles) == 15
    assert "cushion-core" in profiles
    assert sphere_metamorph_profile_evidence("cushion-core") == ("R031", "E096")

    source = compile_sphere()
    for profile in profiles:
        result = apply_verified_mutation(
            source, SphereMetamorphMutation("Sphere2", profile)
        )
        assert parse_bytes(result.data).to_bytes() == result.data
        assert result.changed is True
        assert result.native_validation_required is True
        assert result.fabrication_suitable is False
        assert all(
            item["section"] == "Holon\\1\\MM\\0" and item["key"] == "Pars"
            for item in result.differences
        )

    cushion = apply_verified_mutation(
        source, SphereMetamorphMutation("Sphere2", "cushion-core")
    )
    assert cushion.native_validation_required is True
    assert cushion.fabrication_suitable is False
    assert [item["token_index"] for item in cushion.differences] == [8, 9, 10, 11]
    assert (
        b"Pars=0.00000 0 0.0000 0.00000 0.00000 0.00000 0.00000 "
        b"0.0000 -20.0000 -28.000 1 2 "
    ) in cushion.data

    switched = apply_verified_mutation(
        cushion.data, SphereMetamorphMutation("Sphere2", "warp-tear-anti")
    )
    assert [item["token_index"] for item in switched.differences] == [0, 1, 8, 9, 10, 11]
    assert (
        b"Pars=-7.00000 4 0.0000 0.00000 0.00000 0.00000 0.00000 "
        b"0.0000 0.0000 0.000 0 0 "
    ) in switched.data

    repeated = apply_verified_mutation(
        switched.data, SphereMetamorphMutation("Sphere2", "warp-tear-anti")
    )
    assert repeated.changed is False
    assert repeated.data == switched.data


def test_sphere_metamorph_profile_rejects_unknown_profile_and_cube_target() -> None:
    with pytest.raises(MutationError, match="unknown Sphere metamorph profile"):
        SphereMetamorphMutation("Sphere2", "invented")
    with pytest.raises(MutationError, match="does not support apply-sphere-profile-v1"):
        apply_verified_mutation(
            compile_cube(), SphereMetamorphMutation("Cube2", "cushion-core")
        )


def test_cylinder_metamorph_profiles_are_measured_complete_states() -> None:
    expected = {
        "length-three": b"3.00000 360.0000 2 0 0 0.000 2",
        "closed-ends-none": b"1.00000 360.0000 0 0 0 0.000 2",
        "closed-ends-back": b"1.00000 360.0000 1 0 0 0.000 2",
        "wedge-yes": b"1.00000 360.0000 2 1 0 0.000 2",
        "spherical-yes": b"1.00000 360.0000 2 0 1 0.000 2",
        "bevel-25-both": b"1.00000 360.0000 2 0 0 25.000 2",
        "bevel-25-front": b"1.00000 360.0000 2 0 0 25.000 0",
        "bevel-25-back": b"1.00000 360.0000 2 0 0 25.000 1",
    }
    assert cylinder_metamorph_profiles() == tuple(expected)
    assert cylinder_metamorph_profile_evidence("length-three") == ("R035",)
    assert cylinder_metamorph_profile_evidence("bevel-25-back") == ("R036",)

    source = compile_cylinder()
    for profile, pars in expected.items():
        result = apply_verified_mutation(
            source, CylinderMetamorphMutation("Cylinder2", profile)
        )
        assert parse_bytes(result.data).to_bytes() == result.data
        assert result.changed is True
        assert result.native_validation_required is True
        assert result.fabrication_suitable is False
        assert b"Pars=" + pars + b" " in result.data
        assert all(
            item["section"] == "Holon\\1\\MM\\0" and item["key"] == "Pars"
            for item in result.differences
        )

    beveled = apply_verified_mutation(
        source, CylinderMetamorphMutation("Cylinder2", "bevel-25-front")
    )
    switched = apply_verified_mutation(
        beveled.data, CylinderMetamorphMutation("Cylinder2", "length-three")
    )
    assert b"Pars=" + expected["length-three"] + b" " in switched.data
    assert [item["token_index"] for item in switched.differences] == [0, 5, 6]

    repeated = apply_verified_mutation(
        switched.data, CylinderMetamorphMutation("Cylinder2", "length-three")
    )
    assert repeated.changed is False
    assert repeated.data == switched.data


def test_cylinder_profile_is_scoped_away_from_other_mutation_families() -> None:
    source = compile_cylinder()

    with pytest.raises(MutationError, match="unknown Cylinder metamorph profile"):
        CylinderMetamorphMutation("Cylinder2", "invented")
    with pytest.raises(MutationError, match="does not support apply-cylinder-profile-v1"):
        apply_verified_mutation(
            compile_sphere(),
            CylinderMetamorphMutation("Sphere2", "length-three"),
        )
    with pytest.raises(MutationError, match="Cube or Sphere"):
        apply_verified_mutation(
            source, SphereMetamorphMutation("Cylinder2", "cushion-core")
        )
    with pytest.raises(MutationError, match="Cube or Sphere"):
        apply_verified_mutation(
            source,
            ObjectMutation("Cylinder2", position=Vector3(D("1"), D("0"), D("0"))),
        )
    with pytest.raises(MutationError, match="Cube or Sphere"):
        apply_verified_mutation(source, SeededVariation(seed=17))
    with pytest.raises(MutationError, match="Cube or Sphere"):
        apply_verified_mutation(source, CenteredRowMutation(spacing=D("10")))


def test_known_target_can_be_mutated_beside_an_opaque_object() -> None:
    source = compile_project(
        ProjectSpec(objects=(CubeSpec(), SphereSpec()))
    ).replace(b"Style=1", b"Style=999", 1)
    opaque_before = source[source.index(b"[Holon\\2]") :]

    result = apply_verified_mutation(
        source,
        ObjectMutation("Cube2", position=Vector3(D("25"), D("0"), D("0"))),
    )

    assert result.changed is True
    assert result.object_names == ("Cube2",)
    assert result.data[result.data.index(b"[Holon\\2]") :] == opaque_before
    assert [(item["section"], item["key"], item.get("token_index")) for item in result.differences] == [
        ("Holon\\1", "Transform", 9)
    ]


def test_cylinder_profile_rejects_malformed_record_identity() -> None:
    source = compile_cylinder()
    operation = CylinderMetamorphMutation("Cylinder2", "length-three")

    with pytest.raises(MutationError, match="does not support apply-cylinder-profile-v1"):
        apply_verified_mutation(source.replace(b"Style=13", b"Style=12"), operation)
    with pytest.raises(MutationError, match="does not support apply-cylinder-profile-v1"):
        apply_verified_mutation(source.replace(b"NumPars=7", b"NumPars=8"), operation)
    with pytest.raises(MutationError, match="does not support apply-cylinder-profile-v1"):
        apply_verified_mutation(
            source.replace(
                b"Pars=1.00000 360.0000 2 0 0 0.000 2 ",
                b"Pars=1.00000 360.0000 2 0 0 0.000 ",
            ),
            operation,
        )


def test_cylinder_profile_requires_one_unique_named_target() -> None:
    source = compile_cylinder()
    operation = CylinderMetamorphMutation("Cylinder2", "length-three")

    with pytest.raises(MutationError, match="matched 0 objects"):
        apply_verified_mutation(
            source, CylinderMetamorphMutation("missing", "length-three")
        )

    block_start = source.index(b"[Holon\\1]")
    block_end = source.index(b"[Gradients]")
    duplicate_block = source[block_start:block_end].replace(
        b"Holon\\1", b"Holon\\2"
    ).replace(b"ID=1", b"ID=2", 1)
    duplicate = (
        source[:block_end].replace(b"NumHolons=2", b"NumHolons=3")
        + duplicate_block
        + source[block_end:]
    )

    with pytest.raises(MutationError, match="matched 2 objects"):
        apply_verified_mutation(duplicate, operation)


def test_cylinder_profile_rejects_duplicate_constructor_metamorph() -> None:
    source = compile_cylinder()
    start = source.index(b"[Holon\\1\\MM\\0]")
    end = source.index(b"[Gradients]")
    duplicate = source[:end] + source[start:end] + source[end:]

    with pytest.raises(
        MutationError, match="does not support apply-cylinder-profile-v1"
    ):
        apply_verified_mutation(
            duplicate,
            CylinderMetamorphMutation("Cylinder2", "length-three"),
        )


def test_local_edits_require_only_the_records_and_tokens_they_consume() -> None:
    source = (
        compile_cube()
        .replace(b"ID=1\r\n", b"ID=1\r\nID=99\r\n", 1)
        .replace(b"GroupID=0\r\n", b"GroupID=0\r\nGroupID=99\r\n", 1)
        .replace(
            b"Transform=50.00000 50.00000 50.00000",
            b"Transform=bad 50.00000 50.00000",
            1,
        )
    )

    result = apply_verified_mutation(
        source,
        ObjectMutation(
            "Cube2", position=Vector3(D("1"), D("2"), D("3"))
        ),
    )

    assert result.changed is True
    assert [item["token_index"] for item in result.differences] == [9, 10, 11]


def test_color_density_can_replace_an_unparseable_existing_value() -> None:
    source = compile_cube().replace(b"GradDensity=1.000", b"GradDensity=bad")

    result = apply_verified_mutation(
        source, ObjectMutation("Cube2", color_density=D("0.5"))
    )

    assert b"GradDensity=0.500" in result.data


def test_sphere_profile_does_not_depend_on_transform_parseability() -> None:
    source = compile_sphere().replace(
        b"Transform=50.00000 50.00000 50.00000",
        b"Transform=bad 50.00000 50.00000",
        1,
    )

    result = apply_verified_mutation(
        source, SphereMetamorphMutation("Sphere2", "cushion-core")
    )

    assert result.changed is True


def test_whole_scene_operations_keep_holon_index_order() -> None:
    source = compile_project(ProjectSpec(objects=(CubeSpec(), CubeSpec())))
    reordered_indexes = (
        source.replace(b"Holon\\1", b"Holon\\99")
        .replace(b"Holon\\2", b"Holon\\1")
        .replace(b"Holon\\99", b"Holon\\2")
    )

    result = apply_verified_mutation(
        reordered_indexes, CenteredRowMutation(spacing=D("10"))
    )

    assert result.object_names == ("Cube3", "Cube2")
