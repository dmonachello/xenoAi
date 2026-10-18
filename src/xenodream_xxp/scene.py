"""Typed, read-only descriptions of lossless XenoDream scenes."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from decimal import Decimal, DecimalException
from enum import StrEnum
from hashlib import sha256
import re
from typing import Any

from .document import Document, KeyValueRecord, SectionRecord, parse_bytes
from .metamorph import load_metamorph_registry


SCENE_DESCRIPTION_SCHEMA = "xenosculpt-xenodream-scene/v1"
_HOLON = re.compile(rb"Holon\\([0-9]+)$")
_METAMORPH = re.compile(rb"Holon\\([0-9]+)\\MM\\([0-9]+)$")


class Recognition(StrEnum):
    VERIFIED = "verified"
    OBSERVED = "observed"
    UNKNOWN = "unknown"


class SceneOperation(StrEnum):
    SET_SCALE = "set-scale-v1"
    SET_ROTATION = "set-rotation-v1"
    SET_POSITION = "set-position-v1"
    SET_COLOR_DENSITY = "set-color-density-v1"
    SET_FACE_WARP = "set-face-warp-v1"
    APPLY_SPHERE_PROFILE = "apply-sphere-profile-v1"
    APPLY_CYLINDER_PROFILE = "apply-cylinder-profile-v1"


@dataclass(frozen=True, slots=True)
class SceneBinding:
    revision_id: str
    artifact_sha256: str


@dataclass(frozen=True, slots=True)
class SceneVector:
    x: Decimal
    y: Decimal
    z: Decimal


@dataclass(frozen=True, slots=True)
class SceneTransform:
    scale: SceneVector | None
    rotation: SceneVector | None
    position: SceneVector | None
    raw_tokens: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SceneParameter:
    token_index: int
    raw: str
    name: str | None
    kind: str | None
    value: Decimal | int | None
    mapping_status: str


@dataclass(frozen=True, slots=True)
class SceneMetamorph:
    metamorph_index: int
    section_occurrence: int
    ordinal: int
    style: int | None
    declared_parameter_count: int | None
    parameters: tuple[SceneParameter, ...]
    operation_name: str | None
    schema_verified: bool


@dataclass(frozen=True, slots=True)
class SceneDiagnostic:
    code: str
    message: str
    section: str | None = None
    holon_index: int | None = None
    section_occurrence: int | None = None
    section_ordinal: int | None = None


@dataclass(frozen=True, slots=True)
class SceneNode:
    id: int | None
    holon_index: int
    section_occurrence: int
    section_ordinal: int
    type_code: int | None
    name: str | None
    group_id: int | None
    constructor: str | None
    recognition: Recognition
    transform: SceneTransform | None
    metamorphs: tuple[SceneMetamorph, ...]
    allowed_operations: tuple[SceneOperation, ...]
    write_blockers: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SceneDescription:
    binding: SceneBinding
    xdx_version: str | None
    declared_holon_count: int | None
    nodes: tuple[SceneNode, ...]
    diagnostics: tuple[SceneDiagnostic, ...]
    schema: str = field(default=SCENE_DESCRIPTION_SCHEMA, init=False)


class SceneDescriptionError(ValueError):
    """The source is not an XDX artifact that can be described truthfully."""


@dataclass(frozen=True, slots=True)
class _MetamorphRecord:
    holon_index: int
    metamorph_index: int
    section: bytes
    section_occurrence: int
    ordinal: int


def _text(value: bytes | None) -> str | None:
    return None if value is None else value.decode("ascii", errors="backslashreplace")


def _ascii_text(value: bytes | None) -> str | None:
    if value is None:
        return None
    try:
        return value.decode("ascii")
    except UnicodeDecodeError:
        return None


def _section_fields(
    document: Document, section: bytes, occurrence: int
) -> dict[bytes, list[bytes]]:
    values: dict[bytes, list[bytes]] = defaultdict(list)
    for record in document.records:
        if (
            isinstance(record, KeyValueRecord)
            and record.section == section
            and (record.section_occurrence or 0) == occurrence
        ):
            values[record.key].append(record.value)
    return dict(values)


def _unique(fields: dict[bytes, list[bytes]], key: bytes) -> bytes | None:
    values = fields.get(key, [])
    return values[0] if len(values) == 1 else None


def _integer(value: bytes | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value.decode("ascii"))
    except (UnicodeDecodeError, ValueError):
        return None


def _decimal(value: bytes) -> Decimal | None:
    try:
        result = Decimal(value.decode("ascii"))
    except (DecimalException, UnicodeDecodeError):
        return None
    return result if result.is_finite() else None


def _transform(fields: dict[bytes, list[bytes]]) -> SceneTransform | None:
    raw = _unique(fields, b"Transform")
    if raw is None:
        return None
    tokens = raw.split()
    def vector(start: int) -> SceneVector | None:
        selected = tokens[start : start + 3]
        if len(selected) != 3:
            return None
        values = tuple(_decimal(token) for token in selected)
        if any(value is None for value in values):
            return None
        numbers = tuple(value for value in values if value is not None)
        return SceneVector(*numbers)

    return SceneTransform(
        scale=vector(0),
        rotation=vector(6),
        position=vector(9),
        raw_tokens=tuple(
            token.decode("ascii", errors="backslashreplace") for token in tokens
        ),
    )


def _transform_is_malformed(fields: dict[bytes, list[bytes]]) -> bool:
    values = fields.get(b"Transform", [])
    if len(values) != 1:
        return False
    tokens = values[0].split()
    return len(tokens) != 12 or any(_decimal(token) is None for token in tokens)


def _metamorph_definition(
    *, version: str | None, style: int | None, declared: int | None
) -> dict[str, Any] | None:
    for definition in load_metamorph_registry()["operations"]:
        if str(definition["style"]) != str(style):
            continue
        if version not in definition.get("format_versions", []):
            return None
        if declared not in definition.get("verified_num_pars", []):
            return None
        return definition
    return None


def _describe_metamorph(
    document: Document,
    record: _MetamorphRecord,
    version: str | None,
) -> SceneMetamorph:
    fields = _section_fields(document, record.section, record.section_occurrence)
    style = _integer(_unique(fields, b"Style"))
    declared = _integer(_unique(fields, b"NumPars"))
    pars = _unique(fields, b"Pars")
    tokens = () if pars is None else tuple(pars.split())
    definition = _metamorph_definition(
        version=version, style=style, declared=declared
    )
    schema_verified = definition is not None and declared == len(tokens)
    if schema_verified and definition is not None:
        verified_vectors = definition.get("verified_pars_sha256")
        if verified_vectors is not None:
            schema_verified = (
                isinstance(verified_vectors, list)
                and pars is not None
                and sha256(pars).hexdigest() in verified_vectors
            )
    bindings = (
        {
            int(item["token_index"]): item
            for item in definition.get("token_bindings", [])
        }
        if schema_verified and definition is not None
        else {}
    )
    parameters: list[SceneParameter] = []
    for index, token in enumerate(tokens):
        raw = token.decode("ascii", errors="backslashreplace")
        binding = bindings.get(index)
        kind = None if binding is None else str(binding.get("kind"))
        value: Decimal | int | None = None
        if kind == "numeric":
            value = _decimal(token)
        elif kind == "choice":
            value = _integer(token)
        parameters.append(
            SceneParameter(
                token_index=index,
                raw=raw,
                name=None if binding is None else str(binding["name"]),
                kind=kind,
                value=value,
                mapping_status=(
                    "unresolved" if binding is None else str(binding["status"])
                ),
            )
        )
    return SceneMetamorph(
        metamorph_index=record.metamorph_index,
        section_occurrence=record.section_occurrence,
        ordinal=record.ordinal,
        style=style,
        declared_parameter_count=declared,
        parameters=tuple(parameters),
        operation_name=(
            str(definition.get("name"))
            if schema_verified and definition is not None
            else None
        ),
        schema_verified=schema_verified,
    )


def _metamorph_diagnostics(
    document: Document,
    record: _MetamorphRecord,
    version: str | None,
) -> list[SceneDiagnostic]:
    fields = _section_fields(document, record.section, record.section_occurrence)
    section = record.section.decode("ascii", errors="backslashreplace")

    def diagnostic(code: str, message: str) -> SceneDiagnostic:
        return SceneDiagnostic(
            code=code,
            message=message,
            section=section,
            holon_index=record.holon_index,
            section_occurrence=record.section_occurrence,
            section_ordinal=record.ordinal,
        )

    result: list[SceneDiagnostic] = []
    for key in (b"Style", b"NumPars", b"Pars"):
        count = len(fields.get(key, []))
        label = key.decode("ascii")
        if count == 0:
            result.append(
                diagnostic(
                    "missing-metamorph-field",
                    f"Metamorph is missing required {label} field",
                )
            )
        elif count > 1:
            result.append(
                diagnostic(
                    "duplicate-metamorph-field",
                    f"Metamorph has {count} {label} fields",
                )
            )

    style_raw = _unique(fields, b"Style")
    declared_raw = _unique(fields, b"NumPars")
    pars = _unique(fields, b"Pars")
    style = _integer(style_raw)
    declared = _integer(declared_raw)
    if style_raw is not None and style is None:
        result.append(
            diagnostic("malformed-metamorph-field", "Style must be an integer")
        )
    if declared_raw is not None and declared is None:
        result.append(
            diagnostic("malformed-metamorph-field", "NumPars must be an integer")
        )
    tokens = () if pars is None else tuple(pars.split())
    if declared is not None and pars is not None and declared != len(tokens):
        result.append(
            diagnostic(
                "metamorph-count-mismatch",
                f"NumPars declares {declared}; observed {len(tokens)} Pars tokens",
            )
        )

    definition = _metamorph_definition(
        version=version, style=style, declared=declared
    )
    if definition is not None and declared == len(tokens):
        bindings = {
            int(item["token_index"]): item
            for item in definition.get("token_bindings", [])
        }
        for index, token in enumerate(tokens):
            binding = bindings.get(index)
            if binding is None:
                continue
            kind = binding.get("kind")
            valid = True
            if kind == "numeric":
                valid = _decimal(token) is not None
            elif kind == "choice":
                value = _integer(token)
                choices = binding.get("choices", [])
                valid = value is not None and 0 <= value < len(choices)
            if not valid:
                result.append(
                    diagnostic(
                        "malformed-metamorph-parameter",
                        f"Pars token {index} is not a valid {kind} value",
                    )
                )
    return result


def _constructor(
    *,
    version: str | None,
    type_code: int | None,
    section_occurrence: int,
    metamorphs: tuple[SceneMetamorph, ...],
    ownership_ambiguous: bool,
) -> str | None:
    if (
        version != "1.220"
        or type_code != 1
        or section_occurrence != 0
        or ownership_ambiguous
    ):
        return None
    mm0 = [item for item in metamorphs if item.metamorph_index == 0]
    if (
        len(mm0) != 1
        or mm0[0].section_occurrence != 0
        or not mm0[0].schema_verified
    ):
        return None
    definition = _metamorph_definition(
        version=version,
        style=mm0[0].style,
        declared=mm0[0].declared_parameter_count,
    )
    if (
        definition is not None
        and definition.get("role") == "constructor"
        and mm0[0].operation_name
        in {
            "Cube",
            "Sphere",
            "Cylinder",
            "RoundCube",
            "Pipe",
            "Torus",
            "Cog",
            "SpiralShell",
        }
    ):
        return mm0[0].operation_name
    return None


def _operation_capabilities(
    *,
    version: str | None,
    constructor: str | None,
    fields: dict[bytes, list[bytes]],
    metamorphs: tuple[SceneMetamorph, ...],
    blockers: tuple[str, ...],
) -> tuple[SceneOperation, ...]:
    if version != "1.220" or blockers:
        return ()
    mm0_verified = any(
        item.metamorph_index == 0
        and item.section_occurrence == 0
        and item.schema_verified
        for item in metamorphs
    )
    def has_tokens(key: bytes, indexes: tuple[int, ...]) -> bool:
        values = fields.get(key, [])
        return len(values) == 1 and len(values[0].split()) > max(indexes)

    operations: list[SceneOperation] = []
    if constructor == "Cube":
        if has_tokens(b"Transform", (0, 1, 2)):
            operations.append(SceneOperation.SET_SCALE)
        if has_tokens(b"Transform", (6, 7, 8)):
            operations.append(SceneOperation.SET_ROTATION)
        if has_tokens(b"Transform", (9, 10, 11)):
            operations.append(SceneOperation.SET_POSITION)
        if len(fields.get(b"GradDensity", [])) == 1:
            operations.append(SceneOperation.SET_COLOR_DENSITY)
        if mm0_verified:
            operations.append(SceneOperation.SET_FACE_WARP)
    elif constructor == "Sphere":
        if has_tokens(b"Transform", (0, 1, 2)):
            operations.append(SceneOperation.SET_SCALE)
        if has_tokens(b"Transform", (9, 10, 11)):
            operations.append(SceneOperation.SET_POSITION)
        if mm0_verified:
            operations.append(SceneOperation.APPLY_SPHERE_PROFILE)
    elif constructor == "Cylinder" and mm0_verified:
        operations.append(SceneOperation.APPLY_CYLINDER_PROFILE)
    elif constructor in {"RoundCube", "Pipe", "Torus", "Cog", "SpiralShell"}:
        if has_tokens(b"Transform", (0, 1, 2)):
            operations.append(SceneOperation.SET_SCALE)
        if has_tokens(b"Transform", (9, 10, 11)):
            operations.append(SceneOperation.SET_POSITION)
    return tuple(operations)


def _header_value(document: Document, key: bytes) -> bytes | None:
    return _unique(_section_fields(document, b"Header", 0), key)


def _describe_document(
    document: Document, binding: SceneBinding
) -> SceneDescription:
    program_raw = _header_value(document, b"Program")
    version_raw = _header_value(document, b"Progversion")
    for key, value in (("Program", program_raw), ("Progversion", version_raw)):
        if value is None:
            continue
        try:
            value.decode("ascii")
        except UnicodeDecodeError as error:
            raise SceneDescriptionError(
                f"Header.{key} must contain ASCII text"
            ) from error
    if program_raw != b"XDX":
        raise SceneDescriptionError("source must contain one Header.Program=XDX value")
    version = _text(version_raw)
    declared_count = _integer(_header_value(document, b"NumHolons"))
    diagnostics: list[SceneDiagnostic] = []

    holon_records: list[tuple[int, SectionRecord, int]] = []
    metamorph_records: list[_MetamorphRecord] = []
    holon_ordinal = 0
    metamorph_ordinal = 0
    for record in document.records:
        if not isinstance(record, SectionRecord):
            continue
        holon_match = _HOLON.fullmatch(record.name)
        if holon_match is not None:
            holon_records.append((holon_ordinal, record, int(holon_match.group(1))))
            holon_ordinal += 1
            continue
        metamorph_match = _METAMORPH.fullmatch(record.name)
        if metamorph_match is not None:
            metamorph_records.append(
                _MetamorphRecord(
                    holon_index=int(metamorph_match.group(1)),
                    metamorph_index=int(metamorph_match.group(2)),
                    section=record.name,
                    section_occurrence=record.occurrence,
                    ordinal=metamorph_ordinal,
                )
            )
            metamorph_ordinal += 1

    if declared_count != len(holon_records):
        diagnostics.append(
            SceneDiagnostic(
                "holon-count-mismatch",
                f"Header.NumHolons declares {declared_count}; observed {len(holon_records)}",
                "Header",
            )
        )

    index_counts = Counter(index for _, _, index in holon_records)
    metamorph_counts = Counter(
        (item.holon_index, item.metamorph_index) for item in metamorph_records
    )
    for item in metamorph_records:
        diagnostics.extend(_metamorph_diagnostics(document, item, version))
        section_name = item.section.decode("ascii", errors="backslashreplace")
        owner_count = index_counts[item.holon_index]
        if owner_count == 0:
            diagnostics.append(
                SceneDiagnostic(
                    code="orphan-metamorph",
                    message=f"Metamorph has no Holon\\{item.holon_index} owner",
                    section=section_name,
                    holon_index=item.holon_index,
                    section_occurrence=item.section_occurrence,
                    section_ordinal=item.ordinal,
                )
            )
        elif owner_count > 1:
            diagnostics.append(
                SceneDiagnostic(
                    code="ambiguous-metamorph-owner",
                    message=f"Metamorph matches {owner_count} Holon\\{item.holon_index} sections",
                    section=section_name,
                    holon_index=item.holon_index,
                    section_occurrence=item.section_occurrence,
                    section_ordinal=item.ordinal,
                )
            )
        if metamorph_counts[(item.holon_index, item.metamorph_index)] > 1:
            diagnostics.append(
                SceneDiagnostic(
                    code="duplicate-metamorph-section",
                    message="Metamorph index occurs more than once for its Holon",
                    section=section_name,
                    holon_index=item.holon_index,
                    section_occurrence=item.section_occurrence,
                    section_ordinal=item.ordinal,
                )
            )
    raw_nodes: list[dict[str, Any]] = []
    for ordinal, section_record, holon_index in holon_records:
        section_name = section_record.name.decode("ascii", errors="backslashreplace")
        fields = _section_fields(
            document, section_record.name, section_record.occurrence
        )
        node_id = _integer(_unique(fields, b"ID"))
        type_code = _integer(_unique(fields, b"Type"))
        raw_name = _unique(fields, b"Name")
        name = _text(raw_name)
        group_id = _integer(_unique(fields, b"GroupID"))
        duplicate_fields = sorted(
            key.decode("ascii", errors="backslashreplace")
            for key in (b"ID", b"GroupID", b"Type", b"Name", b"Transform")
            if len(fields.get(key, [])) != 1
        )
        blockers = [f"duplicate-or-missing-{key}" for key in duplicate_fields]
        for key in (b"ID", b"GroupID", b"Type", b"Name", b"Transform"):
            count = len(fields.get(key, []))
            if count == 1:
                continue
            label = key.decode("ascii")
            diagnostics.append(
                SceneDiagnostic(
                    code=(
                        "missing-node-field" if count == 0 else "duplicate-node-field"
                    ),
                    message=(
                        f"Holon is missing required {label} field"
                        if count == 0
                        else f"Holon has {count} {label} fields"
                    ),
                    section=section_name,
                    holon_index=holon_index,
                    section_occurrence=section_record.occurrence,
                    section_ordinal=ordinal,
                )
            )
        for key, value in (
            (b"ID", node_id),
            (b"GroupID", group_id),
            (b"Type", type_code),
        ):
            raw = _unique(fields, key)
            if raw is not None and value is None:
                label = key.decode("ascii")
                diagnostics.append(
                    SceneDiagnostic(
                        code="malformed-node-field",
                        message=f"Holon {label} must be an integer",
                        section=section_name,
                        holon_index=holon_index,
                        section_occurrence=section_record.occurrence,
                        section_ordinal=ordinal,
                    )
                )
        if raw_name is not None and _ascii_text(raw_name) is None:
            blockers.append("non-ascii-name")
            diagnostics.append(
                SceneDiagnostic(
                    code="malformed-node-field",
                    message="Holon Name must contain ASCII text",
                    section=section_name,
                    holon_index=holon_index,
                    section_occurrence=section_record.occurrence,
                    section_ordinal=ordinal,
                )
            )
        elif raw_name == b"":
            blockers.append("empty-name")
            diagnostics.append(
                SceneDiagnostic(
                    code="malformed-node-field",
                    message="Holon Name must be non-empty",
                    section=section_name,
                    holon_index=holon_index,
                    section_occurrence=section_record.occurrence,
                    section_ordinal=ordinal,
                )
            )
        if _transform_is_malformed(fields):
            diagnostics.append(
                SceneDiagnostic(
                    code="malformed-transform",
                    message="Transform must contain twelve finite numeric tokens",
                    section=section_name,
                    holon_index=holon_index,
                    section_occurrence=section_record.occurrence,
                    section_ordinal=ordinal,
                )
            )
        ownership_ambiguous = index_counts[holon_index] != 1
        if ownership_ambiguous:
            blockers.append("ambiguous-metamorph-ownership")
            diagnostics.append(
                SceneDiagnostic(
                    code="duplicate-holon-index",
                    message=f"Holon index {holon_index} occurs more than once",
                    section=section_name,
                    holon_index=holon_index,
                    section_occurrence=section_record.occurrence,
                    section_ordinal=ordinal,
                )
            )
        owned_records = (
            ()
            if ownership_ambiguous
            else tuple(
                item
                for item in metamorph_records
                if item.holon_index == holon_index
            )
        )
        metamorphs = tuple(
            _describe_metamorph(document, item, version) for item in owned_records
        )
        raw_nodes.append(
            {
                "id": node_id,
                "holon_index": holon_index,
                "section_occurrence": section_record.occurrence,
                "section_ordinal": ordinal,
                "type_code": type_code,
                "name": name,
                "group_id": group_id,
                "fields": fields,
                "transform": _transform(fields),
                "metamorphs": metamorphs,
                "ownership_ambiguous": ownership_ambiguous,
                "blockers": blockers,
                "section": section_name,
            }
        )

    name_counts = Counter(
        item["name"] for item in raw_nodes if item["name"] is not None
    )
    id_counts = Counter(
        item["id"] for item in raw_nodes if item["id"] is not None
    )
    group_counts = Counter(
        item["id"]
        for item in raw_nodes
        if item["type_code"] == 0 and item["id"] is not None
    )
    for item in raw_nodes:
        group_id = item["group_id"]
        if group_id is None:
            continue
        if item["type_code"] == 0 and group_id == item["id"]:
            continue
        if group_id == item["id"]:
            diagnostics.append(
                SceneDiagnostic(
                    code="self-referential-group-id",
                    message=f"GroupID {group_id} refers to the same non-group Holon",
                    section=item["section"],
                    holon_index=item["holon_index"],
                    section_occurrence=item["section_occurrence"],
                    section_ordinal=item["section_ordinal"],
                )
            )
        elif group_counts[group_id] != 1:
            diagnostics.append(
                SceneDiagnostic(
                    code="unresolved-group-id",
                    message=f"GroupID {group_id} does not identify one observed group",
                    section=item["section"],
                    holon_index=item["holon_index"],
                    section_occurrence=item["section_occurrence"],
                    section_ordinal=item["section_ordinal"],
                )
            )
    nodes: list[SceneNode] = []
    for item in raw_nodes:
        blockers = list(item["blockers"])
        name = item["name"]
        if name is not None and name_counts[name] != 1:
            blockers.append("duplicate-name")
            diagnostics.append(
                SceneDiagnostic(
                    code="duplicate-holon-name",
                    message=f"Holon name {name!r} occurs more than once",
                    section=item["section"],
                    holon_index=item["holon_index"],
                    section_occurrence=item["section_occurrence"],
                    section_ordinal=item["section_ordinal"],
                )
            )
        node_id = item["id"]
        if node_id is not None and id_counts[node_id] != 1:
            blockers.append("duplicate-id")
            diagnostics.append(
                SceneDiagnostic(
                    code="duplicate-holon-id",
                    message=f"Holon ID {node_id} occurs more than once",
                    section=item["section"],
                    holon_index=item["holon_index"],
                    section_occurrence=item["section_occurrence"],
                    section_ordinal=item["section_ordinal"],
                )
            )
        constructor = _constructor(
            version=version,
            type_code=item["type_code"],
            section_occurrence=item["section_occurrence"],
            metamorphs=item["metamorphs"],
            ownership_ambiguous=item["ownership_ambiguous"],
        )
        if item["type_code"] == 1 and constructor is None:
            blockers.append("unverified-constructor-record")
        if constructor is not None:
            recognition = Recognition.VERIFIED
        elif item["type_code"] in {0, 2}:
            recognition = Recognition.OBSERVED
        else:
            recognition = Recognition.UNKNOWN
        blocker_tuple = tuple(dict.fromkeys(blockers))
        local_blockers = tuple(
            blocker
            for blocker in blocker_tuple
            if blocker
            in {
                "duplicate-or-missing-Name",
                "non-ascii-name",
                "empty-name",
                "ambiguous-metamorph-ownership",
                "duplicate-name",
                "unverified-constructor-record",
            }
        )
        operations = _operation_capabilities(
            version=version,
            constructor=constructor,
            fields=item["fields"],
            metamorphs=item["metamorphs"],
            blockers=local_blockers,
        )
        nodes.append(
            SceneNode(
                id=item["id"],
                holon_index=item["holon_index"],
                section_occurrence=item["section_occurrence"],
                section_ordinal=item["section_ordinal"],
                type_code=item["type_code"],
                name=name,
                group_id=item["group_id"],
                constructor=constructor,
                recognition=recognition,
                transform=(
                    item["transform"]
                    if constructor in {"Cube", "Sphere"}
                    else None
                ),
                metamorphs=item["metamorphs"],
                allowed_operations=operations,
                write_blockers=blocker_tuple,
            )
        )
    def diagnostic_key(item: SceneDiagnostic) -> tuple[object, ...]:
        return (
            item.code,
            -1 if item.holon_index is None else item.holon_index,
            -1 if item.section_occurrence is None else item.section_occurrence,
            -1 if item.section_ordinal is None else item.section_ordinal,
            "" if item.section is None else item.section,
            item.message,
        )

    return SceneDescription(
        binding=binding,
        xdx_version=version,
        declared_holon_count=declared_count,
        nodes=tuple(nodes),
        diagnostics=tuple(sorted(diagnostics, key=diagnostic_key)),
    )


def describe_xdx_scene(data: bytes, binding: SceneBinding) -> SceneDescription:
    """Describe XDX bytes without changing or normalizing them."""

    if not isinstance(data, bytes):
        raise TypeError("data must be bytes")
    if not isinstance(binding, SceneBinding):
        raise TypeError("binding must be SceneBinding")
    document = parse_bytes(data)
    if document.to_bytes() != data:
        raise SceneDescriptionError("source failed exact parser round trip")
    return _describe_document(document, binding)


def _vector_to_dict(value: SceneVector) -> list[str]:
    return [str(value.x), str(value.y), str(value.z)]


def scene_description_to_dict(scene: SceneDescription) -> dict[str, object]:
    """Return the stable JSON-compatible scene description."""

    def parameter(item: SceneParameter) -> dict[str, object]:
        value: str | int | None
        if isinstance(item.value, Decimal):
            value = str(item.value)
        else:
            value = item.value
        return {
            "token_index": item.token_index,
            "raw": item.raw,
            "name": item.name,
            "kind": item.kind,
            "value": value,
            "mapping_status": item.mapping_status,
        }

    def metamorph(item: SceneMetamorph) -> dict[str, object]:
        return {
            "metamorph_index": item.metamorph_index,
            "section_occurrence": item.section_occurrence,
            "ordinal": item.ordinal,
            "style": item.style,
            "declared_parameter_count": item.declared_parameter_count,
            "parameters": [parameter(value) for value in item.parameters],
            "operation_name": item.operation_name,
            "schema_verified": item.schema_verified,
        }

    def node(item: SceneNode) -> dict[str, object]:
        transform = item.transform
        return {
            "id": item.id,
            "holon_index": item.holon_index,
            "section_occurrence": item.section_occurrence,
            "section_ordinal": item.section_ordinal,
            "type_code": item.type_code,
            "name": item.name,
            "group_id": item.group_id,
            "constructor": item.constructor,
            "recognition": item.recognition.value,
            "transform": (
                None
                if transform is None
                else {
                    "scale": (
                        None
                        if transform.scale is None
                        else _vector_to_dict(transform.scale)
                    ),
                    "rotation": (
                        None
                        if transform.rotation is None
                        else _vector_to_dict(transform.rotation)
                    ),
                    "position": (
                        None
                        if transform.position is None
                        else _vector_to_dict(transform.position)
                    ),
                    "raw_tokens": list(transform.raw_tokens),
                }
            ),
            "metamorphs": [metamorph(value) for value in item.metamorphs],
            "allowed_operations": [value.value for value in item.allowed_operations],
            "write_blockers": list(item.write_blockers),
        }

    return {
        "schema": scene.schema,
        "binding": {
            "revision_id": scene.binding.revision_id,
            "artifact_sha256": scene.binding.artifact_sha256,
        },
        "xdx_version": scene.xdx_version,
        "declared_holon_count": scene.declared_holon_count,
        "nodes": [node(item) for item in scene.nodes],
        "diagnostics": [
            {
                "code": item.code,
                "message": item.message,
                "section": item.section,
                "holon_index": item.holon_index,
                "section_occurrence": item.section_occurrence,
                "section_ordinal": item.section_ordinal,
            }
            for item in scene.diagnostics
        ],
    }
