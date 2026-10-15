"""Literal structural reports over lossless `.xxp` documents."""

from __future__ import annotations

from collections import Counter
from hashlib import sha256
import re
from typing import Any

from .document import (
    BlankRecord,
    Document,
    KeyValueRecord,
    RawRecord,
    SectionRecord,
)


def _text(value: bytes) -> str:
    return value.decode("ascii", errors="backslashreplace")


def _field_map(records: list[KeyValueRecord]) -> dict[str, list[str]]:
    fields: dict[str, list[str]] = {}
    for record in records:
        fields.setdefault(_text(record.key), []).append(_text(record.value))
    return fields


def _first(fields: dict[str, list[str]], key: str) -> str | None:
    values = fields.get(key)
    return values[0] if values else None


def inspect_document(document: Document) -> dict[str, Any]:
    data = document.to_bytes()
    ending_counts = Counter(record.ending for record in document.records)
    record_counts = Counter(type(record).__name__ for record in document.records)

    instance_records: dict[tuple[bytes, int], list[KeyValueRecord]] = {}
    for record in document.records:
        if isinstance(record, KeyValueRecord) and record.section is not None:
            key = (record.section, record.section_occurrence or 0)
            instance_records.setdefault(key, []).append(record)

    section_instances: list[dict[str, Any]] = []
    merged_sections: dict[str, dict[str, list[str]]] = {}
    holons: list[dict[str, Any]] = []
    section_names: list[str] = []

    for section in document.sections:
        name = _text(section.name)
        section_names.append(name)
        fields = _field_map(instance_records.get((section.name, section.occurrence), []))
        section_instances.append(
            {"name": name, "occurrence": section.occurrence, "fields": fields}
        )
        merged = merged_sections.setdefault(name, {})
        for key, values in fields.items():
            merged.setdefault(key, []).extend(values)

        match = re.fullmatch(r"Holon\\(\d+)", name)
        if match:
            transform_value = _first(fields, "Transform")
            metamorph_fields = {
                key: values for key, values in fields.items() if "meta" in key.lower()
            }
            holons.append(
                {
                    "section": name,
                    "section_index": int(match.group(1)),
                    "id": _first(fields, "ID"),
                    "group_id": _first(fields, "GroupID"),
                    "type_code": _first(fields, "Type"),
                    "name": _first(fields, "Name"),
                    "transform": (
                        {
                            "raw": transform_value,
                            "tokens": transform_value.split(),
                            "token_count": len(transform_value.split()),
                        }
                        if transform_value is not None
                        else None
                    ),
                    "metamorph_named_fields": metamorph_fields,
                    "fields": fields,
                }
            )

    header = merged_sections.get("Header", {})
    cameras = [name for name in section_names if name.endswith("Camera")]
    material_sections = [
        name
        for name in section_names
        if name == "Materials" or name.startswith("Material\\")
    ]

    return {
        "file": {
            "bytes": len(data),
            "sha256": sha256(data).hexdigest(),
            "ascii_only": all(byte < 128 for byte in data),
            "line_endings": {
                "crlf": ending_counts[b"\r\n"],
                "lf": ending_counts[b"\n"],
                "cr": ending_counts[b"\r"],
            },
            "ends_with_line_ending": data.endswith((b"\r\n", b"\n", b"\r")),
            "max_line_bytes": max(
                (len(record.content) for record in document.records), default=0
            ),
        },
        "record_counts": {
            "blank": record_counts[BlankRecord.__name__],
            "key_value": record_counts[KeyValueRecord.__name__],
            "raw": record_counts[RawRecord.__name__],
            "section": record_counts[SectionRecord.__name__],
        },
        "section_names": section_names,
        "section_instances": section_instances,
        "sections": merged_sections,
        "header": header,
        "holons": holons,
        "cameras": cameras,
        "material_sections": material_sections,
    }

