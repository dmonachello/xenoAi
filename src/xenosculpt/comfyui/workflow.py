"""Strict ComfyUI API-workflow parsing, mutation, and comparison."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
import math
import re
from typing import Any


_NODE_ID = re.compile(r"0|[1-9][0-9]*")


class WorkflowFormatError(ValueError):
    """The input is not an admitted ComfyUI API workflow."""


def _pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in items:
        if key in result:
            raise WorkflowFormatError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _constant(value: str) -> None:
    raise WorkflowFormatError(f"invalid JSON constant: {value}")


def _validate_json(value: Any, path: str = "$") -> None:
    if value is None or isinstance(value, (bool, str, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise WorkflowFormatError(f"non-finite number at {path}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_json(item, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise WorkflowFormatError(f"non-string key at {path}")
            _validate_json(item, f"{path}.{key}")
        return
    raise WorkflowFormatError(f"unsupported JSON value at {path}")


@dataclass(frozen=True, slots=True)
class LiteralInput:
    value: Any


@dataclass(frozen=True, slots=True)
class NodeLink:
    source: str
    output_index: int

    def __post_init__(self) -> None:
        if not isinstance(self.source, str) or not _NODE_ID.fullmatch(self.source):
            raise WorkflowFormatError("link source must be a decimal node ID")
        if type(self.output_index) is not int or self.output_index < 0:
            raise WorkflowFormatError("link output index must be a nonnegative integer")


@dataclass(frozen=True, slots=True)
class InputMutation:
    node_id: str
    input_name: str
    before: Any
    after: Any

    @property
    def changed(self) -> bool:
        return self.before != self.after


@dataclass(frozen=True, slots=True)
class ApiWorkflow:
    document: dict[str, Any]

    @property
    def node_count(self) -> int:
        return len(self.document)

    def to_bytes(self) -> bytes:
        return (
            json.dumps(
                self.document,
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        ).encode("utf-8")


def parse_workflow(data: bytes) -> ApiWorkflow:
    if data.startswith(b"\xef\xbb\xbf"):
        raise WorkflowFormatError("UTF-8 BOM is not permitted")
    try:
        text = data.decode("utf-8", errors="strict")
        value = json.loads(text, object_pairs_hook=_pairs, parse_constant=_constant)
    except WorkflowFormatError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise WorkflowFormatError(f"invalid UTF-8 JSON: {error}") from error
    if not isinstance(value, dict) or not value:
        raise WorkflowFormatError("API-format workflow must be a nonempty object")
    if "nodes" in value or "links" in value:
        raise WorkflowFormatError(
            "frontend workflow JSON is not API-format JSON; export API format"
        )
    for node_id, node in value.items():
        if not _NODE_ID.fullmatch(node_id):
            raise WorkflowFormatError(f"invalid node ID: {node_id!r}")
        if not isinstance(node, dict):
            raise WorkflowFormatError(f"node {node_id} must be an object")
        if not isinstance(node.get("class_type"), str) or not node["class_type"]:
            raise WorkflowFormatError(f"node {node_id} requires class_type")
        if not isinstance(node.get("inputs"), dict):
            raise WorkflowFormatError(f"node {node_id} requires an inputs object")
    _validate_json(value)
    for node_id, node in value.items():
        for name, item in node["inputs"].items():
            if _looks_like_link(item) and item[0] not in value:
                raise WorkflowFormatError(
                    f"node {node_id} input {name!r} references missing source node {item[0]}"
                )
    return ApiWorkflow(value)


def parse_json_value(text: str) -> Any:
    """Decode one strict JSON value for a literal workflow input."""

    try:
        value = json.loads(text, object_pairs_hook=_pairs, parse_constant=_constant)
    except WorkflowFormatError:
        raise
    except json.JSONDecodeError as error:
        raise WorkflowFormatError(f"invalid JSON value: {error}") from error
    _validate_json(value)
    return value


def _looks_like_link(value: Any) -> bool:
    return (
        isinstance(value, list)
        and len(value) == 2
        and isinstance(value[0], str)
        and _NODE_ID.fullmatch(value[0]) is not None
        and isinstance(value[1], int)
        and not isinstance(value[1], bool)
        and value[1] >= 0
    )


def apply_input(
    workflow: ApiWorkflow, node_id: str, input_name: str, value: LiteralInput | NodeLink
) -> tuple[ApiWorkflow, InputMutation]:
    if node_id not in workflow.document:
        raise WorkflowFormatError(f"missing node: {node_id}")
    inputs = workflow.document[node_id]["inputs"]
    if input_name not in inputs:
        raise WorkflowFormatError(f"node {node_id} has no input {input_name!r}")
    if isinstance(value, NodeLink):
        if value.source not in workflow.document:
            raise WorkflowFormatError(f"missing source node: {value.source}")
        after: Any = [value.source, value.output_index]
    else:
        _validate_json(value.value)
        if _looks_like_link(value.value):
            raise WorkflowFormatError(
                "link-shaped values require NodeLink or --link-node/--link-output"
            )
        after = deepcopy(value.value)
    before = deepcopy(inputs[input_name])
    document = deepcopy(workflow.document)
    document[node_id]["inputs"][input_name] = after
    return ApiWorkflow(document), InputMutation(node_id, input_name, before, after)


def _pointer_token(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def compare_workflows(before: ApiWorkflow, after: ApiWorkflow) -> list[dict[str, Any]]:
    differences: list[dict[str, Any]] = []

    def visit(left: Any, right: Any, path: str) -> None:
        if isinstance(left, dict) and isinstance(right, dict):
            for key in sorted(left.keys() | right.keys()):
                child = f"{path}/{_pointer_token(key)}"
                if key not in left:
                    differences.append({"after": right[key], "kind": "added", "path": child})
                elif key not in right:
                    differences.append({"before": left[key], "kind": "removed", "path": child})
                else:
                    visit(left[key], right[key], child)
            return
        if isinstance(left, list) and isinstance(right, list):
            common = min(len(left), len(right))
            for index in range(common):
                visit(left[index], right[index], f"{path}/{index}")
            for index in range(common, len(left)):
                differences.append({"before": left[index], "kind": "removed", "path": f"{path}/{index}"})
            for index in range(common, len(right)):
                differences.append({"after": right[index], "kind": "added", "path": f"{path}/{index}"})
            return
        if left != right or type(left) is not type(right):
            differences.append({"after": right, "before": left, "kind": "value_changed", "path": path or "/"})

    visit(before.document, after.document, "")
    return differences
