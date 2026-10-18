from __future__ import annotations

from decimal import Decimal
import json

from xenodream_xxp.document import parse_bytes
from xenodream_xxp.cli import main
from xenodream_xxp.generator import ClosedConstructorName, Vector3
from xenodream_xxp.multi_spiral import (
    InteractingSpiralProfile,
    InteractingSpiralsSpec,
    compile_interacting_spirals,
    interacting_spiral_members,
)
from xenodream_xxp.scene import (
    Recognition,
    SceneBinding,
    SceneOperation,
    describe_xdx_scene,
)


D = Decimal
BINDING = SceneBinding("a" * 64, "b" * 64)


def test_interleaved_eight_profile_is_a_closed_exact_domain_value() -> None:
    spec = InteractingSpiralsSpec()

    assert spec.profile is InteractingSpiralProfile.INTERLEAVED_EIGHT_V1
    assert [
        (member.holon_index, member.constructor, member.scale, member.position)
        for member in interacting_spiral_members(spec)
    ] == [
        (1, ClosedConstructorName.SPIRAL_SHELL, Vector3(D("28"), D("28"), D("28")), Vector3(D("28"), D("0"), D("-30"))),
        (2, ClosedConstructorName.TORUS, Vector3(D("26"), D("26"), D("26")), Vector3(D("-28"), D("0"), D("-30"))),
        (3, ClosedConstructorName.COG, Vector3(D("25"), D("25"), D("25")), Vector3(D("0"), D("28"), D("-10"))),
        (4, ClosedConstructorName.PIPE, Vector3(D("27"), D("27"), D("27")), Vector3(D("0"), D("-28"), D("-10"))),
        (5, ClosedConstructorName.ROUND_CUBE, Vector3(D("24"), D("24"), D("24")), Vector3(D("-28"), D("0"), D("10"))),
        (6, ClosedConstructorName.SPIRAL_SHELL, Vector3(D("30"), D("30"), D("30")), Vector3(D("28"), D("0"), D("10"))),
        (7, ClosedConstructorName.PIPE, Vector3(D("26"), D("26"), D("26")), Vector3(D("0"), D("-28"), D("30"))),
        (8, ClosedConstructorName.COG, Vector3(D("25"), D("25"), D("25")), Vector3(D("0"), D("28"), D("30"))),
    ]


def test_compiled_interacting_spirals_have_exact_verified_scene_shape() -> None:
    data = compile_interacting_spirals()

    assert parse_bytes(data).to_bytes() == data
    scene = describe_xdx_scene(data, BINDING)
    assert scene.xdx_version == "1.220"
    assert scene.declared_holon_count == 9
    assert scene.diagnostics == ()
    assert [node.name for node in scene.nodes] == [
        "Group1",
        "SpiralShell2",
        "Torus3",
        "Cog4",
        "Pipe5",
        "RoundCube6",
        "SpiralShell7",
        "Pipe8",
        "Cog9",
    ]

    members = interacting_spiral_members(InteractingSpiralsSpec())
    for node, member in zip(scene.nodes[1:], members):
        assert node.id == member.holon_index
        assert node.holon_index == member.holon_index
        assert node.group_id == 0
        assert node.constructor == member.constructor.value
        assert node.recognition is Recognition.VERIFIED
        assert node.allowed_operations == (
            SceneOperation.SET_SCALE,
            SceneOperation.SET_POSITION,
        )


def test_generate_interacting_spirals_cli_writes_exact_artifact(
    tmp_path, capsys
) -> None:
    output = tmp_path / "interacting-spirals.xxp"

    assert main(["generate-interacting-spirals", str(output)]) == 0

    result = json.loads(capsys.readouterr().out)
    assert result["member_count"] == 8
    assert result["native_validation_required"] is True
    assert result["fabrication_suitable"] is False
    assert output.read_bytes() == compile_interacting_spirals()
