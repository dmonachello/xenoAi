from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from xenodream_xxp.diffing import diff_documents
from xenodream_xxp.document import parse_bytes


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
