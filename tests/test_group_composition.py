from __future__ import annotations

from xenodream_xxp.cli import main
from xenodream_xxp.composition import (
    AddEmptyGroup,
    ConfigureGroup3,
    Group3Profile,
    append_empty_group,
    configure_group3,
)
from xenodream_xxp.generator import compile_cube
from xenodream_xxp.mutation import apply_verified_mutation
from xenodream_xxp.mutation import MutationError
from xenodream_xxp.scene import SceneBinding, describe_xdx_scene
from xenodream_xxp.workspace import ProjectWorkspace


BINDING = SceneBinding("a" * 64, "b" * 64)


def _source() -> bytes:
    return append_empty_group(compile_cube(), AddEmptyGroup()).data


def test_configure_group3_changes_only_membership_and_group_scale() -> None:
    result = configure_group3(
        _source(),
        ConfigureGroup3(Group3Profile.STRETCH_X_20),
    )

    assert [
        (item["section"], item["key"], item.get("token_index"))
        for item in result.differences
    ] == [
        ("Holon\\1", "GroupID", None),
        ("Holon\\2", "Transform", 0),
        ("Holon\\2", "Transform", 1),
        ("Holon\\2", "Transform", 2),
    ]
    assert result.grouped.object_id == 1
    assert result.grouped.object_name == "Cube2"
    assert result.grouped.group_id == 2
    assert result.grouped.group_name == "Group3"
    scene = describe_xdx_scene(result.data, BINDING)
    assert scene.nodes[1].group_id == 2
    assert scene.nodes[2].id == 2


def test_configure_group3_is_idempotent_and_can_update_profile() -> None:
    first = configure_group3(
        _source(), ConfigureGroup3(Group3Profile.STRETCH_X_20)
    )
    same = configure_group3(
        first.data, ConfigureGroup3(Group3Profile.STRETCH_X_20)
    )
    changed = configure_group3(
        first.data, ConfigureGroup3(Group3Profile.GROUPED)
    )

    assert same.data == first.data
    assert same.differences == ()
    assert [item["token_index"] for item in changed.differences] == [0]


def test_group3_operation_uses_verified_mutation_and_workspace_revision(tmp_path) -> None:
    operation = ConfigureGroup3(Group3Profile.STRETCH_X_20)
    mutation = apply_verified_mutation(_source(), operation)

    assert mutation.changed is True
    assert mutation.native_validation_required is True
    assert mutation.fabrication_suitable is False
    assert mutation.grouped is not None

    source = tmp_path / "group.xxp"
    source.write_bytes(_source())
    workspace = ProjectWorkspace.create(tmp_path / "group.xsp", source)
    applied = workspace.apply(operation, message="group Cube2")
    assert applied.created is True
    assert applied.revision.operation == "configure-group3-v1"
    assert applied.revision.details["native_validation_required"] is True


def test_group_cube2_cli_reports_exact_relationship(tmp_path, capsys) -> None:
    source = tmp_path / "group.xxp"
    source.write_bytes(_source())
    workspace = tmp_path / "group.xsp"
    ProjectWorkspace.create(workspace, source)

    assert main(
        [
            "project",
            "group-cube2",
            str(workspace),
            "--profile",
            "stretch-x-20",
            "--message",
            "group Cube2",
        ]
    ) == 0

    result = __import__("json").loads(capsys.readouterr().out)
    assert result["created"] is True
    assert result["grouped"] == {
        "group_id": 2,
        "group_name": "Group3",
        "object_id": 1,
        "object_name": "Cube2",
    }
    assert result["native_validation_required"] is True
    assert result["fabrication_suitable"] is False


def test_group3_rejects_a_noncanonical_neighbor_without_writing(tmp_path) -> None:
    source = _source().replace(b"Name=Cube2\r\n", b"Name=Other\r\n", 1)
    artifact = tmp_path / "other.xxp"
    artifact.write_bytes(source)
    workspace = ProjectWorkspace.create(tmp_path / "other.xsp", artifact)
    before = workspace.status()

    try:
        workspace.apply(
            ConfigureGroup3(Group3Profile.GROUPED), message="must reject"
        )
    except MutationError:
        pass
    else:
        raise AssertionError("noncanonical scene was accepted")

    after = workspace.status()
    assert after.head.id == before.head.id
    assert after.head.artifact_sha256 == before.head.artifact_sha256
    assert tuple(workspace.history()) == (before.head,)


def test_group3_profile_type_is_closed() -> None:
    try:
        ConfigureGroup3("100-percent")  # type: ignore[arg-type]
    except TypeError as error:
        assert str(error) == "profile must be Group3Profile"
    else:
        raise AssertionError("unmeasured group profile was accepted")
