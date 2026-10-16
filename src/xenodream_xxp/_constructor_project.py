"""Constructors recovered from binary descriptors and observed record families."""

from __future__ import annotations

from dataclasses import replace

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
from .generator import CylinderSpec, SphereSpec, TemplateMismatchError


_CYLINDER_DEFAULT_PARS = b"1.00000 360.0000 2 0 0 0.000 2 "


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


def compile_cylinder_template(spec: CylinderSpec) -> bytes:
    """Derive a one-constructor project from the normalized one-object scaffold."""

    profile = _PROFILES[(SphereSpec,)]
    template = parse_bytes(_template_bytes(profile))
    _validate_template(template, profile)
    section = b"Holon\\1"
    metamorph = section + b"\\MM\\0"
    document = template
    for key, expected, value in (
        (b"Name", b"Sphere2", b"Cylinder2"),
        (b"Style", b"1", b"13"),
        (b"NumPars", b"12", b"7"),
        (b"Pars", profile.objects[0].pars, _CYLINDER_DEFAULT_PARS),
    ):
        target = section if key == b"Name" else metamorph
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

    allowed_values = {
        ("Holon\\1", "Name"),
        ("Holon\\1\\MM\\0", "Style"),
        ("Holon\\1\\MM\\0", "NumPars"),
        ("Holon\\1\\MM\\0", "Pars"),
    }
    unexpected = []
    for difference in diff_documents(template, document):
        locator = (difference.get("section"), difference.get("key"))
        if locator in allowed_values or _allowed_difference(
            difference, transform_fields
        ):
            continue
        unexpected.append(difference)
    if unexpected:
        raise TemplateMismatchError(
            f"Cylinder compiler changed unsupported fields: {unexpected}"
        )
    output = document.to_bytes()
    if parse_bytes(output).to_bytes() != output:
        raise TemplateMismatchError("compiled Cylinder failed exact parser round trip")
    return output
