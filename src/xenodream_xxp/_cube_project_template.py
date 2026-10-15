"""Private compiler for verified XDX 1.220 object project profiles."""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal, DecimalException
from hashlib import sha256
from importlib.resources import files
import re

from .diffing import diff_documents
from .document import Document, KeyValueRecord, parse_bytes
from .generator import (
    CubeProjectSpec,
    CubeSpec,
    GenerationError,
    ProjectSpec,
    SphereSpec,
    TemplateMismatchError,
)


_CUBE_PARS = b"0.0000 0 0.0000 0.0000 0.0000 0.0000 0.0000 0.0000 0 "
_SPHERE_PARS = (
    b"0.00000 0 0.0000 0.00000 0.00000 0.00000 0.00000 0.0000 "
    b"0.0000 0.000 0 0 "
)


@dataclass(frozen=True, slots=True)
class _ObjectContract:
    spec_type: type[CubeSpec] | type[SphereSpec]
    name: bytes
    source_x: bytes
    style: bytes
    num_pars: bytes
    pars: bytes


@dataclass(frozen=True, slots=True)
class _Profile:
    resource_name: str
    sha256: str
    objects: tuple[_ObjectContract, ...]


@dataclass(frozen=True, slots=True)
class _Field:
    section: bytes
    key: bytes
    token_index: int | None
    expected: bytes
    places: int


def _cube(name: bytes, source_x: bytes) -> _ObjectContract:
    return _ObjectContract(CubeSpec, name, source_x, b"5", b"9", _CUBE_PARS)


def _sphere(name: bytes, source_x: bytes) -> _ObjectContract:
    return _ObjectContract(SphereSpec, name, source_x, b"1", b"12", _SPHERE_PARS)


_PROFILES: dict[tuple[type[object], ...], _Profile] = {
    (CubeSpec,): _Profile(
        "cube_base.xxp",
        "fcba6d61f2af4cf79c1e86a20b570a0bb0039db3fb79c9d73c84e842430fc7a0",
        (_cube(b"Cube2", b"0.00000"),),
    ),
    (CubeSpec, CubeSpec): _Profile(
        "two_cube_positions.xxp",
        "7b0f0b57d82feb0200b320befb179143804b0d75aca85908b809d9d684ac1e2a",
        (
            _cube(b"Cube2", b"-50.00000"),
            _cube(b"Cube3", b"50.00000"),
        ),
    ),
    (CubeSpec, CubeSpec, CubeSpec): _Profile(
        "three_cube_positions.xxp",
        "caff33da71c7a24e6a79a7c4448a17daeefdc3c1915d3bc7d85ab167fe05654d",
        (
            _cube(b"Cube2", b"-75.00000"),
            _cube(b"Cube3", b"0.00000"),
            _cube(b"Cube4", b"75.00000"),
        ),
    ),
    (SphereSpec,): _Profile(
        "sphere_base.xxp",
        "19bdf9608585ea50de30490d08ac0ae80aa96803d6de6028191559ba314f9013",
        (_sphere(b"Sphere2", b"0.00000"),),
    ),
    (CubeSpec, SphereSpec): _Profile(
        "cube_sphere.xxp",
        "bf4c03b607ed8b27af0840e0dade492f1706bdfad3f31f451df640c65e76bc85",
        (
            _cube(b"Cube2", b"-50.00000"),
            _sphere(b"Sphere3", b"50.00000"),
        ),
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


def _sphere_fields(index: int, source_x: bytes) -> tuple[_Field, ...]:
    section = f"Holon\\{index}".encode("ascii")
    return (
        _Field(section, b"Transform", 0, b"50.00000", 5),
        _Field(section, b"Transform", 1, b"50.00000", 5),
        _Field(section, b"Transform", 2, b"50.00000", 5),
        _Field(section, b"Transform", 9, source_x, 5),
        _Field(section, b"Transform", 10, b"0.00000", 5),
        _Field(section, b"Transform", 11, b"0.00000", 5),
    )


def _template_bytes(profile: _Profile) -> bytes:
    resource = files("xenodream_xxp").joinpath(
        "templates", "xdx-1.220", profile.resource_name
    )
    data = resource.read_bytes()
    actual = sha256(data).hexdigest()
    if actual != profile.sha256:
        raise TemplateMismatchError(
            f"project template hash mismatch: expected {profile.sha256}, got {actual}"
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


def _validate_template(document: Document, profile: _Profile) -> None:
    expected = {
        (b"Header", b"Program"): b"XDX",
        (b"Header", b"Progversion"): b"1.220",
        (b"Header", b"NumHolons"): str(len(profile.objects) + 1).encode("ascii"),
        (b"Holon\\0", b"ID"): b"0",
        (b"Holon\\0", b"GroupID"): b"0",
        (b"Holon\\0", b"Type"): b"0",
        (b"Holon\\0", b"Name"): b"Group1",
    }
    for index, contract in enumerate(profile.objects, start=1):
        section = f"Holon\\{index}".encode("ascii")
        metamorph = section + b"\\MM\\0"
        expected.update(
            {
                (section, b"ID"): str(index).encode("ascii"),
                (section, b"GroupID"): b"0",
                (section, b"Type"): b"1",
                (section, b"Name"): contract.name,
                (metamorph, b"Style"): contract.style,
                (metamorph, b"NumPars"): contract.num_pars,
                (metamorph, b"Pars"): contract.pars,
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


def _object_values(obj: CubeSpec | SphereSpec) -> tuple[Decimal, ...]:
    if type(obj) is CubeSpec:
        return (
            obj.scale.x,
            obj.scale.y,
            obj.scale.z,
            obj.rotation.x,
            obj.rotation.y,
            obj.rotation.z,
            obj.position.x,
            obj.position.y,
            obj.position.z,
            obj.color_density,
            obj.face_warp,
        )
    if type(obj) is SphereSpec:
        return (
            obj.scale.x,
            obj.scale.y,
            obj.scale.z,
            obj.position.x,
            obj.position.y,
            obj.position.z,
        )
    raise TypeError(f"unsupported object type: {type(obj).__name__}")


def compile_project_template(spec: CubeProjectSpec | ProjectSpec) -> bytes:
    objects = spec.cubes if isinstance(spec, CubeProjectSpec) else spec.objects
    signature = tuple(type(obj) for obj in objects)
    profile = _PROFILES.get(signature)
    if profile is None:
        raise GenerationError("no verified template for object sequence")

    template_data = _template_bytes(profile)
    template = parse_bytes(template_data)
    _validate_template(template, profile)

    fields_by_object = tuple(
        _cube_fields(index, contract.source_x)
        if contract.spec_type is CubeSpec
        else _sphere_fields(index, contract.source_x)
        for index, contract in enumerate(profile.objects, start=1)
    )
    fields = tuple(
        field for object_fields in fields_by_object for field in object_fields
    )
    document = template
    for obj, object_fields in zip(objects, fields_by_object):
        for field, value in zip(object_fields, _object_values(obj)):
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
