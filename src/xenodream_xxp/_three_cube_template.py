"""Private contract for the verified XDX 1.220 three-cube template."""

from __future__ import annotations

from hashlib import sha256
from importlib.resources import files

from ._cube_template import _Field, _replace_field, _value
from .diffing import diff_documents
from .document import Document, parse_bytes
from .generator import ThreeCubeProjectSpec, TemplateMismatchError


TEMPLATE_SHA256 = (
    "caff33da71c7a24e6a79a7c4448a17daeefdc3c1915d3bc7d85ab167fe05654d"
)
_POSITION_X = (b"-75.00000", b"0.00000", b"75.00000")


def _cube_fields(index: int) -> tuple[_Field, ...]:
    section = f"Holon\\{index}".encode("ascii")
    metamorph = section + b"\\MM\\0"
    return (
        _Field(section, b"Transform", 0, b"50.00000", 5),
        _Field(section, b"Transform", 1, b"50.00000", 5),
        _Field(section, b"Transform", 2, b"50.00000", 5),
        _Field(section, b"Transform", 6, b"0.00000", 5),
        _Field(section, b"Transform", 7, b"0.00000", 5),
        _Field(section, b"Transform", 8, b"0.00000", 5),
        _Field(section, b"Transform", 9, _POSITION_X[index - 1], 5),
        _Field(section, b"Transform", 10, b"0.00000", 5),
        _Field(section, b"Transform", 11, b"0.00000", 5),
        _Field(section, b"GradDensity", None, b"1.000", 3),
        _Field(metamorph, b"Pars", 0, b"0.0000", 4),
    )


_CUBE_FIELDS = tuple(_cube_fields(index) for index in (1, 2, 3))
_FIELDS = tuple(field for fields_for_cube in _CUBE_FIELDS for field in fields_for_cube)


def _template_bytes() -> bytes:
    resource = files("xenodream_xxp").joinpath(
        "templates", "xdx-1.220", "three_cube_positions.xxp"
    )
    data = resource.read_bytes()
    actual = sha256(data).hexdigest()
    if actual != TEMPLATE_SHA256:
        raise TemplateMismatchError(
            f"three-cube template hash mismatch: expected {TEMPLATE_SHA256}, "
            f"got {actual}"
        )
    return data


def _validate_template(document: Document) -> None:
    expected = {
        (b"Header", b"Program"): b"XDX",
        (b"Header", b"Progversion"): b"1.220",
        (b"Header", b"NumHolons"): b"4",
        (b"Holon\\0", b"ID"): b"0",
        (b"Holon\\0", b"GroupID"): b"0",
        (b"Holon\\0", b"Type"): b"0",
        (b"Holon\\0", b"Name"): b"Group1",
    }
    for index in (1, 2, 3):
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


def _allowed_difference(difference: dict[str, object]) -> bool:
    for field in _FIELDS:
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


def compile_three_cube_template(spec: ThreeCubeProjectSpec) -> bytes:
    template_data = _template_bytes()
    template = parse_bytes(template_data)
    _validate_template(template)

    document = template
    for cube, fields_for_cube in zip(spec.cubes, _CUBE_FIELDS):
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
        for field, value in zip(fields_for_cube, values):
            document = _replace_field(document, field, value)

    unexpected = [
        item
        for item in diff_documents(template, document)
        if not _allowed_difference(item)
    ]
    if unexpected:
        raise TemplateMismatchError(f"compiler changed unsupported fields: {unexpected}")

    output = document.to_bytes()
    if parse_bytes(output).to_bytes() != output:
        raise TemplateMismatchError("compiled output failed exact parser round trip")
    return output
