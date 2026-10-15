"""Private contract for the verified XDX 1.220 cube template."""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal, DecimalException
from hashlib import sha256
from importlib.resources import files
import re

from .diffing import diff_documents
from .document import Document, KeyValueRecord, parse_bytes
from .generator import CubeSpec, GenerationError, TemplateMismatchError


TEMPLATE_SHA256 = (
    "fcba6d61f2af4cf79c1e86a20b570a0bb0039db3fb79c9d73c84e842430fc7a0"
)


@dataclass(frozen=True, slots=True)
class _Field:
    section: bytes
    key: bytes
    token_index: int | None
    expected: bytes
    places: int


_SCALE = (
    _Field(b"Holon\\1", b"Transform", 0, b"50.00000", 5),
    _Field(b"Holon\\1", b"Transform", 1, b"50.00000", 5),
    _Field(b"Holon\\1", b"Transform", 2, b"50.00000", 5),
)
_ROTATION = (
    _Field(b"Holon\\1", b"Transform", 6, b"0.00000", 5),
    _Field(b"Holon\\1", b"Transform", 7, b"0.00000", 5),
    _Field(b"Holon\\1", b"Transform", 8, b"0.00000", 5),
)
_POSITION = (
    _Field(b"Holon\\1", b"Transform", 9, b"0.00000", 5),
    _Field(b"Holon\\1", b"Transform", 10, b"0.00000", 5),
    _Field(b"Holon\\1", b"Transform", 11, b"0.00000", 5),
)
_COLOR_DENSITY = _Field(b"Holon\\1", b"GradDensity", None, b"1.000", 3)
_FACE_WARP = _Field(b"Holon\\1\\MM\\0", b"Pars", 0, b"0.0000", 4)
_FIELDS = (*_SCALE, *_ROTATION, *_POSITION, _COLOR_DENSITY, _FACE_WARP)


def _template_bytes() -> bytes:
    resource = files("xenodream_xxp").joinpath(
        "templates", "xdx-1.220", "cube_base.xxp"
    )
    data = resource.read_bytes()
    actual = sha256(data).hexdigest()
    if actual != TEMPLATE_SHA256:
        raise TemplateMismatchError(
            f"cube template hash mismatch: expected {TEMPLATE_SHA256}, got {actual}"
        )
    return data


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
        raise TemplateMismatchError(
            f"expected one {section!r}.{key!r} record, found {len(matches)}"
        )
    return matches[0][1].value


def _validate_template(document: Document) -> None:
    expected = {
        (b"Header", b"Program"): b"XDX",
        (b"Header", b"Progversion"): b"1.220",
        (b"Header", b"NumHolons"): b"2",
        (b"Holon\\0", b"ID"): b"0",
        (b"Holon\\0", b"GroupID"): b"0",
        (b"Holon\\0", b"Type"): b"0",
        (b"Holon\\0", b"Name"): b"Group1",
        (b"Holon\\1", b"ID"): b"1",
        (b"Holon\\1", b"GroupID"): b"0",
        (b"Holon\\1", b"Type"): b"1",
        (b"Holon\\1", b"Name"): b"Cube2",
        (b"Holon\\1\\MM\\0", b"Style"): b"5",
    }
    for (section, key), value in expected.items():
        actual = _value(document, section, key)
        if actual != value:
            raise TemplateMismatchError(
                f"unexpected {section!r}.{key!r}: expected {value!r}, got {actual!r}"
            )


def _format_decimal(value: Decimal, places: int, field: _Field) -> bytes:
    quantum = Decimal(1).scaleb(-places)
    try:
        quantized = value.quantize(quantum)
    except DecimalException as error:
        raise GenerationError(
            f"value cannot be represented for {field.section!r}.{field.key!r}"
        ) from error
    if quantized != value:
        raise GenerationError(
            f"value {value} exceeds the verified {places}-place precision"
        )
    return format(quantized, f".{places}f").encode("ascii")


def _replace_field(document: Document, field: _Field, value: Decimal) -> Document:
    matches = _matching_records(document, field.section, field.key)
    if len(matches) != 1:
        raise TemplateMismatchError(
            f"expected one {field.section!r}.{field.key!r} record, "
            f"found {len(matches)}"
        )
    record_index, record = matches[0]
    replacement = _format_decimal(value, field.places, field)

    if field.token_index is None:
        if record.value != field.expected:
            raise TemplateMismatchError(
                f"unexpected source value for {field.section!r}.{field.key!r}"
            )
        new_value = replacement
    else:
        tokens = list(re.finditer(rb"\S+", record.value))
        if field.token_index >= len(tokens):
            raise TemplateMismatchError(
                f"missing token {field.token_index} in "
                f"{field.section!r}.{field.key!r}"
            )
        token = tokens[field.token_index]
        if token.group() != field.expected:
            raise TemplateMismatchError(
                f"unexpected source token for {field.section!r}.{field.key!r}"
            )
        new_value = (
            record.value[: token.start()]
            + replacement
            + record.value[token.end() :]
        )

    separator = record.content.find(b"=")
    if separator < 0:
        raise TemplateMismatchError("key/value record lost its separator")
    new_record = replace(
        record,
        content=record.content[: separator + 1] + new_value,
        value=new_value,
    )
    records = list(document.records)
    records[record_index] = new_record
    return Document(tuple(records))


def _allowed_difference(difference: dict[str, object]) -> bool:
    for field in _FIELDS:
        section = field.section.decode("ascii")
        key = field.key.decode("ascii")
        if difference.get("section") != section or difference.get("key") != key:
            continue
        if field.token_index is None:
            if difference.get("kind") == "value_changed":
                return True
            continue
        if (
            difference.get("kind") == "value_token_changed"
            and difference.get("token_index") == field.token_index
        ):
            return True
    return False


def compile_template(spec: CubeSpec) -> bytes:
    template_data = _template_bytes()
    template = parse_bytes(template_data)
    _validate_template(template)

    document = template
    for field, value in zip(_SCALE, (spec.scale.x, spec.scale.y, spec.scale.z)):
        document = _replace_field(document, field, value)
    for field, value in zip(
        _ROTATION, (spec.rotation.x, spec.rotation.y, spec.rotation.z)
    ):
        document = _replace_field(document, field, value)
    for field, value in zip(
        _POSITION, (spec.position.x, spec.position.y, spec.position.z)
    ):
        document = _replace_field(document, field, value)
    document = _replace_field(document, _COLOR_DENSITY, spec.color_density)
    document = _replace_field(document, _FACE_WARP, spec.face_warp)

    differences = diff_documents(template, document)
    unexpected = [item for item in differences if not _allowed_difference(item)]
    if unexpected:
        raise TemplateMismatchError(f"compiler changed unsupported fields: {unexpected}")

    output = document.to_bytes()
    if parse_bytes(output).to_bytes() != output:
        raise TemplateMismatchError("compiled output failed exact parser round trip")
    return output
