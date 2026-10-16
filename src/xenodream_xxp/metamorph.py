"""Evidence-aware inspection of XenoDream metamorph records."""

from __future__ import annotations

from functools import lru_cache
from importlib.resources import files
import json
import re
from typing import Any

from .document import Document, KeyValueRecord


_METAMORPH_SECTION = re.compile(rb"Holon\\([0-9]+)\\MM\\([0-9]+)$")


@lru_cache(maxsize=1)
def load_metamorph_registry() -> dict[str, Any]:
    """Load the packaged, evidence-scoped XDX 1.220 operation registry."""

    resource = files("xenodream_xxp").joinpath(
        "data", "xdx-1.220-metamorph-registry.json"
    )
    return json.loads(resource.read_text(encoding="utf-8"))


def _text(value: bytes | None) -> str | None:
    return None if value is None else value.decode("ascii", errors="backslashreplace")


def _fields(document: Document, section: bytes, occurrence: int) -> dict[bytes, list[bytes]]:
    result: dict[bytes, list[bytes]] = {}
    for record in document.records:
        if (
            isinstance(record, KeyValueRecord)
            and record.section == section
            and (record.section_occurrence or 0) == occurrence
        ):
            result.setdefault(record.key, []).append(record.value)
    return result


def _first(values: dict[bytes, list[bytes]], key: bytes) -> bytes | None:
    matches = values.get(key)
    return matches[0] if matches else None


def inspect_metamorphs(document: Document) -> dict[str, Any]:
    """Project persisted metamorph blocks without assigning unknown semantics."""

    registry = load_metamorph_registry()
    definitions = {
        str(item["style"]): item for item in registry["operations"]
    }
    header = _fields(document, b"Header", 0)
    version = _text(_first(header, b"Progversion"))
    metamorphs: list[dict[str, Any]] = []

    for section_record in document.sections:
        match = _METAMORPH_SECTION.fullmatch(section_record.name)
        if match is None:
            continue
        values = _fields(document, section_record.name, section_record.occurrence)
        style = _text(_first(values, b"Style"))
        declared_text = _text(_first(values, b"NumPars"))
        pars = _first(values, b"Pars")
        tokens = [] if pars is None else [_text(token) for token in pars.split()]
        try:
            declared = None if declared_text is None else int(declared_text)
        except ValueError:
            declared = None

        definition = definitions.get(style or "")
        schema_match = False
        if definition is not None:
            schema_match = (
                version in definition.get("format_versions", [])
                and declared in definition.get("verified_num_pars", [])
            )

        bindings: dict[int, dict[str, Any]] = {}
        if definition is not None and schema_match:
            bindings = {
                int(binding["token_index"]): binding
                for binding in definition.get("token_bindings", [])
            }

        parameters = []
        for index, raw in enumerate(tokens):
            binding = bindings.get(index)
            parameters.append(
                {
                    "token_index": index,
                    "raw": raw,
                    "name": None if binding is None else binding["name"],
                    "mapping_status": (
                        "unresolved" if binding is None else binding["status"]
                    ),
                    "evidence": [] if binding is None else binding["evidence"],
                }
            )

        metamorphs.append(
            {
                "section": _text(section_record.name),
                "section_occurrence": section_record.occurrence,
                "holon_section": f"Holon\\{int(match.group(1))}",
                "holon_index": int(match.group(1)),
                "metamorph_index": int(match.group(2)),
                "style": style,
                "num_pars_raw": declared_text,
                "num_pars": declared,
                "pars_raw": _text(pars),
                "pars_token_count": len(tokens),
                "num_pars_matches": declared == len(tokens),
                "operation": (
                    {
                        "name": definition["name"],
                        "role": definition["role"],
                        "status": definition["status"],
                        "confidence": definition["confidence"],
                        "schema_match": schema_match,
                        "displayed_parameter_names": definition.get(
                            "displayed_parameter_names", []
                        ),
                    }
                    if definition is not None
                    else {
                        "name": None,
                        "role": "unknown",
                        "status": "unresolved",
                        "confidence": "none",
                        "schema_match": False,
                        "displayed_parameter_names": [],
                    }
                ),
                "parameters": parameters,
            }
        )

    return {
        "format_version": version,
        "registry_schema_version": registry["schema_version"],
        "registry_target": registry["target"],
        "metamorph_count": len(metamorphs),
        "all_num_pars_match": all(
            item["num_pars_matches"] for item in metamorphs
        ),
        "metamorphs": metamorphs,
    }
