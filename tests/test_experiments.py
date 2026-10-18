from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from pathlib import Path

from xenodream_xxp.diffing import diff_documents
from xenodream_xxp.document import (
    Document,
    KeyValueRecord,
    SectionRecord,
    parse_bytes,
)


PAIR = Path(__file__).parents[1] / "experiments" / "scale-x"
Y_PAIR = Path(__file__).parents[1] / "experiments" / "scale-y"
Z_PAIR = Path(__file__).parents[1] / "experiments" / "scale-z"
X_POSITION_PAIR = Path(__file__).parents[1] / "experiments" / "position-x"
Y_POSITION_PAIR = Path(__file__).parents[1] / "experiments" / "position-y"
Z_POSITION_PAIR = Path(__file__).parents[1] / "experiments" / "position-z"
X_ROTATION_PAIR = Path(__file__).parents[1] / "experiments" / "rotation-x"
Y_ROTATION_PAIR = Path(__file__).parents[1] / "experiments" / "rotation-y"
Z_ROTATION_PAIR = Path(__file__).parents[1] / "experiments" / "rotation-z"
GROUP_Y_ROTATION_PAIR = (
    Path(__file__).parents[1] / "experiments" / "rotation-y-group"
)
GROUP_Z_ROTATION_PAIR = (
    Path(__file__).parents[1] / "experiments" / "rotation-z-group"
)
GROUP_COLOR_DENSITY_PAIR = (
    Path(__file__).parents[1] / "experiments" / "color-density-group"
)
COLOR_DENSITY_PAIR = Path(__file__).parents[1] / "experiments" / "color-density"
FACE_WARP_PAIR = (
    Path(__file__).parents[1] / "experiments" / "metamorph-face-warp"
)
GROUP_CREATION_PAIR = (
    Path(__file__).parents[1] / "experiments" / "group-creation"
)
MIDDLE_CUBE_DELETION = (
    Path(__file__).parents[1] / "experiments" / "delete-middle-cube"
)
CLEAN_MIDDLE_CUBE_DELETION = (
    Path(__file__).parents[1] / "experiments" / "delete-middle-cube-clean"
)
CUBE_SPHERE = Path(__file__).parents[1] / "experiments" / "cube-sphere"
TWO_CUBE_REFERENCE = (
    Path(__file__).parents[1]
    / "experiments"
    / "two-cube-positions"
    / "two_cubesV2.xxp"
)


def test_scale_x_pair_has_one_observed_token_change() -> None:
    base_bytes = (PAIR / "sphere_base.xxp").read_bytes()
    scaled_bytes = (PAIR / "sphere_x_scale.xxp").read_bytes()
    base = parse_bytes(base_bytes)
    scaled = parse_bytes(scaled_bytes)

    assert sha256(base_bytes).hexdigest() == (
        "b1da4b2dafa99c717f3988e4dff29bec26cbab4b6e50445c49c58a4bd3e31b32"
    )
    assert sha256(scaled_bytes).hexdigest() == (
        "841731df554bcbd1a1e5b75f48d88cac80917127b6b1bf855324d4fbaebaf3cb"
    )
    assert len(base_bytes) == len(scaled_bytes) == 3_465
    assert [
        index
        for index, (base_byte, scaled_byte) in enumerate(
            zip(base_bytes, scaled_bytes, strict=True)
        )
        if base_byte != scaled_byte
    ] == [756, 757]
    assert base.to_bytes() == base_bytes
    assert scaled.to_bytes() == scaled_bytes
    assert diff_documents(base, scaled) == [
        {
            "kind": "value_token_changed",
            "section": "Holon\\1",
            "section_occurrence": 0,
            "key": "Transform",
            "key_occurrence": 0,
            "token_index": 0,
            "before": "50.00000",
            "after": "25.00000",
        }
    ]


def test_scale_y_pair_records_transform_and_selection_spot_changes() -> None:
    base_bytes = (Y_PAIR / "sphere_base.xxp").read_bytes()
    scaled_bytes = (Y_PAIR / "sphere_y_scale.xxp").read_bytes()
    base = parse_bytes(base_bytes)
    scaled = parse_bytes(scaled_bytes)

    assert sha256(base_bytes).hexdigest() == (
        "b1da4b2dafa99c717f3988e4dff29bec26cbab4b6e50445c49c58a4bd3e31b32"
    )
    assert sha256(scaled_bytes).hexdigest() == (
        "82953ec3b813bbe452cced3fde61d7c2abf943f6fbd285aa61e3d33ead1e0b89"
    )
    assert base.to_bytes() == base_bytes
    assert scaled.to_bytes() == scaled_bytes
    differences = diff_documents(base, scaled)
    assert differences[0] == {
        "kind": "value_token_changed",
        "section": "Holon\\1",
        "section_occurrence": 0,
        "key": "Transform",
        "key_occurrence": 0,
        "token_index": 1,
        "before": "50.00000",
        "after": "25.00000",
    }
    assert differences[1]["kind"] == "value_changed"
    assert differences[1]["section"] == "SelectionSpots"
    assert differences[1]["key"] == "0"
    assert differences[1]["after"] == "3 1 1 "


def test_scale_z_pair_records_transform_and_selection_spot_changes() -> None:
    base_bytes = (Z_PAIR / "sphere_base.xxp").read_bytes()
    scaled_bytes = (Z_PAIR / "sphere_z_scale.xxp").read_bytes()
    base = parse_bytes(base_bytes)
    scaled = parse_bytes(scaled_bytes)

    assert sha256(base_bytes).hexdigest() == (
        "b1da4b2dafa99c717f3988e4dff29bec26cbab4b6e50445c49c58a4bd3e31b32"
    )
    assert sha256(scaled_bytes).hexdigest() == (
        "8bfdf805f7f2f107b8ae28465e106c96f6496376cf30c040e645ba2e7196c1ba"
    )
    assert base.to_bytes() == base_bytes
    assert scaled.to_bytes() == scaled_bytes
    differences = diff_documents(base, scaled)
    assert differences[0] == {
        "kind": "value_token_changed",
        "section": "Holon\\1",
        "section_occurrence": 0,
        "key": "Transform",
        "key_occurrence": 0,
        "token_index": 2,
        "before": "50.00000",
        "after": "25.00000",
    }
    assert differences[1]["kind"] == "value_changed"
    assert differences[1]["section"] == "SelectionSpots"
    assert differences[1]["key"] == "0"
    assert differences[1]["after"] == "3 1 1 "


def test_x_position_pair_records_transform_and_selection_spot_changes() -> None:
    base_bytes = (X_POSITION_PAIR / "sphere_base.xxp").read_bytes()
    moved_bytes = (X_POSITION_PAIR / "sphere_x_position.xxp").read_bytes()
    base = parse_bytes(base_bytes)
    moved = parse_bytes(moved_bytes)

    assert sha256(base_bytes).hexdigest() == (
        "b1da4b2dafa99c717f3988e4dff29bec26cbab4b6e50445c49c58a4bd3e31b32"
    )
    assert sha256(moved_bytes).hexdigest() == (
        "59e1f7d3bb9ea346edc68ac985c2f92b8ad683f4143539c198b77e19a83ebe5c"
    )
    assert base.to_bytes() == base_bytes
    assert moved.to_bytes() == moved_bytes
    differences = diff_documents(base, moved)
    assert differences[0] == {
        "kind": "value_token_changed",
        "section": "Holon\\1",
        "section_occurrence": 0,
        "key": "Transform",
        "key_occurrence": 0,
        "token_index": 9,
        "before": "0.00000",
        "after": "25.00000",
    }
    assert differences[1]["kind"] == "value_changed"
    assert differences[1]["section"] == "SelectionSpots"
    assert differences[1]["after"] == "3 1 1 "


def test_y_position_pair_records_transform_and_selection_spot_changes() -> None:
    base_bytes = (Y_POSITION_PAIR / "sphere_base.xxp").read_bytes()
    moved_bytes = (Y_POSITION_PAIR / "sphere_y_position.xxp").read_bytes()
    base = parse_bytes(base_bytes)
    moved = parse_bytes(moved_bytes)

    assert sha256(base_bytes).hexdigest() == (
        "b1da4b2dafa99c717f3988e4dff29bec26cbab4b6e50445c49c58a4bd3e31b32"
    )
    assert sha256(moved_bytes).hexdigest() == (
        "af358ddcaad971ecaf3cc1e1b3f913ef3c1231f8faf986a62b113dc02eeaf037"
    )
    assert base.to_bytes() == base_bytes
    assert moved.to_bytes() == moved_bytes
    differences = diff_documents(base, moved)
    assert differences[0] == {
        "kind": "value_token_changed",
        "section": "Holon\\1",
        "section_occurrence": 0,
        "key": "Transform",
        "key_occurrence": 0,
        "token_index": 10,
        "before": "0.00000",
        "after": "25.00000",
    }
    assert differences[1]["kind"] == "value_changed"
    assert differences[1]["section"] == "SelectionSpots"
    assert differences[1]["after"] == "3 1 1 "


def test_z_position_pair_records_transform_and_selection_spot_changes() -> None:
    base_bytes = (Z_POSITION_PAIR / "sphere_base.xxp").read_bytes()
    moved_bytes = (Z_POSITION_PAIR / "sphere_z_position.xxp").read_bytes()
    base = parse_bytes(base_bytes)
    moved = parse_bytes(moved_bytes)

    assert sha256(base_bytes).hexdigest() == (
        "b1da4b2dafa99c717f3988e4dff29bec26cbab4b6e50445c49c58a4bd3e31b32"
    )
    assert sha256(moved_bytes).hexdigest() == (
        "9fe95958879b1514435af815ac5bee329565e25ea1cb1fdba445fae50a60cc02"
    )
    assert base.to_bytes() == base_bytes
    assert moved.to_bytes() == moved_bytes
    differences = diff_documents(base, moved)
    assert differences[0] == {
        "kind": "value_token_changed",
        "section": "Holon\\1",
        "section_occurrence": 0,
        "key": "Transform",
        "key_occurrence": 0,
        "token_index": 11,
        "before": "0.00000",
        "after": "25.00000",
    }
    assert differences[1]["kind"] == "value_changed"
    assert differences[1]["section"] == "SelectionSpots"
    assert differences[1]["after"] == "3 1 1 "


def test_x_rotation_pair_has_one_observed_token_change() -> None:
    base_bytes = (X_ROTATION_PAIR / "cube_base.xxp").read_bytes()
    rotated_bytes = (X_ROTATION_PAIR / "cube_x_rotation.xxp").read_bytes()
    base = parse_bytes(base_bytes)
    rotated = parse_bytes(rotated_bytes)

    assert sha256(base_bytes).hexdigest() == (
        "fcba6d61f2af4cf79c1e86a20b570a0bb0039db3fb79c9d73c84e842430fc7a0"
    )
    assert sha256(rotated_bytes).hexdigest() == (
        "5e2442b52d6b27951be605cc83586b0987a0ef61ffffb5a76956d1b09d2f5961"
    )
    assert base.to_bytes() == base_bytes
    assert rotated.to_bytes() == rotated_bytes
    assert diff_documents(base, rotated) == [
        {
            "kind": "value_token_changed",
            "section": "Holon\\1",
            "section_occurrence": 0,
            "key": "Transform",
            "key_occurrence": 0,
            "token_index": 6,
            "before": "0.00000",
            "after": "30.00000",
        }
    ]


def test_y_rotation_pair_has_one_observed_token_change() -> None:
    base_bytes = (Y_ROTATION_PAIR / "cube_base.xxp").read_bytes()
    rotated_bytes = (Y_ROTATION_PAIR / "cube_y_rotation2.xxp").read_bytes()
    base = parse_bytes(base_bytes)
    rotated = parse_bytes(rotated_bytes)

    assert sha256(base_bytes).hexdigest() == (
        "fcba6d61f2af4cf79c1e86a20b570a0bb0039db3fb79c9d73c84e842430fc7a0"
    )
    assert sha256(rotated_bytes).hexdigest() == (
        "a9386cf00d4bfc6e253b8fa48d72f6338d7660d77eb56f3a86f50d541f1e8dc3"
    )
    assert base.to_bytes() == base_bytes
    assert rotated.to_bytes() == rotated_bytes
    assert diff_documents(base, rotated) == [
        {
            "kind": "value_token_changed",
            "section": "Holon\\1",
            "section_occurrence": 0,
            "key": "Transform",
            "key_occurrence": 0,
            "token_index": 7,
            "before": "0.00000",
            "after": "30.00000",
        }
    ]


def test_z_rotation_pair_has_one_observed_token_change() -> None:
    base_bytes = (Z_ROTATION_PAIR / "cube_base.xxp").read_bytes()
    rotated_bytes = (Z_ROTATION_PAIR / "cube_z_rotation2.xxp").read_bytes()
    base = parse_bytes(base_bytes)
    rotated = parse_bytes(rotated_bytes)

    assert sha256(base_bytes).hexdigest() == (
        "fcba6d61f2af4cf79c1e86a20b570a0bb0039db3fb79c9d73c84e842430fc7a0"
    )
    assert sha256(rotated_bytes).hexdigest() == (
        "42cad0adc8aa6764a456d28a9acd8bdbb01fad6814811a926fe339018de4c779"
    )
    assert base.to_bytes() == base_bytes
    assert rotated.to_bytes() == rotated_bytes
    assert diff_documents(base, rotated) == [
        {
            "kind": "value_token_changed",
            "section": "Holon\\1",
            "section_occurrence": 0,
            "key": "Transform",
            "key_occurrence": 0,
            "token_index": 8,
            "before": "0.00000",
            "after": "30.00000",
        }
    ]


def test_group_y_rotation_pair_has_one_observed_token_change() -> None:
    base_bytes = (GROUP_Y_ROTATION_PAIR / "cube_base.xxp").read_bytes()
    rotated_bytes = (
        GROUP_Y_ROTATION_PAIR / "cube_y_rotation.xxp"
    ).read_bytes()
    base = parse_bytes(base_bytes)
    rotated = parse_bytes(rotated_bytes)

    assert sha256(base_bytes).hexdigest() == (
        "fcba6d61f2af4cf79c1e86a20b570a0bb0039db3fb79c9d73c84e842430fc7a0"
    )
    assert sha256(rotated_bytes).hexdigest() == (
        "12897d040f18e75d4958a7440445ecdf95cc5f80f5236f6ab83d7ff2b1246026"
    )
    assert base.to_bytes() == base_bytes
    assert rotated.to_bytes() == rotated_bytes
    assert diff_documents(base, rotated) == [
        {
            "kind": "value_token_changed",
            "section": "Holon\\0",
            "section_occurrence": 0,
            "key": "Transform",
            "key_occurrence": 0,
            "token_index": 7,
            "before": "0.00000",
            "after": "30.00000",
        }
    ]


def test_group_z_rotation_pair_has_one_observed_token_change() -> None:
    base_bytes = (GROUP_Z_ROTATION_PAIR / "cube_base.xxp").read_bytes()
    rotated_bytes = (
        GROUP_Z_ROTATION_PAIR / "cube_z_rotation.xxp"
    ).read_bytes()
    base = parse_bytes(base_bytes)
    rotated = parse_bytes(rotated_bytes)

    assert sha256(base_bytes).hexdigest() == (
        "fcba6d61f2af4cf79c1e86a20b570a0bb0039db3fb79c9d73c84e842430fc7a0"
    )
    assert sha256(rotated_bytes).hexdigest() == (
        "9cad9d53990df84ee599407c40a5246fed54e67f2ea456a3dc425bfedc8d687b"
    )
    assert base.to_bytes() == base_bytes
    assert rotated.to_bytes() == rotated_bytes
    assert diff_documents(base, rotated) == [
        {
            "kind": "value_token_changed",
            "section": "Holon\\0",
            "section_occurrence": 0,
            "key": "Transform",
            "key_occurrence": 0,
            "token_index": 8,
            "before": "0.00000",
            "after": "30.00000",
        }
    ]


def test_group_color_density_pair_has_one_observed_value_change() -> None:
    base_bytes = (GROUP_COLOR_DENSITY_PAIR / "cube_base.xxp").read_bytes()
    changed_bytes = (
        GROUP_COLOR_DENSITY_PAIR / "cube_color_density.xxp"
    ).read_bytes()
    base = parse_bytes(base_bytes)
    changed = parse_bytes(changed_bytes)

    assert sha256(base_bytes).hexdigest() == (
        "fcba6d61f2af4cf79c1e86a20b570a0bb0039db3fb79c9d73c84e842430fc7a0"
    )
    assert sha256(changed_bytes).hexdigest() == (
        "f4efcb3ea1558383ef24f5541f072e7d3c3cfd5033dbee0c4548c10f146dea19"
    )
    assert base.to_bytes() == base_bytes
    assert changed.to_bytes() == changed_bytes
    assert diff_documents(base, changed) == [
        {
            "kind": "value_changed",
            "section": "Holon\\0",
            "section_occurrence": 0,
            "key": "GradDensity",
            "key_occurrence": 0,
            "before": "1.000",
            "after": "0.500",
        }
    ]


def test_cube_color_density_pair_has_one_observed_value_change() -> None:
    base_bytes = (COLOR_DENSITY_PAIR / "cube_base.xxp").read_bytes()
    changed_bytes = (
        COLOR_DENSITY_PAIR / "cube_color_density2.xxp"
    ).read_bytes()
    base = parse_bytes(base_bytes)
    changed = parse_bytes(changed_bytes)

    assert sha256(base_bytes).hexdigest() == (
        "fcba6d61f2af4cf79c1e86a20b570a0bb0039db3fb79c9d73c84e842430fc7a0"
    )
    assert sha256(changed_bytes).hexdigest() == (
        "87e2fb7169b01d4361840d844fb2c1e4003c872c6a9e5d7eccd28981aa9728e7"
    )
    assert base.to_bytes() == base_bytes
    assert changed.to_bytes() == changed_bytes
    assert diff_documents(base, changed) == [
        {
            "kind": "value_changed",
            "section": "Holon\\1",
            "section_occurrence": 0,
            "key": "GradDensity",
            "key_occurrence": 0,
            "before": "1.000",
            "after": "0.500",
        }
    ]


def test_cube_face_warp_pair_has_one_observed_token_change() -> None:
    base_bytes = (FACE_WARP_PAIR / "cube_base.xxp").read_bytes()
    changed_bytes = (FACE_WARP_PAIR / "cube_face_warp.xxp").read_bytes()
    base = parse_bytes(base_bytes)
    changed = parse_bytes(changed_bytes)

    assert sha256(base_bytes).hexdigest() == (
        "fcba6d61f2af4cf79c1e86a20b570a0bb0039db3fb79c9d73c84e842430fc7a0"
    )
    assert sha256(changed_bytes).hexdigest() == (
        "6c2db8fc701c1b29d96ef4028e5d5c51bc509a5c1e2b9ca50b66723bd89d7d51"
    )
    assert base.to_bytes() == base_bytes
    assert changed.to_bytes() == changed_bytes
    assert diff_documents(base, changed) == [
        {
            "kind": "value_token_changed",
            "section": "Holon\\1\\MM\\0",
            "section_occurrence": 0,
            "key": "Pars",
            "key_occurrence": 0,
            "token_index": 0,
            "before": "0.0000",
            "after": "0.2500",
        }
    ]


def test_empty_group_creation_adds_one_holon_without_changing_existing_ones() -> None:
    base_bytes = (GROUP_CREATION_PAIR / "cube_base.xxp").read_bytes()
    changed_bytes = (GROUP_CREATION_PAIR / "cube_two_groups.xxp").read_bytes()
    base = parse_bytes(base_bytes)
    changed = parse_bytes(changed_bytes)

    assert sha256(base_bytes).hexdigest() == (
        "fcba6d61f2af4cf79c1e86a20b570a0bb0039db3fb79c9d73c84e842430fc7a0"
    )
    assert sha256(changed_bytes).hexdigest() == (
        "c207830dcb70a1a05b44f583cb3199752e634803ad9035296c6da7b1c8b53b4e"
    )
    assert len(base_bytes) == 3_377
    assert len(changed_bytes) == 3_982
    assert base.to_bytes() == base_bytes
    assert changed.to_bytes() == changed_bytes

    differences = diff_documents(base, changed)
    assert len(differences) == 35
    assert differences[0] == {
        "kind": "value_changed",
        "section": "Header",
        "section_occurrence": 0,
        "key": "NumHolons",
        "key_occurrence": 0,
        "before": "2",
        "after": "3",
    }
    added = differences[1:]
    assert all(item["kind"] == "key_added" for item in added)
    assert all(item["section"] == "Holon\\2" for item in added)
    added_values = {item["key"]: item["after"] for item in added}
    assert added_values["ID"] == "2"
    assert added_values["GroupID"] == "2"
    assert added_values["Type"] == "0"
    assert added_values["Name"] == "Group3"


def test_deleting_middle_cube_compacts_sections_but_preserves_identity() -> None:
    data = (MIDDLE_CUBE_DELETION / "two_cubes.xxp").read_bytes()
    document = parse_bytes(data)

    assert len(data) == 4_103
    assert sha256(data).hexdigest() == (
        "010462dd1d78043c37ac5f306bd1ce16d167ca35b72b98b09228949023ca7809"
    )
    assert document.to_bytes() == data

    sections = {
        record.name
        for record in document.records
        if isinstance(record, SectionRecord)
    }
    assert b"Holon\\2" in sections
    assert b"Holon\\2\\MM\\0" in sections
    assert b"Holon\\3" not in sections
    assert b"Holon\\3\\MM\\0" not in sections

    values = {
        (record.section, record.key): record.value
        for record in document.records
        if isinstance(record, KeyValueRecord)
    }
    assert values[(b"Header", b"NumHolons")] == b"3"
    assert values[(b"Holon\\2", b"ID")] == b"3"
    assert values[(b"Holon\\2", b"Name")] == b"Cube4"
    assert values[(b"Holon\\2", b"GroupID")] == b"0"
    assert values[(b"Holon\\2", b"Type")] == b"1"
    assert values[(b"SelectionSpots", b"0")] == b"3 1 1 "


def test_clean_middle_cube_deletion_is_exact_and_has_no_incidental_change() -> None:
    source_bytes = (
        Path(__file__).parents[1]
        / "experiments"
        / "three-cube-positions"
        / "3_cube_positions.xxp"
    ).read_bytes()
    target_bytes = (CLEAN_MIDDLE_CUBE_DELETION / "middle_deleted.xxp").read_bytes()
    source = parse_bytes(source_bytes)
    target = parse_bytes(target_bytes)

    assert sha256(source_bytes).hexdigest() == (
        "caff33da71c7a24e6a79a7c4448a17daeefdc3c1915d3bc7d85ab167fe05654d"
    )
    assert sha256(target_bytes).hexdigest() == (
        "bb980364c5281d29a24c5b72accb74d907c33fc664e660731d697aaa56555d3a"
    )
    assert target.to_bytes() == target_bytes

    def section_index(document: Document, name: bytes) -> int:
        return next(
            index
            for index, record in enumerate(document.records)
            if isinstance(record, SectionRecord) and record.name == name
        )

    removed_start = section_index(source, b"Holon\\2")
    survivor_start = section_index(source, b"Holon\\3")
    gradients_start = section_index(source, b"Gradients")
    survivor = source.records[survivor_start:gradients_start]
    reindexed = []
    for record in survivor:
        if isinstance(record, SectionRecord):
            name = record.name.replace(b"Holon\\3", b"Holon\\2", 1)
            reindexed.append(replace(record, content=b"[" + name + b"]", name=name))
        elif isinstance(record, KeyValueRecord):
            reindexed.append(
                replace(
                    record,
                    section=record.section.replace(b"Holon\\3", b"Holon\\2", 1),
                )
            )
        else:
            reindexed.append(record)
    records = list(source.records)
    records[removed_start:gradients_start] = reindexed
    count_index = next(
        index
        for index, record in enumerate(records)
        if isinstance(record, KeyValueRecord)
        and record.section == b"Header"
        and record.key == b"NumHolons"
    )
    count = records[count_index]
    assert isinstance(count, KeyValueRecord)
    records[count_index] = replace(count, content=b"NumHolons=3", value=b"3")

    assert Document(tuple(records)).to_bytes() == target_bytes
    assert source.records[removed_start:survivor_start]
    assert all(item["section"] != "Holon\\0" for item in diff_documents(source, target))


def test_cube_sphere_changes_only_the_second_objects_constructor_records() -> None:
    mixed_bytes = (CUBE_SPHERE / "cube_sphere.xxp").read_bytes()
    cubes = parse_bytes(TWO_CUBE_REFERENCE.read_bytes())
    mixed = parse_bytes(mixed_bytes)

    assert len(mixed_bytes) == 4_126
    assert sha256(mixed_bytes).hexdigest() == (
        "bf4c03b607ed8b27af0840e0dade492f1706bdfad3f31f451df640c65e76bc85"
    )
    assert mixed.to_bytes() == mixed_bytes
    assert diff_documents(cubes, mixed) == [
        {
            "kind": "value_changed",
            "section": "Holon\\2",
            "section_occurrence": 0,
            "key": "Name",
            "key_occurrence": 0,
            "before": "Cube3",
            "after": "Sphere3",
        },
        {
            "kind": "value_changed",
            "section": "Holon\\2\\MM\\0",
            "section_occurrence": 0,
            "key": "Style",
            "key_occurrence": 0,
            "before": "5",
            "after": "1",
        },
        {
            "kind": "value_changed",
            "section": "Holon\\2\\MM\\0",
            "section_occurrence": 0,
            "key": "NumPars",
            "key_occurrence": 0,
            "before": "9",
            "after": "12",
        },
        {
            "kind": "value_changed",
            "section": "Holon\\2\\MM\\0",
            "section_occurrence": 0,
            "key": "Pars",
            "key_occurrence": 0,
            "before": "0.0000 0 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0 ",
            "after": (
                "0.00000 0 0.0000 0.00000 0.00000 0.00000 0.00000 "
                "0.0000 0.0000 0.000 0 0 "
            ),
        },
    ]
