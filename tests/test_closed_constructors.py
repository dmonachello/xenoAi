from __future__ import annotations

from decimal import Decimal
from hashlib import sha256

from xenodream_xxp.cli import main
from xenodream_xxp.diffing import diff_documents
from xenodream_xxp.document import parse_bytes
from xenodream_xxp.generator import (
    ClosedConstructorName,
    ClosedConstructorSpec,
    Vector3,
    compile_closed_constructor,
)
from xenodream_xxp.mutation import ObjectMutation, apply_verified_mutation
from xenodream_xxp.scene import SceneBinding, SceneOperation, describe_xdx_scene
from xenodream_xxp.workspace import ProjectWorkspace


D = Decimal
BINDING = SceneBinding("a" * 64, "b" * 64)
EXPECTED = {
    ClosedConstructorName.ROUND_CUBE: (
        "9be76e32e36f9a98ba3295f38b7089aa94838681f4763470492f7ddd2b969da5",
        "RoundCube2",
    ),
    ClosedConstructorName.PIPE: (
        "2e28e99d702130ac93f248681ac255b430187a530467c39ffc95e985039342cd",
        "Pipe2",
    ),
    ClosedConstructorName.TORUS: (
        "c32c4dff9a2f946a4800aae7d689e4c18a3f07d57b3e8d95df8e78b224014ba7",
        "Torus2",
    ),
    ClosedConstructorName.COG: (
        "fe74b398d7b55d671ff1f86d326c90213ca04ef0eb5eb283c5a4e482a7911017",
        "Cog2",
    ),
    ClosedConstructorName.SPIRAL_SHELL: (
        "f75d94cf2db8e630439f1df50f04ab6dd3fcb8dabf1817418b3d19ac75cb6012",
        "SpiralShell2",
    ),
}


def test_default_closed_constructors_match_native_evaluated_candidates() -> None:
    for constructor, (digest, object_name) in EXPECTED.items():
        data = compile_closed_constructor(ClosedConstructorSpec(constructor))

        assert sha256(data).hexdigest() == digest
        scene = describe_xdx_scene(data, BINDING)
        node = scene.nodes[1]
        assert node.name == object_name
        assert node.constructor == constructor.value
        assert node.allowed_operations == (
            SceneOperation.SET_SCALE,
            SceneOperation.SET_POSITION,
        )


def test_closed_constructor_transform_changes_only_requested_tokens() -> None:
    for constructor in ClosedConstructorName:
        baseline = compile_closed_constructor(ClosedConstructorSpec(constructor))
        changed = compile_closed_constructor(
            ClosedConstructorSpec(
                constructor,
                scale=Vector3(D("40"), D("55"), D("65")),
                position=Vector3(D("15"), D("-10"), D("20")),
            )
        )

        assert [
            (item["section"], item["key"], item.get("token_index"))
            for item in diff_documents(parse_bytes(baseline), parse_bytes(changed))
        ] == [
            ("Holon\\1", "Transform", 0),
            ("Holon\\1", "Transform", 1),
            ("Holon\\1", "Transform", 2),
            ("Holon\\1", "Transform", 9),
            ("Holon\\1", "Transform", 10),
            ("Holon\\1", "Transform", 11),
        ]


def test_closed_constructor_uses_existing_object_mutation_authority() -> None:
    for constructor, (_, object_name) in EXPECTED.items():
        source = compile_closed_constructor(ClosedConstructorSpec(constructor))
        result = apply_verified_mutation(
            source,
            ObjectMutation(object_name, position=Vector3(D("25"), D("0"), D("5"))),
        )

        assert result.changed is True
        assert result.object_names == (object_name,)
        assert [item["token_index"] for item in result.differences] == [9, 11]
        assert result.native_validation_required is True
        assert result.fabrication_suitable is False


def test_unverified_constructor_parameter_vector_suppresses_write_capabilities() -> None:
    source = compile_closed_constructor(
        ClosedConstructorSpec(ClosedConstructorName.TORUS)
    ).replace(
        b"Pars=25.00 360.00 0 0.00 16 0 0 0 0.000 0 0.0 ",
        b"Pars=26.00 360.00 0 0.00 16 0 0 0 0.000 0 0.0 ",
        1,
    )

    node = describe_xdx_scene(source, BINDING).nodes[1]
    assert node.name == "Torus2"
    assert node.constructor is None
    assert node.allowed_operations == ()


def test_generate_constructor_cli_writes_exact_typed_artifact(tmp_path, capsys) -> None:
    output = tmp_path / "torus.xxp"

    assert main(
        [
            "generate-constructor",
            "Torus",
            str(output),
            "--scale",
            "40",
            "55",
            "65",
            "--position",
            "15",
            "-10",
            "20",
        ]
    ) == 0

    result = __import__("json").loads(capsys.readouterr().out)
    assert result["constructor"] == "Torus"
    assert result["native_validation_required"] is True
    assert result["fabrication_suitable"] is False
    assert output.read_bytes() == compile_closed_constructor(
        ClosedConstructorSpec(
            ClosedConstructorName.TORUS,
            scale=Vector3(D("40"), D("55"), D("65")),
            position=Vector3(D("15"), D("-10"), D("20")),
        )
    )


def test_closed_constructor_workspace_revision_requires_native_validation(tmp_path) -> None:
    source = tmp_path / "pipe.xxp"
    source.write_bytes(
        compile_closed_constructor(ClosedConstructorSpec(ClosedConstructorName.PIPE))
    )
    workspace = ProjectWorkspace.create(tmp_path / "pipe.xsp", source)

    applied = workspace.apply(
        ObjectMutation("Pipe2", position=Vector3(D("25"), D("0"), D("5"))),
        message="move Pipe",
        prompt="set object Pipe2 position to 25 0 5",
    )

    assert applied.created is True
    assert applied.mutation is not None
    assert applied.mutation.native_validation_required is True
    assert applied.revision.details["native_validation_required"] is True
    assert applied.revision.details["fabrication_suitable"] is False
