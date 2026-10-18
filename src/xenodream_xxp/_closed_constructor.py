"""Closed constructor profiles admitted by exact native evidence."""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from hashlib import sha256

from ._cube_project_template import (
    _PROFILES,
    _allowed_difference,
    _replace_field,
    _sphere_fields,
    _template_bytes,
    _validate_template,
)
from .diffing import diff_documents
from .document import Document, KeyValueRecord, parse_bytes
from .generator import (
    ClosedConstructorName,
    ClosedConstructorSpec,
    SphereSpec,
    TemplateMismatchError,
    Vector3,
)


@dataclass(frozen=True, slots=True)
class _ClosedProfile:
    style: int
    parameter_count: int
    parameters: bytes
    canonical_sha256: str
    evidence: tuple[str, ...]


_PROFILES_BY_NAME = {
    ClosedConstructorName.ROUND_CUBE: _ClosedProfile(
        6,
        10,
        b"25.00 0.00 0 0.00 0 0.00 0.00 0.00 0.00 0.00 ",
        "9be76e32e36f9a98ba3295f38b7089aa94838681f4763470492f7ddd2b969da5",
        ("E111", "E112"),
    ),
    ClosedConstructorName.PIPE: _ClosedProfile(
        11,
        11,
        b"1.000 50.00 0.00 0.00 0.00 8 0 0 0.00 0 0.000 ",
        "2e28e99d702130ac93f248681ac255b430187a530467c39ffc95e985039342cd",
        ("E111", "E112"),
    ),
    ClosedConstructorName.TORUS: _ClosedProfile(
        42,
        11,
        b"25.00 360.00 0 0.00 16 0 0 0 0.000 0 0.0 ",
        "c32c4dff9a2f946a4800aae7d689e4c18a3f07d57b3e8d95df8e78b224014ba7",
        ("E111", "E112"),
    ),
    ClosedConstructorName.COG: _ClosedProfile(
        62,
        10,
        b"6 0.500 2 -25.0 40.0 1.000 0.000 0.000 0.000 0.000 ",
        "fe74b398d7b55d671ff1f86d326c90213ca04ef0eb5eb283c5a4e482a7911017",
        ("E111", "E112"),
    ),
    ClosedConstructorName.SPIRAL_SHELL: _ClosedProfile(
        65,
        12,
        b"1.000 1.000 3.000 0.00 4.00 0 2.00 0 0.0 0.000 0.000 0.00 ",
        "f75d94cf2db8e630439f1df50f04ab6dd3fcb8dabf1817418b3d19ac75cb6012",
        ("E111", "E112"),
    ),
}


def _replace_value(
    document: Document, section: bytes, key: bytes, expected: bytes, value: bytes
) -> Document:
    matches = [
        (index, record)
        for index, record in enumerate(document.records)
        if isinstance(record, KeyValueRecord)
        and record.section == section
        and record.section_occurrence == 0
        and record.key == key
    ]
    if len(matches) != 1 or matches[0][1].value != expected:
        raise TemplateMismatchError(
            f"unexpected source value for {section!r}.{key!r}"
        )
    record_index, record = matches[0]
    separator = record.content.find(b"=")
    updated = replace(
        record,
        content=record.content[: separator + 1] + value,
        value=value,
    )
    records = list(document.records)
    records[record_index] = updated
    return Document(tuple(records))


def compile_closed_constructor_template(spec: ClosedConstructorSpec) -> bytes:
    profile = _PROFILES_BY_NAME[spec.constructor]
    scaffold_profile = _PROFILES[(SphereSpec,)]
    scaffold = parse_bytes(_template_bytes(scaffold_profile))
    _validate_template(scaffold, scaffold_profile)
    section = b"Holon\\1"
    metamorph = section + b"\\MM\\0"
    document = scaffold
    for target, key, expected, value in (
        (section, b"Name", b"Sphere2", f"{spec.constructor.value}2".encode("ascii")),
        (metamorph, b"Style", b"1", str(profile.style).encode("ascii")),
        (
            metamorph,
            b"NumPars",
            b"12",
            str(profile.parameter_count).encode("ascii"),
        ),
        (metamorph, b"Pars", scaffold_profile.objects[0].pars, profile.parameters),
    ):
        document = _replace_value(document, target, key, expected, value)

    transform_fields = _sphere_fields(1, b"0.00000")
    values = (
        spec.scale.x,
        spec.scale.y,
        spec.scale.z,
        spec.position.x,
        spec.position.y,
        spec.position.z,
    )
    for field, value in zip(transform_fields, values):
        document = _replace_field(document, field, value)

    constructor_fields = {
        ("Holon\\1", "Name"),
        ("Holon\\1\\MM\\0", "Style"),
        ("Holon\\1\\MM\\0", "NumPars"),
        ("Holon\\1\\MM\\0", "Pars"),
    }
    unexpected = []
    for difference in diff_documents(scaffold, document):
        locator = (difference.get("section"), difference.get("key"))
        if locator in constructor_fields or _allowed_difference(
            difference, transform_fields
        ):
            continue
        unexpected.append(difference)
    if unexpected:
        raise TemplateMismatchError(
            f"closed constructor compiler changed unsupported fields: {unexpected}"
        )

    output = document.to_bytes()
    if parse_bytes(output).to_bytes() != output:
        raise TemplateMismatchError(
            "compiled closed constructor failed exact parser round trip"
        )
    if spec.scale == Vector3(Decimal("50"), Decimal("50"), Decimal("50")) and spec.position == Vector3():
        actual = sha256(output).hexdigest()
        if actual != profile.canonical_sha256:
            raise TemplateMismatchError(
                f"canonical {spec.constructor.value} digest mismatch"
            )
    return output
