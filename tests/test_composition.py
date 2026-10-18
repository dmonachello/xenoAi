from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

import xenodream_xxp.composition as composition_module
from xenodream_xxp.composition import (
    AddCube,
    AddSphere,
    CompositionError,
    StructuralChange,
    addition_capabilities,
    append_cube,
    append_sphere,
)
from xenodream_xxp.document import KeyValueRecord, SectionRecord, parse_bytes
from xenodream_xxp.generator import (
    CubeProjectSpec,
    CubeSpec,
    ThreeCubeProjectSpec,
    Vector3,
    compile_cube,
    compile_cube_project,
    compile_three_cubes,
    ProjectSpec,
    SphereSpec,
    compile_project,
)
from xenodream_xxp.mutation import ObjectMutation, apply_verified_mutation
from xenodream_xxp.scene import SceneBinding, describe_xdx_scene


D = Decimal
BINDING = SceneBinding("revision", "artifact")


def _value(data: bytes, section: bytes, key: bytes) -> bytes:
    matches = [
        record.value
        for record in parse_bytes(data).records
        if isinstance(record, KeyValueRecord)
        and record.section == section
        and record.section_occurrence == 0
        and record.key == key
    ]
    assert len(matches) == 1
    return matches[0]


def _two_cubes() -> bytes:
    return compile_cube_project(
        CubeProjectSpec(
            cubes=(
                CubeSpec(position=Vector3(D("-50"), D("0"), D("0"))),
                CubeSpec(position=Vector3(D("50"), D("0"), D("0"))),
            )
        )
    )


def test_append_cube_allocates_cube3_and_preserves_the_existing_cube() -> None:
    source = apply_verified_mutation(
        compile_cube(),
        ObjectMutation(
            "Cube2",
            scale=Vector3(D("25"), D("50"), D("75")),
            position=Vector3(D("10"), D("20"), D("30")),
            face_warp=D("0.25"),
        ),
    ).data

    rewrite = append_cube(
        source,
        AddCube(position=Vector3(D("75"), D("0"), D("0"))),
    )

    assert rewrite.added.id == 2
    assert rewrite.added.holon_index == 2
    assert rewrite.added.name == "Cube3"
    assert rewrite.added.group_id == 0
    assert rewrite.added.constructor == "Cube"
    assert rewrite.structural_changes == (
        StructuralChange("section_added", "Holon\\2", 0, 30),
        StructuralChange("section_added", "Holon\\2\\MM\\0", 0, 9),
    )
    assert _value(rewrite.data, b"Header", b"NumHolons") == b"3"
    assert _value(rewrite.data, b"Holon\\1", b"Transform") == _value(
        source, b"Holon\\1", b"Transform"
    )
    assert _value(rewrite.data, b"Holon\\1\\MM\\0", b"Pars") == _value(
        source, b"Holon\\1\\MM\\0", b"Pars"
    )
    assert _value(rewrite.data, b"Holon\\2", b"Transform").split()[9:12] == [
        b"75.00000",
        b"0.00000",
        b"0.00000",
    ]
    scene = describe_xdx_scene(rewrite.data, BINDING)
    assert [node.name for node in scene.nodes] == ["Group1", "Cube2", "Cube3"]
    assert scene.diagnostics == ()


def test_append_sphere_allocates_sphere3_and_matches_canonical_output() -> None:
    source = apply_verified_mutation(
        compile_cube(),
        ObjectMutation("Cube2", position=Vector3(D("-50"), D("0"), D("0"))),
    ).data

    rewrite = append_sphere(
        source,
        AddSphere(position=Vector3(D("50"), D("0"), D("0"))),
    )

    assert rewrite.data == compile_project(
        ProjectSpec(
            objects=(
                CubeSpec(position=Vector3(D("-50"), D("0"), D("0"))),
                SphereSpec(position=Vector3(D("50"), D("0"), D("0"))),
            )
        )
    )
    assert rewrite.added.name == "Sphere3"
    assert rewrite.added.constructor == "Sphere"
    assert rewrite.structural_changes == (
        StructuralChange("section_added", "Holon\\2", 0, 30),
        StructuralChange("section_added", "Holon\\2\\MM\\0", 0, 9),
    )
    scene = describe_xdx_scene(rewrite.data, BINDING)
    assert [node.name for node in scene.nodes] == ["Group1", "Cube2", "Sphere3"]
    assert scene.nodes[-1].constructor == "Sphere"
    assert scene.diagnostics == ()


def test_append_sphere_preserves_admitted_cube_edits_and_rejects_two_cubes() -> None:
    source = apply_verified_mutation(
        compile_cube(),
        ObjectMutation(
            "Cube2",
            scale=Vector3(D("25"), D("50"), D("75")),
            position=Vector3(D("10"), D("20"), D("30")),
            face_warp=D("0.25"),
        ),
    ).data
    rewrite = append_sphere(
        source,
        AddSphere(position=Vector3(D("75"), D("0"), D("0"))),
    )
    assert _value(rewrite.data, b"Holon\\1", b"Transform") == _value(
        source, b"Holon\\1", b"Transform"
    )
    assert _value(rewrite.data, b"Holon\\1\\MM\\0", b"Pars") == _value(
        source, b"Holon\\1\\MM\\0", b"Pars"
    )

    with pytest.raises(CompositionError, match="exactly one existing Cube"):
        append_sphere(_two_cubes(), AddSphere(position=Vector3()))


def test_addition_capabilities_are_derived_from_writer_admission() -> None:
    one = addition_capabilities(compile_cube(), BINDING)
    assert [offer.operation for offer in one.available] == [
        "add-cube-v1", "add-sphere-v1"
    ]
    assert one.blockers == ()

    two = addition_capabilities(_two_cubes(), BINDING)
    assert [offer.operation for offer in two.available] == ["add-cube-v1"]
    assert [blocker.operation for blocker in two.blockers] == ["add-sphere-v1"]

    three = addition_capabilities(compile_three_cubes(), BINDING)
    assert three.available == ()
    assert [blocker.operation for blocker in three.blockers] == [
        "add-cube-v1", "add-sphere-v1"
    ]


def test_append_cube_allocates_cube4_from_the_two_cube_profile() -> None:
    source = _two_cubes()

    rewrite = append_cube(
        source,
        AddCube(position=Vector3(D("100"), D("5"), D("-5"))),
    )

    assert rewrite.added.id == 3
    assert rewrite.added.holon_index == 3
    assert rewrite.added.name == "Cube4"
    assert rewrite.structural_changes == (
        StructuralChange("section_added", "Holon\\3", 0, 30),
        StructuralChange("section_added", "Holon\\3\\MM\\0", 0, 9),
    )
    assert _value(rewrite.data, b"Header", b"NumHolons") == b"4"
    assert _value(rewrite.data, b"Holon\\3", b"Transform").split()[9:12] == [
        b"100.00000",
        b"5.00000",
        b"-5.00000",
    ]
    assert [
        record.name
        for record in parse_bytes(rewrite.data).records
        if isinstance(record, SectionRecord)
    ][:8] == [
        b"Header",
        b"Holon\\0",
        b"Holon\\1",
        b"Holon\\1\\MM\\0",
        b"Holon\\2",
        b"Holon\\2\\MM\\0",
        b"Holon\\3",
        b"Holon\\3\\MM\\0",
    ]
    assert describe_xdx_scene(rewrite.data, BINDING).diagnostics == ()


def test_append_cube_one_to_two_matches_the_canonical_compiler_output() -> None:
    source = apply_verified_mutation(
        compile_cube(),
        ObjectMutation("Cube2", position=Vector3(D("-50"), D("0"), D("0"))),
    ).data

    rewrite = append_cube(
        source,
        AddCube(position=Vector3(D("50"), D("0"), D("0"))),
    )

    assert rewrite.data == _two_cubes()


def test_append_cube_two_to_three_matches_the_canonical_compiler_output() -> None:
    source = apply_verified_mutation(
        _two_cubes(),
        ObjectMutation("Cube2", position=Vector3(D("-75"), D("0"), D("0"))),
    ).data
    source = apply_verified_mutation(
        source,
        ObjectMutation("Cube3", position=Vector3(D("0"), D("0"), D("0"))),
    ).data

    rewrite = append_cube(
        source,
        AddCube(position=Vector3(D("75"), D("0"), D("0"))),
    )

    assert rewrite.data == compile_three_cubes(ThreeCubeProjectSpec())


def test_append_cube_rejects_three_cubes_and_noncanonical_structure() -> None:
    with pytest.raises(CompositionError, match="one or two"):
        append_cube(
            compile_three_cubes(ThreeCubeProjectSpec()),
            AddCube(position=Vector3()),
        )

    source = parse_bytes(compile_cube())
    records = list(source.records)
    index = next(
        index
        for index, record in enumerate(records)
        if isinstance(record, KeyValueRecord)
        and record.section == b"Material\\0"
        and record.key == b"Name"
    )
    record = records[index]
    assert isinstance(record, KeyValueRecord)
    records[index] = replace(
        record,
        content=b"Name=Changed",
        value=b"Changed",
    )
    changed = source.__class__(tuple(records)).to_bytes()
    with pytest.raises(CompositionError, match="canonical flat Cube profile"):
        append_cube(changed, AddCube(position=Vector3()))


def test_append_cube_rejects_position_that_requires_rounding() -> None:
    with pytest.raises(CompositionError, match="five-place precision"):
        append_cube(
            compile_cube(),
            AddCube(position=Vector3(D("0.000001"), D("0"), D("0"))),
        )


def test_structural_audit_rejects_an_extra_inserted_record_change(monkeypatch) -> None:
    original = composition_module._positioned_span

    def corrupt_span(context, position):
        records = list(original(context, position))
        index = next(
            index
            for index, record in enumerate(records)
            if isinstance(record, KeyValueRecord)
            and record.section == b"Holon\\2\\MM\\0"
            and record.key == b"Combine"
        )
        record = records[index]
        assert isinstance(record, KeyValueRecord)
        records[index] = replace(record, content=b"Combine=1", value=b"1")
        return tuple(records)

    monkeypatch.setattr(composition_module, "_positioned_span", corrupt_span)
    with pytest.raises(CompositionError, match="canonical target span"):
        append_cube(
            compile_cube(),
            AddCube(position=Vector3(D("75"), D("0"), D("0"))),
        )
