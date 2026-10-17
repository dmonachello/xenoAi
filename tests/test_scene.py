from __future__ import annotations

from copy import deepcopy
from decimal import Decimal

from xenodream_xxp.generator import (
    CubeSpec,
    ProjectSpec,
    SphereSpec,
    compile_cube,
    compile_cylinder,
    compile_project,
    compile_sphere,
)
from xenodream_xxp.scene import (
    Recognition,
    SceneBinding,
    SceneDescriptionError,
    SceneOperation,
    describe_xdx_scene,
    scene_description_to_dict,
)
from xenodream_xxp.metamorph import load_metamorph_registry
import xenodream_xxp.scene as scene_module
from xenodream_xxp.mutation import MutationError, ObjectMutation, apply_verified_mutation
from xenodream_xxp.generator import Vector3
import pytest


BINDING = SceneBinding("a" * 64, "b" * 64)


def _opaque_sphere_neighbor() -> bytes:
    return compile_project(
        ProjectSpec(objects=(CubeSpec(), SphereSpec()))
    ).replace(b"Style=1", b"Style=999", 1)


def test_describes_verified_scene_without_normalizing_source() -> None:
    source = compile_sphere()

    scene = describe_xdx_scene(source, BINDING)

    assert scene.binding == BINDING
    assert scene.xdx_version == "1.220"
    assert scene.declared_holon_count == 2
    assert [node.holon_index for node in scene.nodes] == [0, 1]
    assert [node.section_ordinal for node in scene.nodes] == [0, 1]
    assert scene.nodes[0].group_id == 0
    sphere = scene.nodes[1]
    assert sphere.id == 1
    assert sphere.group_id == 0
    assert sphere.constructor == "Sphere"
    assert sphere.recognition is Recognition.VERIFIED
    assert sphere.transform is not None
    assert sphere.transform.scale.x == Decimal("50.00000")
    assert sphere.allowed_operations == (
        SceneOperation.SET_SCALE,
        SceneOperation.SET_POSITION,
        SceneOperation.APPLY_SPHERE_PROFILE,
    )
    assert sphere.metamorphs[0].metamorph_index == 0
    assert sphere.metamorphs[0].parameters[0].name == "Warp"
    assert sphere.metamorphs[0].parameters[0].raw == "0.00000"
    assert source == compile_sphere()


def test_recognizes_cylinder_but_does_not_infer_transform_writes() -> None:
    scene = describe_xdx_scene(compile_cylinder(), BINDING)
    cylinder = scene.nodes[1]

    assert cylinder.constructor == "Cylinder"
    assert cylinder.allowed_operations == (
        SceneOperation.APPLY_CYLINDER_PROFILE,
    )


def test_keeps_an_opaque_neighbor_visible_without_blocking_known_capabilities() -> None:
    scene = describe_xdx_scene(_opaque_sphere_neighbor(), BINDING)

    cube, opaque = scene.nodes[1:]
    assert cube.constructor == "Cube"
    assert SceneOperation.SET_POSITION in cube.allowed_operations
    assert opaque.name == "Sphere3"
    assert opaque.constructor is None
    assert opaque.recognition is Recognition.UNKNOWN
    assert opaque.allowed_operations == ()
    assert opaque.metamorphs[0].style == 999


def test_description_reports_partial_structure_in_physical_order() -> None:
    source = compile_cube().replace(b"NumHolons=2", b"NumHolons=4")
    scene = describe_xdx_scene(source, BINDING)
    result = scene_description_to_dict(scene)

    assert list(result) == [
        "schema",
        "binding",
        "xdx_version",
        "declared_holon_count",
        "nodes",
        "diagnostics",
    ]
    assert [node["holon_index"] for node in result["nodes"]] == [0, 1]
    assert [node["section_ordinal"] for node in result["nodes"]] == [0, 1]
    assert "ordinal" not in result["nodes"][1]
    assert "parent_id" not in result["nodes"][1]
    assert result["nodes"][1]["transform"]["scale"] == ["50.00000"] * 3
    assert any(
        item["code"] == "holon-count-mismatch"
        for item in result["diagnostics"]
    )
    assert list(result["diagnostics"][0]) == [
        "code",
        "message",
        "section",
        "holon_index",
        "section_occurrence",
        "section_ordinal",
    ]


def test_historical_scene_does_not_advertise_writes() -> None:
    source = compile_cube().replace(b"Progversion=1.220", b"Progversion=1.007")
    scene = describe_xdx_scene(source, BINDING)

    assert scene.nodes[1].constructor is None
    assert scene.nodes[1].transform is None
    assert scene.nodes[1].allowed_operations == ()


def test_non_ascii_name_remains_visible_but_is_not_a_write_target() -> None:
    source = compile_cube().replace(b"Name=Cube2", b"Name=Cube\xff")

    cube = describe_xdx_scene(source, BINDING).nodes[1]

    assert cube.name == "Cube\\xff"
    assert "non-ascii-name" in cube.write_blockers
    assert cube.allowed_operations == ()
    with pytest.raises(MutationError, match="does not support set-position-v1"):
        apply_verified_mutation(
            source,
            ObjectMutation(
                "Cube\\xff",
                position=Vector3(
                    Decimal("1"), Decimal("0"), Decimal("0")
                ),
            ),
        )


def test_duplicate_name_across_known_and_opaque_nodes_blocks_name_writes() -> None:
    source = _opaque_sphere_neighbor().replace(b"Name=Sphere3", b"Name=Cube2")
    scene = describe_xdx_scene(source, BINDING)

    assert scene.nodes[1].constructor == "Cube"
    assert scene.nodes[1].allowed_operations == ()
    assert "duplicate-name" in scene.nodes[1].write_blockers
    assert scene.nodes[2].allowed_operations == ()
    with pytest.raises(MutationError, match="matched 2 objects"):
        apply_verified_mutation(
            source,
            ObjectMutation(
                "Cube2",
                position=Vector3(
                    Decimal("1"), Decimal("0"), Decimal("0")
                ),
            ),
        )


def test_duplicate_holon_section_keeps_occurrences_distinct_and_suppresses_writes() -> None:
    source = compile_cube()
    block_start = source.index(b"[Holon\\1]")
    block_end = source.index(b"[Gradients]")
    duplicate = (
        source[:block_end].replace(b"NumHolons=2", b"NumHolons=3")
        + source[block_start:block_end]
        + source[block_end:]
    )

    scene = describe_xdx_scene(duplicate, BINDING)
    duplicates = [node for node in scene.nodes if node.holon_index == 1]

    assert [node.section_occurrence for node in duplicates] == [0, 1]
    assert all(node.allowed_operations == () for node in duplicates)
    assert all(
        "ambiguous-metamorph-ownership" in node.write_blockers
        for node in duplicates
    )
    assert any(
        item.code == "ambiguous-metamorph-owner"
        for item in scene.diagnostics
    )


def test_duplicate_target_field_suppresses_only_that_nodes_writes() -> None:
    source = compile_cube().replace(
        b"Name=Cube2\r\n", b"Name=Cube2\r\nName=Alias\r\n"
    )
    scene = describe_xdx_scene(source, BINDING)

    cube = scene.nodes[1]
    assert cube.name is None
    assert cube.allowed_operations == ()
    assert "duplicate-or-missing-Name" in cube.write_blockers
    diagnostic = next(
        item for item in scene.diagnostics
        if item.code == "duplicate-node-field"
    )
    assert diagnostic.holon_index == 1
    assert diagnostic.section_occurrence == 0
    assert diagnostic.section_ordinal == 1


def test_invalid_metamorph_schema_does_not_expose_operation_name() -> None:
    source = compile_cube().replace(
        b"Pars=0.0000 0 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0 ",
        b"Pars=0.0000 0 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 ",
    )

    metamorph = describe_xdx_scene(source, BINDING).nodes[1].metamorphs[0]

    assert metamorph.schema_verified is False
    assert metamorph.operation_name is None
    assert any(
        item.code == "metamorph-count-mismatch"
        for item in describe_xdx_scene(source, BINDING).diagnostics
    )


def test_orphan_metamorph_is_reported_instead_of_disappearing() -> None:
    source = compile_cube() + (
        b"[Holon\\99\\MM\\0]\r\n"
        b"Style=5\r\n"
        b"NumPars=9\r\n"
        b"Pars=0 0 0 0 0 0 0 0 0 \r\n"
    )

    scene = describe_xdx_scene(source, BINDING)

    diagnostic = next(
        item for item in scene.diagnostics if item.code == "orphan-metamorph"
    )
    assert diagnostic.holon_index == 99
    assert diagnostic.section_occurrence == 0
    assert diagnostic.section_ordinal == 1


def test_transform_slices_are_independent_and_malformed_shape_is_diagnosed() -> None:
    source = compile_cube().replace(
        b"Transform=50.00000 50.00000 50.00000",
        b"Transform=bad 50.00000 50.00000",
        1,
    )

    scene = describe_xdx_scene(source, BINDING)
    transform = scene.nodes[1].transform

    assert transform is not None
    assert transform.scale is None
    assert transform.rotation is not None
    assert transform.position is not None
    assert transform.raw_tokens[0] == "bad"
    assert any(item.code == "malformed-transform" for item in scene.diagnostics)


def test_malformed_metamorph_parameter_and_unresolved_group_are_diagnosed() -> None:
    source = (
        compile_cube()
        .replace(b"Pars=0.0000 0 ", b"Pars=junk 0 ", 1)
        .replace(b"GroupID=0\r\nType=1", b"GroupID=99\r\nType=1", 1)
    )

    scene = describe_xdx_scene(source, BINDING)
    codes = [item.code for item in scene.diagnostics]

    assert "malformed-metamorph-parameter" in codes
    assert "unresolved-group-id" in codes
    assert codes == sorted(codes)


def test_missing_group_fact_is_diagnosed_without_blocking_local_edit() -> None:
    source = compile_cube().replace(b"GroupID=0\r\nType=1", b"Type=1", 1)

    scene = describe_xdx_scene(source, BINDING)
    cube = scene.nodes[1]

    assert any(
        item.code == "missing-node-field" and item.holon_index == 1
        for item in scene.diagnostics
    )
    assert SceneOperation.SET_POSITION in cube.allowed_operations


@pytest.mark.parametrize("key", [b"Program", b"Progversion"])
def test_non_ascii_required_header_is_fatal(key: bytes) -> None:
    source = compile_cube()
    old = b"Program=XDX" if key == b"Program" else b"Progversion=1.220"
    new = b"Program=XD\xff" if key == b"Program" else b"Progversion=1.22\xff"

    with pytest.raises(SceneDescriptionError, match="ASCII"):
        describe_xdx_scene(source.replace(old, new), BINDING)


def test_constructor_recognition_requires_constructor_registry_role(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = deepcopy(load_metamorph_registry())
    cube = next(item for item in registry["operations"] if item["name"] == "Cube")
    cube["role"] = "modifier"
    monkeypatch.setattr(
        scene_module, "load_metamorph_registry", lambda: registry
    )

    node = describe_xdx_scene(compile_cube(), BINDING).nodes[1]

    assert node.constructor is None
    assert node.allowed_operations == ()
