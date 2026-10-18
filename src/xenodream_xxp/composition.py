"""Evidence-bounded structural composition for XDX 1.220 Cube projects."""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal, DecimalException
from hashlib import sha256
from typing import Literal
import re

from ._cube_project_template import (
    _PROFILES,
    _cube_fields,
    _sphere_fields,
    _replace_field,
    _template_bytes,
    _validate_template,
)
from .diffing import diff_documents
from .document import (
    BlankRecord,
    Document,
    KeyValueRecord,
    RawRecord,
    Record,
    SectionRecord,
    parse_bytes,
)
from .generator import CubeSpec, SphereSpec, Vector3
from .scene import Recognition, SceneBinding, SceneOperation, describe_xdx_scene


class CompositionError(ValueError):
    """The requested structural transition is outside verified evidence."""


@dataclass(frozen=True, slots=True)
class AddCube:
    position: Vector3

    def __post_init__(self) -> None:
        if not isinstance(self.position, Vector3):
            raise TypeError("position must be Vector3")


@dataclass(frozen=True, slots=True)
class AddSphere:
    position: Vector3

    def __post_init__(self) -> None:
        if not isinstance(self.position, Vector3):
            raise TypeError("position must be Vector3")


@dataclass(frozen=True, slots=True)
class AddEmptyGroup:
    """Request the one evidenced Group1/Cube2 to Group1/Cube2/Group3 transition."""


@dataclass(frozen=True, slots=True)
class AddedCube:
    id: int
    holon_index: int
    name: str
    group_id: int
    constructor: Literal["Cube"] = "Cube"


@dataclass(frozen=True, slots=True)
class AddedSphere:
    id: int
    holon_index: int
    name: str
    group_id: int
    constructor: Literal["Sphere"] = "Sphere"


@dataclass(frozen=True, slots=True)
class AddedEmptyGroup:
    id: Literal[2] = 2
    holon_index: Literal[2] = 2
    name: Literal["Group3"] = "Group3"
    group_id: Literal[2] = 2
    kind: Literal["group"] = "group"


@dataclass(frozen=True, slots=True)
class StructuralChange:
    kind: Literal["section_added"]
    section: str
    section_occurrence: int
    record_count: int


@dataclass(frozen=True, slots=True)
class CompositionRewrite:
    data: bytes
    differences: tuple[dict[str, object], ...]
    structural_changes: tuple[StructuralChange, ...]
    added: AddedCube | AddedSphere | AddedEmptyGroup


@dataclass(frozen=True, slots=True)
class AdditionOffer:
    operation: Literal["add-cube-v1", "add-sphere-v1"]
    constructor: Literal["Cube", "Sphere"]
    allocated_name: str
    allocated_id: int
    holon_index: int
    group_id: int


@dataclass(frozen=True, slots=True)
class AdditionBlocker:
    operation: Literal["add-cube-v1", "add-sphere-v1"]
    code: str
    message: str


@dataclass(frozen=True, slots=True)
class AdditionCapabilities:
    binding: SceneBinding
    available: tuple[AdditionOffer, ...]
    blockers: tuple[AdditionBlocker, ...]
    schema: str = "xenosculpt-xenodream-additions/v1"


@dataclass(frozen=True, slots=True)
class _FlatCubeAppendContext:
    source: Document
    cube_count: int
    target: Document
    insertion_index: int
    new_holon_index: int
    source_x: bytes
    constructor: Literal["Cube", "Sphere"] = "Cube"


_EDITABLE_TRANSFORM_TOKENS = frozenset((0, 1, 2, 6, 7, 8, 9, 10, 11))
_EMPTY_GROUP_SOURCE_SHA256 = (
    "fcba6d61f2af4cf79c1e86a20b570a0bb0039db3fb79c9d73c84e842430fc7a0"
)
_EMPTY_GROUP_TARGET_SHA256 = (
    "c207830dcb70a1a05b44f583cb3199752e634803ad9035296c6da7b1c8b53b4e"
)


def _mask_tokens(value: bytes, reference: bytes, indexes: frozenset[int]) -> bytes | None:
    source_tokens = list(re.finditer(rb"\S+", value))
    reference_tokens = list(re.finditer(rb"\S+", reference))
    if len(source_tokens) != len(reference_tokens):
        return None
    masked = value
    for index in sorted(indexes, reverse=True):
        if index >= len(source_tokens):
            return None
        source_token = source_tokens[index]
        replacement = reference_tokens[index].group()
        masked = masked[: source_token.start()] + replacement + masked[source_token.end() :]
    return masked


def _editable_value_matches(
    record: KeyValueRecord,
    reference: KeyValueRecord,
    cube_count: int,
) -> bool:
    cube_sections = {f"Holon\\{index}".encode("ascii") for index in range(1, cube_count + 1)}
    metamorph_sections = {section + b"\\MM\\0" for section in cube_sections}
    if record.section in cube_sections and record.key == b"Transform":
        return _mask_tokens(
            record.value,
            reference.value,
            _EDITABLE_TRANSFORM_TOKENS,
        ) == reference.value
    if record.section in cube_sections and record.key == b"GradDensity":
        if re.fullmatch(rb"-?\d+\.\d{3}", record.value) is None:
            return False
        try:
            value = Decimal(record.value.decode("ascii"))
        except (DecimalException, UnicodeDecodeError):
            return False
        return value.is_finite() and record.content == b"GradDensity=" + record.value
    if record.section in metamorph_sections and record.key == b"Pars":
        return _mask_tokens(record.value, reference.value, frozenset((0,))) == reference.value
    return False


def _matches_source_profile(
    source: Document,
    reference: Document,
    cube_count: int,
) -> bool:
    if len(source.records) != len(reference.records):
        return False
    for record, expected in zip(source.records, reference.records, strict=True):
        if type(record) is not type(expected) or record.ending != expected.ending:
            return False
        if isinstance(record, KeyValueRecord) and isinstance(expected, KeyValueRecord):
            if (
                record.key != expected.key
                or record.section != expected.section
                or record.section_occurrence != expected.section_occurrence
            ):
                return False
            if record.content == expected.content and record.value == expected.value:
                continue
            if not _editable_value_matches(record, expected, cube_count):
                return False
            continue
        if isinstance(record, SectionRecord) and isinstance(expected, SectionRecord):
            if (
                record.content != expected.content
                or record.name != expected.name
                or record.occurrence != expected.occurrence
            ):
                return False
            continue
        if isinstance(record, (BlankRecord, RawRecord)) and isinstance(
            expected, (BlankRecord, RawRecord)
        ):
            if record.content != expected.content:
                return False
            continue
        return False
    return True


def _unique_key(
    document: Document, section: bytes, key: bytes
) -> tuple[int, KeyValueRecord]:
    matches = [
        (index, record)
        for index, record in enumerate(document.records)
        if isinstance(record, KeyValueRecord)
        and record.section == section
        and record.section_occurrence == 0
        and record.key == key
    ]
    if len(matches) != 1:
        raise CompositionError(
            f"expected one {section.decode()}.{key.decode()} record"
        )
    return matches[0]


def _unique_section(document: Document, name: bytes) -> int:
    matches = [
        index
        for index, record in enumerate(document.records)
        if isinstance(record, SectionRecord)
        and record.name == name
        and record.occurrence == 0
    ]
    if len(matches) != 1:
        raise CompositionError(f"expected one [{name.decode()}] section")
    return matches[0]


def _admit(data: bytes) -> _FlatCubeAppendContext:
    source = parse_bytes(data)
    if source.to_bytes() != data:
        raise CompositionError("input failed exact parser round trip")
    digest = sha256(data).hexdigest()
    scene = describe_xdx_scene(data, SceneBinding(digest, digest))
    if scene.xdx_version != "1.220" or scene.diagnostics:
        raise CompositionError("source is not a canonical flat Cube profile")
    if len(scene.nodes) not in (2, 3):
        raise CompositionError("add Cube requires exactly one or two existing Cubes")
    root, *cubes = scene.nodes
    cube_count = len(cubes)
    if (
        root.id != 0
        or root.holon_index != 0
        or root.type_code != 0
        or root.name != "Group1"
        or root.group_id != 0
    ):
        raise CompositionError("source is not a canonical flat Cube profile")
    for index, cube in enumerate(cubes, start=1):
        if (
            cube.id != index
            or cube.holon_index != index
            or cube.section_occurrence != 0
            or cube.name != f"Cube{index + 1}"
            or cube.group_id != 0
            or cube.constructor != "Cube"
            or cube.recognition is not Recognition.VERIFIED
            or len(cube.metamorphs) != 1
            or cube.metamorphs[0].metamorph_index != 0
            or SceneOperation.SET_POSITION not in cube.allowed_operations
        ):
            raise CompositionError("source is not a canonical flat Cube profile")

    source_profile = _PROFILES[(CubeSpec,) * cube_count]
    source_template = parse_bytes(_template_bytes(source_profile))
    _validate_template(source_template, source_profile)
    if not _matches_source_profile(source, source_template, cube_count):
        raise CompositionError("source is not a canonical flat Cube profile")

    target_profile = _PROFILES[(CubeSpec,) * (cube_count + 1)]
    target = parse_bytes(_template_bytes(target_profile))
    _validate_template(target, target_profile)
    insertion_index = _unique_section(source, b"Gradients")
    last_mm_index = _unique_section(
        source, f"Holon\\{cube_count}\\MM\\0".encode("ascii")
    )
    if insertion_index <= last_mm_index:
        raise CompositionError("Cube insertion point is not canonical")
    return _FlatCubeAppendContext(
        source=source,
        cube_count=cube_count,
        target=target,
        insertion_index=insertion_index,
        new_holon_index=cube_count + 1,
        source_x=target_profile.objects[-1].source_x,
    )


def _admit_sphere(data: bytes) -> _FlatCubeAppendContext:
    source = parse_bytes(data)
    if source.to_bytes() != data:
        raise CompositionError("input failed exact parser round trip")
    digest = sha256(data).hexdigest()
    scene = describe_xdx_scene(data, SceneBinding(digest, digest))
    if scene.xdx_version != "1.220" or scene.diagnostics:
        raise CompositionError("source is not a canonical flat Cube profile")
    if len(scene.nodes) != 2:
        raise CompositionError("add Sphere requires exactly one existing Cube")
    root, cube = scene.nodes
    if (
        root.id != 0
        or root.holon_index != 0
        or root.type_code != 0
        or root.name != "Group1"
        or root.group_id != 0
        or cube.id != 1
        or cube.holon_index != 1
        or cube.section_occurrence != 0
        or cube.name != "Cube2"
        or cube.group_id != 0
        or cube.constructor != "Cube"
        or cube.recognition is not Recognition.VERIFIED
        or len(cube.metamorphs) != 1
        or cube.metamorphs[0].metamorph_index != 0
        or SceneOperation.SET_POSITION not in cube.allowed_operations
    ):
        raise CompositionError("source is not a canonical flat Cube profile")

    source_profile = _PROFILES[(CubeSpec,)]
    source_template = parse_bytes(_template_bytes(source_profile))
    _validate_template(source_template, source_profile)
    if not _matches_source_profile(source, source_template, 1):
        raise CompositionError("source is not a canonical flat Cube profile")

    target_profile = _PROFILES[(CubeSpec, SphereSpec)]
    target = parse_bytes(_template_bytes(target_profile))
    _validate_template(target, target_profile)
    insertion_index = _unique_section(source, b"Gradients")
    last_mm_index = _unique_section(source, b"Holon\\1\\MM\\0")
    if insertion_index <= last_mm_index:
        raise CompositionError("Sphere insertion point is not canonical")
    return _FlatCubeAppendContext(
        source=source,
        cube_count=1,
        target=target,
        insertion_index=insertion_index,
        new_holon_index=2,
        source_x=target_profile.objects[-1].source_x,
        constructor="Sphere",
    )


def _target_span(context: _FlatCubeAppendContext) -> tuple[Record, ...]:
    section = f"Holon\\{context.new_holon_index}".encode("ascii")
    start = _unique_section(context.target, section)
    end = _unique_section(context.target, b"Gradients")
    if start >= end:
        raise CompositionError("target Cube span is not canonical")
    return context.target.records[start:end]


def _replace_count(document: Document, expected: int, value: int) -> Document:
    index, record = _unique_key(document, b"Header", b"NumHolons")
    expected_bytes = str(expected).encode("ascii")
    if record.value != expected_bytes or record.content != b"NumHolons=" + expected_bytes:
        raise CompositionError("Header.NumHolons does not match the admitted scene")
    value_bytes = str(value).encode("ascii")
    records = list(document.records)
    records[index] = replace(
        record,
        content=b"NumHolons=" + value_bytes,
        value=value_bytes,
    )
    return Document(tuple(records))


def _positioned_span(
    context: _FlatCubeAppendContext, position: Vector3
) -> tuple[Record, ...]:
    span = Document(_target_span(context))
    field_factory = _cube_fields if context.constructor == "Cube" else _sphere_fields
    fields = {
        field.token_index: field
        for field in field_factory(context.new_holon_index, context.source_x)
        if field.key == b"Transform" and field.token_index in (9, 10, 11)
    }
    try:
        for token_index, value in zip((9, 10, 11), (position.x, position.y, position.z)):
            span = _replace_field(span, fields[token_index], value)
    except ValueError as error:
        message = str(error).replace("5-place", "five-place")
        raise CompositionError(message) from error
    return span.records


def _audit(
    context: _FlatCubeAppendContext,
    output: Document,
    inserted: tuple[Record, ...],
    position: Vector3,
) -> None:
    reference_span = _target_span(context)
    if len(inserted) != len(reference_span):
        raise CompositionError(f"inserted {context.constructor} does not match the canonical target span")
    transform_section = f"Holon\\{context.new_holon_index}".encode("ascii")
    expected_position = tuple(
        format(value, ".5f").encode("ascii")
        for value in (position.x, position.y, position.z)
    )
    for record, reference in zip(inserted, reference_span, strict=True):
        if (
            isinstance(record, KeyValueRecord)
            and isinstance(reference, KeyValueRecord)
            and record.section == transform_section
            and record.key == b"Transform"
        ):
            if (
                record.ending != reference.ending
                or record.section_occurrence != reference.section_occurrence
                or _mask_tokens(record.value, reference.value, frozenset((9, 10, 11)))
                != reference.value
                or tuple(record.value.split()[9:12]) != expected_position
                or record.content != b"Transform=" + record.value
            ):
                raise CompositionError(
                    f"inserted {context.constructor} does not match the canonical target span"
                )
        elif record != reference:
            raise CompositionError(
                f"inserted {context.constructor} does not match the canonical target span"
            )

    output_bytes = output.to_bytes()
    reparsed = parse_bytes(output_bytes)
    if reparsed.to_bytes() != output_bytes:
        raise CompositionError("composed output failed exact parser round trip")

    after_insertion = context.insertion_index
    output_records = list(reparsed.records)
    actual_span = tuple(
        output_records[after_insertion : after_insertion + len(inserted)]
    )
    if actual_span != inserted:
        raise CompositionError(f"inserted {context.constructor} record span changed during composition")

    reconstructed = Document(
        tuple(
            output_records[:after_insertion]
            + output_records[after_insertion + len(inserted) :]
        )
    )
    reconstructed = _replace_count(
        reconstructed,
        context.cube_count + 2,
        context.cube_count + 1,
    )
    if reconstructed.to_bytes() != context.source.to_bytes():
        raise CompositionError("structural audit could not reconstruct the source")

    digest = sha256(output_bytes).hexdigest()
    scene = describe_xdx_scene(output_bytes, SceneBinding(digest, digest))
    expected_names = (
        ["Group1"]
        + [f"Cube{index + 1}" for index in range(1, context.cube_count + 1)]
        + [f"{context.constructor}{context.new_holon_index + 1}"]
    )
    if scene.diagnostics or [node.name for node in scene.nodes] != expected_names:
        raise CompositionError("composed scene failed semantic audit")
    added = scene.nodes[-1]
    if (
        added.id != context.new_holon_index
        or added.holon_index != context.new_holon_index
        or added.group_id != 0
        or added.constructor != context.constructor
        or added.recognition is not Recognition.VERIFIED
        or SceneOperation.SET_POSITION not in added.allowed_operations
    ):
        raise CompositionError(f"composed {context.constructor} identity failed semantic audit")


def append_cube(data: bytes, operation: AddCube) -> CompositionRewrite:
    """Append one canonical Cube, changing only the admitted header record."""

    if not isinstance(data, bytes):
        raise TypeError("data must be bytes")
    if not isinstance(operation, AddCube):
        raise TypeError("operation must be AddCube")
    context = _admit(data)
    inserted = _positioned_span(context, operation.position)
    with_count = _replace_count(
        context.source,
        context.cube_count + 1,
        context.cube_count + 2,
    )
    records = list(with_count.records)
    records[context.insertion_index:context.insertion_index] = inserted
    output = parse_bytes(Document(tuple(records)).to_bytes())
    _audit(context, output, inserted, operation.position)

    index = context.new_holon_index
    added = AddedCube(index, index, f"Cube{index + 1}", 0)
    metamorph_name = f"Holon\\{index}\\MM\\0"
    metamorph_start = next(
        (
            record_index
            for record_index, record in enumerate(inserted)
            if isinstance(record, SectionRecord)
            and record.name == metamorph_name.encode("ascii")
            and record.occurrence == 0
        ),
        None,
    )
    if metamorph_start is None:
        raise CompositionError("inserted Cube is missing its canonical MM\\0 section")
    changes = (
        StructuralChange(
            kind="section_added",
            section=f"Holon\\{index}",
            section_occurrence=0,
            record_count=metamorph_start,
        ),
        StructuralChange(
            kind="section_added",
            section=metamorph_name,
            section_occurrence=0,
            record_count=len(inserted) - metamorph_start,
        ),
    )
    return CompositionRewrite(
        data=output.to_bytes(),
        differences=tuple(diff_documents(context.source, output)),
        structural_changes=changes,
        added=added,
    )


def append_sphere(data: bytes, operation: AddSphere) -> CompositionRewrite:
    """Append one canonical Sphere to an admitted one-Cube composition."""

    if not isinstance(data, bytes):
        raise TypeError("data must be bytes")
    if not isinstance(operation, AddSphere):
        raise TypeError("operation must be AddSphere")
    context = _admit_sphere(data)
    inserted = _positioned_span(context, operation.position)
    with_count = _replace_count(context.source, 2, 3)
    records = list(with_count.records)
    records[context.insertion_index:context.insertion_index] = inserted
    output = parse_bytes(Document(tuple(records)).to_bytes())
    _audit(context, output, inserted, operation.position)

    index = context.new_holon_index
    added = AddedSphere(index, index, "Sphere3", 0)
    metamorph_name = f"Holon\\{index}\\MM\\0"
    metamorph_start = next(
        (
            record_index
            for record_index, record in enumerate(inserted)
            if isinstance(record, SectionRecord)
            and record.name == metamorph_name.encode("ascii")
            and record.occurrence == 0
        ),
        None,
    )
    if metamorph_start is None:
        raise CompositionError("inserted Sphere is missing its canonical MM\\0 section")
    changes = (
        StructuralChange("section_added", f"Holon\\{index}", 0, metamorph_start),
        StructuralChange(
            "section_added",
            metamorph_name,
            0,
            len(inserted) - metamorph_start,
        ),
    )
    return CompositionRewrite(
        data=output.to_bytes(),
        differences=tuple(diff_documents(context.source, output)),
        structural_changes=changes,
        added=added,
    )


def _empty_group_span(source: Document) -> tuple[Record, ...]:
    start = _unique_section(source, b"Holon\\0")
    end = _unique_section(source, b"Holon\\1")
    if end - start != 36:
        raise CompositionError("source Group1 span is not the evidenced record family")
    result: list[Record] = []
    for record in source.records[start:end]:
        if isinstance(record, SectionRecord):
            if record.name != b"Holon\\0" or record.occurrence != 0:
                raise CompositionError("source Group1 section is not canonical")
            result.append(
                replace(record, content=b"[Holon\\2]", name=b"Holon\\2")
            )
            continue
        if isinstance(record, KeyValueRecord):
            if record.section != b"Holon\\0" or record.section_occurrence != 0:
                raise CompositionError("source Group1 fields are not canonical")
            value = record.value
            if record.key in (b"ID", b"GroupID"):
                value = b"2"
            elif record.key == b"Name":
                value = b"Group3"
            result.append(
                replace(
                    record,
                    content=record.key + b"=" + value,
                    value=value,
                    section=b"Holon\\2",
                )
            )
            continue
        result.append(record)
    return tuple(result)


def append_empty_group(data: bytes, operation: AddEmptyGroup) -> CompositionRewrite:
    """Append the exact native-observed empty Group3 record family."""

    if not isinstance(data, bytes):
        raise TypeError("data must be bytes")
    if not isinstance(operation, AddEmptyGroup):
        raise TypeError("operation must be AddEmptyGroup")
    try:
        context = _admit_sphere(data)
    except CompositionError as error:
        raise CompositionError(
            "add empty group requires exactly one existing Cube in the canonical flat profile"
        ) from error
    inserted = _empty_group_span(context.source)
    with_count = _replace_count(context.source, 2, 3)
    records = list(with_count.records)
    records[context.insertion_index:context.insertion_index] = inserted
    output = parse_bytes(Document(tuple(records)).to_bytes())
    output_bytes = output.to_bytes()
    if parse_bytes(output_bytes).to_bytes() != output_bytes:
        raise CompositionError("composed output failed exact parser round trip")

    actual_span = output.records[
        context.insertion_index : context.insertion_index + len(inserted)
    ]
    if actual_span != inserted:
        raise CompositionError("inserted Group3 record span changed during composition")
    reconstructed_records = list(output.records)
    del reconstructed_records[
        context.insertion_index : context.insertion_index + len(inserted)
    ]
    reconstructed = _replace_count(Document(tuple(reconstructed_records)), 3, 2)
    if reconstructed.to_bytes() != data:
        raise CompositionError("structural audit could not reconstruct the source")

    if sha256(data).hexdigest() == _EMPTY_GROUP_SOURCE_SHA256:
        if sha256(output_bytes).hexdigest() != _EMPTY_GROUP_TARGET_SHA256:
            raise CompositionError("canonical Group3 output does not match native evidence")

    digest = sha256(output_bytes).hexdigest()
    scene = describe_xdx_scene(output_bytes, SceneBinding(digest, digest))
    if scene.diagnostics or [node.name for node in scene.nodes] != [
        "Group1",
        "Cube2",
        "Group3",
    ]:
        raise CompositionError("composed Group3 scene failed semantic audit")
    group = scene.nodes[-1]
    if (
        group.id != 2
        or group.holon_index != 2
        or group.group_id != 2
        or group.type_code != 0
        or group.constructor is not None
        or group.allowed_operations
    ):
        raise CompositionError("composed Group3 identity failed semantic audit")

    return CompositionRewrite(
        data=output_bytes,
        differences=tuple(diff_documents(context.source, output)),
        structural_changes=(
            StructuralChange("section_added", "Holon\\2", 0, len(inserted)),
        ),
        added=AddedEmptyGroup(),
    )


def addition_capabilities(
    data: bytes, binding: SceneBinding
) -> AdditionCapabilities:
    """Report additions admitted by the exact writer predicates."""

    if not isinstance(data, bytes):
        raise TypeError("data must be bytes")
    if not isinstance(binding, SceneBinding):
        raise TypeError("binding must be SceneBinding")
    available: list[AdditionOffer] = []
    blockers: list[AdditionBlocker] = []
    for operation, constructor, admit in (
        ("add-cube-v1", "Cube", _admit),
        ("add-sphere-v1", "Sphere", _admit_sphere),
    ):
        try:
            context = admit(data)
        except CompositionError as error:
            blockers.append(
                AdditionBlocker(operation, "source-profile-not-admitted", str(error))
            )
            continue
        index = context.new_holon_index
        available.append(
            AdditionOffer(
                operation=operation,
                constructor=constructor,
                allocated_name=f"{constructor}{index + 1}",
                allocated_id=index,
                holon_index=index,
                group_id=0,
            )
        )
    return AdditionCapabilities(binding, tuple(available), tuple(blockers))
