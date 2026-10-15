from __future__ import annotations

from pathlib import Path

from xenodream_xxp.document import parse_bytes
from xenodream_xxp.report import inspect_document


SAMPLE = (
    Path(__file__).parents[1]
    / "samples"
    / "originals"
    / "20061109Sirps08.xxp"
)


def test_reference_report_covers_observed_structure() -> None:
    report = inspect_document(parse_bytes(SAMPLE.read_bytes()))

    assert report["file"]["bytes"] == 19_797
    assert report["file"]["sha256"] == (
        "0f9a2a22f23b5ba587548285f8cb9821a0ebb1814920c7955296e0f8c6095bae"
    )
    assert report["file"]["line_endings"] == {"crlf": 1001, "lf": 0, "cr": 0}
    assert report["file"]["max_line_bytes"] == 3018
    assert report["record_counts"] == {
        "blank": 38,
        "key_value": 925,
        "raw": 0,
        "section": 38,
    }
    assert report["header"]["Program"] == ["XDX"]
    assert report["header"]["Progversion"] == ["1.007"]
    assert report["header"]["NumHolons"] == ["26"]
    assert len(report["holons"]) == 26
    assert report["holons"][0]["id"] == "0"
    assert report["holons"][0]["type_code"] == "0"
    assert report["holons"][0]["transform"]["token_count"] == 12
    assert report["holons"][1]["type_code"] == "2"
    assert report["holons"][1]["metamorph_named_fields"] == {"PostMetas": ["0"]}
    assert report["cameras"] == ["HolonCamera", "SceneCamera"]
    assert report["material_sections"] == ["Materials", "Material\\0", "Material\\0\\Layer\\0"]
    assert "Material\\1" not in report["section_names"]
    assert set(report["sections"]["SceneCamera"]) >= {"Position", "Angles"}


def test_missing_fields_and_extra_fields_are_reported_without_defaults() -> None:
    source = b"[Header]\nProgram=XDX\nFutureField=opaque\n[Holon\\9]\nID=9\n"

    report = inspect_document(parse_bytes(source))

    assert report["header"] == {"Program": ["XDX"], "FutureField": ["opaque"]}
    assert report["holons"][0]["id"] == "9"
    assert report["holons"][0]["type_code"] is None
    assert report["holons"][0]["transform"] is None

