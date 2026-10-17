from __future__ import annotations

from pathlib import Path

import pytest

from xenosculpt.comfyui.workflow import (
    LiteralInput,
    NodeLink,
    WorkflowFormatError,
    apply_input,
    compare_workflows,
    parse_workflow,
)


FIXTURE = Path(__file__).parent / "fixtures" / "comfyui" / "empty-image-api.json"


def test_api_workflow_roundtrips_to_canonical_json() -> None:
    workflow = parse_workflow(FIXTURE.read_bytes())

    assert workflow.node_count == 2
    assert parse_workflow(workflow.to_bytes()) == workflow
    assert workflow.to_bytes().endswith(b"\n")


@pytest.mark.parametrize(
    "data, message",
    [
        (b'{"nodes":[],"links":[]}', "API-format"),
        (b'{"1":{"class_type":"X","inputs":{}},"1":{}}', "duplicate"),
        (b'{"1":{"class_type":"X","inputs":{"v":NaN}}}', "constant"),
        (b'\xef\xbb\xbf{}', "BOM"),
    ],
)
def test_parser_rejects_ambiguous_or_non_api_json(data: bytes, message: str) -> None:
    with pytest.raises(WorkflowFormatError, match=message):
        parse_workflow(data)


def test_typed_input_edits_and_full_semantic_diff() -> None:
    original = parse_workflow(FIXTURE.read_bytes())
    changed, literal = apply_input(original, "1", "width", LiteralInput(96))
    linked, link = apply_input(changed, "2", "images", NodeLink("1", 0))

    assert literal.before == 64
    assert literal.after == 96
    assert link.changed is False
    assert compare_workflows(original, linked) == [
        {"after": 96, "before": 64, "kind": "value_changed", "path": "/1/inputs/width"}
    ]


def test_link_must_point_to_an_existing_node() -> None:
    workflow = parse_workflow(FIXTURE.read_bytes())
    with pytest.raises(WorkflowFormatError, match="source node"):
        apply_input(workflow, "2", "images", NodeLink("99", 0))


@pytest.mark.parametrize("output", [True, 0.5, "0", -1])
def test_link_output_must_be_a_nonnegative_integer(output: object) -> None:
    with pytest.raises(WorkflowFormatError, match="nonnegative integer"):
        NodeLink("1", output)  # type: ignore[arg-type]


def test_literal_cannot_smuggle_a_link() -> None:
    workflow = parse_workflow(FIXTURE.read_bytes())
    with pytest.raises(WorkflowFormatError, match="link-shaped"):
        apply_input(workflow, "2", "images", LiteralInput(["99", 0]))
