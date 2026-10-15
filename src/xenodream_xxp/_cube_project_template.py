"""Private compiler for the verified XDX 1.220 cube project profiles."""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal, DecimalException
from hashlib import sha256
from importlib.resources import files
import re

from .diffing import diff_documents
from .document import Document, KeyValueRecord, parse_bytes
from .generator import CubeProjectSpec, GenerationError, TemplateMismatchError


@dataclass(frozen=True, slots=True)
class _Profile:
    resource_name: str
    sha256: str
    source_x_positions: tuple[bytes, ...]


@dataclass(frozen=True, slots=True)
class _Field:
    section: bytes
    key: bytes
    token_index: int | None
    expected: bytes
    places: int


_PROFILES = {
    1: _Profile(
        "cube_base.xxp",
        "fcba6d61f2af4cf79c1e86a20b570a0bb0039db3fb79c9d73c84e842430fc7a0",
        (b"0.00000",),
    ),
    2: _Profile(
        "two_cube_positions.xxp",
        "7b0f0b57d82feb0200b320befb179143804b0d75aca85908b809d9d684ac1e2a",
        (b"-50.00000", b"50.00000"),
    ),
    3: _Profile(
        "three_cube_positions.xxp",
        "caff33da71c7a24e6a79a7c4448a17daeefdc3c1915d3bc7d85ab167fe05654d",
        (b"-75.00000", b"0.00000", b"75.00000"),
    ),
}


def _cube_fields(index: int, source_x: bytes) -> tuple[_Field, ...]:
    section = f"Holon\\{index}".encode("ascii")
    metamorph = section + b"\\MM\\0"
    return (
        _Field(section, b"Transform", 0, b"50.00000", 5),
        _Field(section, b"Transform", 1, b"50.00000", 5),
        _Field(section, b"Transform", 2, b"50.00000", 5),
        _Field(section, b"Transform", 6, b"0.00000", 5),
        _Field(section, b"Transform", 7, b"0.00000", 5),
        _Field(section, b"Transform", 8, b"0.00000", 5),
        _Field(section, b"Transform", 9, source_x, 5),
        _Field(section, b"Transform", 10, b"0.00000", 5),
        _Field(section, b"Transform", 11, b"0.00000", 5),
        _Field(section, b"GradDensity", None, b"1.000", 3),
        _Field(metamorph, b"Pars", 0, b"0.0000", 4),
    )


def _template_bytes(profile: _Profile) -> bytes:
    resource = files("xenodream_xxp").joinpath(
        "templates", "xdx-1.220", profile.resource_name
    )
    data = resource.read_bytes()
    actual = sha256(data).hexdigest()
    if actual != profile.sha256:
        raise TemplateMismatchError(
            f"cube project template hash mismatch: expected {profile.sha256}, "
            f"got {actual}"
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


def _validate_template(document: Document, cube_count: int) -> None:
    expected = {
        (b"Header", b"Program"): b"XDX",
        (b"Header", b"Progversion"): b"1.220",
        (b"Header", b"NumHolons"): str(cube_count + 1).encode("ascii"),
        (b"Holon\\0", b"ID"): b"0",
        (b"Holon\\0", b"GroupID"): b"0",
        (b"Holon\\0", b"Type"): b"0",
        (b"Holon\\0", b"Name"): b"Group1",
    }
    for index in range(1, cube_count + 1):
        section = f"Holon\\{index}".encode("ascii")
        expected.update(
            {
                (section, b"ID"): str(index).encode("ascii"),
                (section, b"GroupID"): b"0",
                (section, b"Type"): b"1",
                (section, b"Name"): f"Cube{index + 1}".encode("ascii"),
                (section + b"\\MM\\0", b"Style"): b"5",
            }
        )
    for (section, key), expected_value in expected.items():
        actual = _value(document, section, key)
        if actual != expected_value:
            raise TemplateMismatchError(
                f"unexpected {section!r}.{key!r}: expected "
                f"{expected_value!r}, got {actual!r}"
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
        new_value = record.value[: token.start()] + replacement + record.value[token.end() :]

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


def _allowed_difference(
    difference: dict[str, object], fields: tuple[_Field, ...]
) -> bool:
    for field in fields:
        if difference.get("section") != field.section.decode("ascii"):
            continue
        if difference.get("key") != field.key.decode("ascii"):
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


def compile_project_template(spec: CubeProjectSpec) -> bytes:
    cube_count = len(spec.cubes)
    profile = _PROFILES[cube_count]
    template_data = _template_bytes(profile)
    template = parse_bytes(template_data)
    _validate_template(template, cube_count)

    fields_by_cube = tuple(
        _cube_fields(index, source_x)
        for index, source_x in enumerate(profile.source_x_positions, start=1)
    )
    fields = tuple(field for cube_fields in fields_by_cube for field in cube_fields)
    document = template
    for cube, cube_fields in zip(spec.cubes, fields_by_cube):
        values = (
            cube.scale.x,
            cube.scale.y,
            cube.scale.z,
            cube.rotation.x,
            cube.rotation.y,
            cube.rotation.z,
            cube.position.x,
            cube.position.y,
            cube.position.z,
            cube.color_density,
            cube.face_warp,
        )
        for field, value in zip(cube_fields, values):
            document = _replace_field(document, field, value)

    unexpected = [
        item
        for item in diff_documents(template, document)
        if not _allowed_difference(item, fields)
    ]
    if unexpected:
        raise TemplateMismatchError(f"compiler changed unsupported fields: {unexpected}")

    output = document.to_bytes()
    if parse_bytes(output).to_bytes() != output:
        raise TemplateMismatchError("compiled output failed exact parser round trip")
    return output
