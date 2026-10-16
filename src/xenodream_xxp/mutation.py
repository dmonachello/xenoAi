"""Evidence-gated, byte-preserving mutations of native XDX 1.220 projects."""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal, DecimalException
import re
from typing import TypeAlias

from .diffing import diff_documents
from .document import Document, KeyValueRecord, SectionRecord, parse_bytes
from .generator import Vector3


class MutationError(ValueError):
    """A requested edit is ambiguous or outside the verified mutation surface."""


@dataclass(frozen=True, slots=True)
class ObjectMutation:
    """Verified editable properties for one uniquely named object."""

    object_name: str
    scale: Vector3 | None = None
    rotation: Vector3 | None = None
    position: Vector3 | None = None
    color_density: Decimal | None = None
    face_warp: Decimal | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.object_name, str) or not self.object_name:
            raise TypeError("object_name must be a non-empty string")
        for name in ("scale", "rotation", "position"):
            value = getattr(self, name)
            if value is not None and not isinstance(value, Vector3):
                raise TypeError(f"{name} must be Vector3 or None")
        for name in ("color_density", "face_warp"):
            value = getattr(self, name)
            if value is not None:
                if not isinstance(value, Decimal):
                    raise TypeError(f"{name} must be Decimal or None")
                if not value.is_finite():
                    raise MutationError(f"{name} must be finite")
        if all(
            value is None
            for value in (
                self.scale,
                self.rotation,
                self.position,
                self.color_density,
                self.face_warp,
            )
        ):
            raise MutationError("object mutation must change at least one property")


@dataclass(frozen=True, slots=True)
class CenteredRowMutation:
    """Place every supported object at equal X intervals around a center."""

    spacing: Decimal
    center: Vector3 = Vector3()

    def __post_init__(self) -> None:
        if not isinstance(self.spacing, Decimal):
            raise TypeError("spacing must be Decimal")
        if not self.spacing.is_finite():
            raise MutationError("spacing must be finite")
        if not isinstance(self.center, Vector3):
            raise TypeError("center must be Vector3")


VerifiedOperation: TypeAlias = ObjectMutation | CenteredRowMutation


@dataclass(frozen=True, slots=True)
class MutationResult:
    data: bytes
    changed: bool
    differences: tuple[dict[str, object], ...]
    object_names: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _ObjectRecord:
    section: bytes
    name: str
    kind: str


_HOLON_SECTION = re.compile(rb"Holon\\([0-9]+)$")
_SUPPORTED_SIGNATURES = {
    ("cube",),
    ("cube", "cube"),
    ("cube", "cube", "cube"),
    ("sphere",),
    ("cube", "sphere"),
}


def _matching_records(
    document: Document, section: bytes, key: bytes
) -> list[tuple[int, KeyValueRecord]]:
    return [
        (index, record)
        for index, record in enumerate(document.records)
        if isinstance(record, KeyValueRecord)
        and record.section == section
        and record.section_occurrence == 0
        and record.key == key
    ]


def _value(document: Document, section: bytes, key: bytes) -> bytes:
    matches = _matching_records(document, section, key)
    if len(matches) != 1:
        raise MutationError(
            f"expected one {section.decode('ascii', 'replace')}.{key.decode('ascii', 'replace')} record, "
            f"found {len(matches)}"
        )
    return matches[0][1].value


def _require_xdx_1220(document: Document) -> None:
    if _value(document, b"Header", b"Program") != b"XDX":
        raise MutationError("verified mutations require an XDX project")
    if _value(document, b"Header", b"Progversion") != b"1.220":
        raise MutationError("verified mutations require XDX version 1.220")


def _objects(document: Document) -> tuple[_ObjectRecord, ...]:
    indexed_sections: list[tuple[int, bytes]] = []
    for record in document.records:
        if not isinstance(record, SectionRecord) or record.occurrence != 0:
            continue
        match = _HOLON_SECTION.fullmatch(record.name)
        if match and int(match.group(1)) > 0:
            indexed_sections.append((int(match.group(1)), record.name))

    objects: list[_ObjectRecord] = []
    for _, section in sorted(indexed_sections):
        if _value(document, section, b"Type") != b"1":
            continue
        try:
            name = _value(document, section, b"Name").decode("ascii")
        except UnicodeDecodeError as error:
            raise MutationError("verified object names must be ASCII") from error
        metamorph = section + b"\\MM\\0"
        style = _value(document, metamorph, b"Style")
        num_pars = _value(document, metamorph, b"NumPars")
        pars = _value(document, metamorph, b"Pars")
        if style == b"5" and num_pars == b"9" and len(pars.split()) == 9:
            kind = "cube"
        elif style == b"1" and num_pars == b"12" and len(pars.split()) == 12:
            kind = "sphere"
        else:
            raise MutationError(
                f"{name} does not match a verified XDX 1.220 Cube or Sphere record"
            )
        objects.append(_ObjectRecord(section, name, kind))
    if not objects:
        raise MutationError("project contains no verified editable objects")
    return tuple(objects)


def _format_decimal(value: Decimal, places: int, label: str) -> bytes:
    quantum = Decimal(1).scaleb(-places)
    try:
        quantized = value.quantize(quantum)
    except DecimalException as error:
        raise MutationError(f"{label} cannot be represented") from error
    if quantized != value:
        raise MutationError(f"{label} exceeds the verified {places}-place precision")
    return format(quantized, f".{places}f").encode("ascii")


def _replace_value(
    document: Document,
    section: bytes,
    key: bytes,
    value: Decimal,
    places: int,
    token_index: int | None,
) -> Document:
    matches = _matching_records(document, section, key)
    if len(matches) != 1:
        raise MutationError(f"expected one editable {section!r}.{key!r} record")
    record_index, record = matches[0]
    replacement = _format_decimal(value, places, f"{section!r}.{key!r}")
    if token_index is None:
        new_value = replacement
    else:
        tokens = list(re.finditer(rb"\S+", record.value))
        if token_index >= len(tokens):
            raise MutationError(f"missing token {token_index} in {section!r}.{key!r}")
        token = tokens[token_index]
        new_value = record.value[: token.start()] + replacement + record.value[token.end() :]
    separator = record.content.find(b"=")
    if separator < 0:
        raise MutationError("key/value record lost its separator")
    new_record = replace(
        record,
        content=record.content[: separator + 1] + new_value,
        value=new_value,
    )
    records = list(document.records)
    records[record_index] = new_record
    return Document(tuple(records))


def _set_vector(
    document: Document, section: bytes, indices: tuple[int, int, int], value: Vector3
) -> Document:
    for token_index, component in zip(indices, (value.x, value.y, value.z)):
        document = _replace_value(
            document, section, b"Transform", component, 5, token_index
        )
    return document


def _apply_object_mutation(
    document: Document, operation: ObjectMutation, objects: tuple[_ObjectRecord, ...]
) -> tuple[Document, tuple[str, ...], set[tuple[str, str, int | None]]]:
    matches = [item for item in objects if item.name == operation.object_name]
    if len(matches) != 1:
        raise MutationError(
            f"object name {operation.object_name!r} matched {len(matches)} objects"
        )
    obj = matches[0]
    if obj.kind == "sphere" and any(
        value is not None
        for value in (operation.rotation, operation.color_density, operation.face_warp)
    ):
        raise MutationError(
            "Sphere mutations support only scale and position until more fields are verified"
        )

    allowed: set[tuple[str, str, int | None]] = set()
    if operation.scale is not None:
        document = _set_vector(document, obj.section, (0, 1, 2), operation.scale)
        allowed.update((obj.section.decode(), "Transform", index) for index in (0, 1, 2))
    if operation.rotation is not None:
        document = _set_vector(document, obj.section, (6, 7, 8), operation.rotation)
        allowed.update((obj.section.decode(), "Transform", index) for index in (6, 7, 8))
    if operation.position is not None:
        document = _set_vector(document, obj.section, (9, 10, 11), operation.position)
        allowed.update((obj.section.decode(), "Transform", index) for index in (9, 10, 11))
    if operation.color_density is not None:
        document = _replace_value(
            document, obj.section, b"GradDensity", operation.color_density, 3, None
        )
        allowed.add((obj.section.decode(), "GradDensity", None))
    if operation.face_warp is not None:
        metamorph = obj.section + b"\\MM\\0"
        document = _replace_value(
            document, metamorph, b"Pars", operation.face_warp, 4, 0
        )
        allowed.add((metamorph.decode(), "Pars", 0))
    return document, (obj.name,), allowed


def _apply_row_mutation(
    document: Document,
    operation: CenteredRowMutation,
    objects: tuple[_ObjectRecord, ...],
) -> tuple[Document, tuple[str, ...], set[tuple[str, str, int | None]]]:
    signature = tuple(item.kind for item in objects)
    if signature not in _SUPPORTED_SIGNATURES:
        raise MutationError("row mutation requires a currently supported object sequence")
    start = operation.center.x - operation.spacing * Decimal(len(objects) - 1) / 2
    allowed: set[tuple[str, str, int | None]] = set()
    for index, obj in enumerate(objects):
        position = Vector3(
            start + operation.spacing * index,
            operation.center.y,
            operation.center.z,
        )
        document = _set_vector(document, obj.section, (9, 10, 11), position)
        allowed.update((obj.section.decode(), "Transform", token) for token in (9, 10, 11))
    return document, tuple(item.name for item in objects), allowed


def apply_verified_mutation(data: bytes, operation: VerifiedOperation) -> MutationResult:
    """Apply one verified operation while preserving every unrelated byte."""

    if not isinstance(operation, (ObjectMutation, CenteredRowMutation)):
        raise TypeError("operation must be ObjectMutation or CenteredRowMutation")
    original = parse_bytes(data)
    if original.to_bytes() != data:
        raise MutationError("input failed exact parser round trip")
    _require_xdx_1220(original)
    objects = _objects(original)
    if isinstance(operation, ObjectMutation):
        mutated, names, allowed = _apply_object_mutation(original, operation, objects)
    else:
        mutated, names, allowed = _apply_row_mutation(original, operation, objects)

    differences = tuple(diff_documents(original, mutated))
    unexpected = []
    for item in differences:
        locator = (
            item.get("section"),
            item.get("key"),
            item.get("token_index"),
        )
        if locator not in allowed:
            unexpected.append(item)
    if unexpected:
        raise MutationError(f"mutation changed unsupported fields: {unexpected}")
    output = mutated.to_bytes()
    if parse_bytes(output).to_bytes() != output:
        raise MutationError("mutated output failed exact parser round trip")
    return MutationResult(output, output != data, differences, names)
