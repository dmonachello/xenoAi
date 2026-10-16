from __future__ import annotations

from pathlib import Path

from xenodream_xxp.document import parse_bytes
from xenodream_xxp.metamorph import inspect_metamorphs, load_metamorph_registry


TEMPLATES = Path(__file__).parents[1] / "src" / "xenodream_xxp" / "templates" / "xdx-1.220"


def test_registry_contains_binary_recovered_token_descriptors() -> None:
    registry = load_metamorph_registry()
    operations = {item["name"]: item for item in registry["operations"]}

    assert operations["Sphere"]["displayed_parameter_names"] == [
        "Warp",
        "Warp Shape",
        "Waist",
        "Ovoid",
        "Sharpness",
        "Bilobe",
        "Shear",
        "Shear Bias",
        "XZ Curve",
        "Taper X",
        "Taper Type",
        "Taper Shape",
    ]
    sphere = operations["Sphere"]["token_bindings"]
    cube = operations["Cube"]["token_bindings"]
    assert [item["token_index"] for item in sphere] == list(range(12))
    assert [item["name"] for item in sphere] == operations["Sphere"][
        "displayed_parameter_names"
    ]
    assert sphere[1]["choices"][:3] == ["Round Up", "Tear Up", "Sharp Up"]
    assert sphere[9]["decimal_places"] == 1
    assert [item["token_index"] for item in cube] == list(range(9))
    assert cube[0]["name"] == "Face Warp"
    assert cube[0]["status"] == "confirmed"
    assert cube[0]["evidence"][:2] == ["E049", "R027"]
    assert cube[8]["choices"] == ["All", "X, Y", "X, Z", "X", "Y", "Z"]


def test_cube_metamorph_report_exposes_recovered_descriptors() -> None:
    document = parse_bytes((TEMPLATES / "cube_base.xxp").read_bytes())

    report = inspect_metamorphs(document)

    assert report["format_version"] == "1.220"
    assert report["metamorph_count"] == 1
    assert report["all_num_pars_match"] is True
    metamorph = report["metamorphs"][0]
    assert metamorph["operation"] == {
        "name": "Cube",
        "role": "constructor",
        "status": "verified_record_family",
        "confidence": "high",
        "schema_match": True,
        "displayed_parameter_names": [
            "Face Warp",
            "Face Shape",
            "Face Curve",
            "Inset",
            "Edge Warp",
            "Crop Face",
            "Corner Crush",
            "Face Squeeze",
            "Face Choice",
        ],
    }
    assert metamorph["parameters"][0]["name"] == "Face Warp"
    assert metamorph["parameters"][0]["mapping_status"] == "confirmed"
    assert metamorph["parameters"][0]["descriptor"] == {
        "kind": "numeric",
        "minimum": "-100",
        "maximum": "100",
        "default": "0",
        "step": "0.01",
        "decimal_places": 2,
    }
    assert metamorph["parameters"][1]["name"] == "Face Shape"
    assert metamorph["parameters"][1]["descriptor"]["choices"] == [
        "Pyramid",
        "Pyramid 45",
        "Cone",
        "Bullet",
    ]


def test_sphere_report_maps_all_persisted_tokens() -> None:
    document = parse_bytes((TEMPLATES / "sphere_base.xxp").read_bytes())

    metamorph = inspect_metamorphs(document)["metamorphs"][0]

    assert metamorph["operation"]["name"] == "Sphere"
    assert metamorph["operation"]["schema_match"] is True
    assert len(metamorph["operation"]["displayed_parameter_names"]) == 12
    assert len(metamorph["parameters"]) == 12
    assert [parameter["name"] for parameter in metamorph["parameters"]] == [
        "Warp",
        "Warp Shape",
        "Waist",
        "Ovoid",
        "Sharpness",
        "Bilobe",
        "Shear",
        "Shear Bias",
        "XZ Curve",
        "Taper X",
        "Taper Type",
        "Taper Shape",
    ]
    assert all(
        parameter["mapping_status"] == "binary_verified"
        for parameter in metamorph["parameters"]
    )


def test_unknown_style_and_invalid_count_remain_literal_and_unresolved() -> None:
    source = (
        b"[Header]\nProgversion=1.220\n"
        b"[Holon\\2\\MM\\3]\nStyle=999\nNumPars=3\nPars=1 2 \n"
    )
    document = parse_bytes(source)

    report = inspect_metamorphs(document)

    assert document.to_bytes() == source
    assert report["all_num_pars_match"] is False
    metamorph = report["metamorphs"][0]
    assert metamorph["metamorph_index"] == 3
    assert metamorph["operation"]["status"] == "unresolved"
    assert metamorph["parameters"] == [
        {
            "token_index": 0,
            "raw": "1",
            "name": None,
            "mapping_status": "unresolved",
            "evidence": [],
            "descriptor": None,
        },
        {
            "token_index": 1,
            "raw": "2",
            "name": None,
            "mapping_status": "unresolved",
            "evidence": [],
            "descriptor": None,
        },
    ]
