from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from xenodream_xxp.diffing import diff_documents
from xenodream_xxp.document import parse_bytes


PAIR = Path(__file__).parents[1] / "experiments" / "scale-x"
Y_PAIR = Path(__file__).parents[1] / "experiments" / "scale-y"


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
