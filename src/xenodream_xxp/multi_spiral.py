"""One evidence-bounded composition of interleaved closed holons."""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from enum import StrEnum

from .document import Document, KeyValueRecord, SectionRecord, parse_bytes
from .generator import (
    ClosedConstructorName,
    ClosedConstructorSpec,
    GenerationError,
    TemplateMismatchError,
    Vector3,
    compile_closed_constructor,
)
from .scene import Recognition, SceneBinding, SceneOperation, describe_xdx_scene


INTERACTING_SPIRAL_COMPILER_PROFILE = (
    "xdx-1.220-interleaved-eight-closed-holons-2026-10-18"
)


class InteractingSpiralProfile(StrEnum):
    INTERLEAVED_EIGHT_V1 = "interleaved-eight/v1"


@dataclass(frozen=True, slots=True)
class InteractingSpiralsSpec:
    profile: InteractingSpiralProfile = InteractingSpiralProfile.INTERLEAVED_EIGHT_V1

    def __post_init__(self) -> None:
        if not isinstance(self.profile, InteractingSpiralProfile):
            raise TypeError("profile must be InteractingSpiralProfile")


@dataclass(frozen=True, slots=True)
class SpiralMember:
    holon_index: int
    constructor: ClosedConstructorName
    scale: Vector3
    position: Vector3


D = Decimal
_INTERLEAVED_EIGHT = (
    SpiralMember(1, ClosedConstructorName.SPIRAL_SHELL, Vector3(D("28"), D("28"), D("28")), Vector3(D("28"), D("0"), D("-30"))),
    SpiralMember(2, ClosedConstructorName.TORUS, Vector3(D("26"), D("26"), D("26")), Vector3(D("-28"), D("0"), D("-30"))),
    SpiralMember(3, ClosedConstructorName.COG, Vector3(D("25"), D("25"), D("25")), Vector3(D("0"), D("28"), D("-10"))),
    SpiralMember(4, ClosedConstructorName.PIPE, Vector3(D("27"), D("27"), D("27")), Vector3(D("0"), D("-28"), D("-10"))),
    SpiralMember(5, ClosedConstructorName.ROUND_CUBE, Vector3(D("24"), D("24"), D("24")), Vector3(D("-28"), D("0"), D("10"))),
    SpiralMember(6, ClosedConstructorName.SPIRAL_SHELL, Vector3(D("30"), D("30"), D("30")), Vector3(D("28"), D("0"), D("10"))),
    SpiralMember(7, ClosedConstructorName.PIPE, Vector3(D("26"), D("26"), D("26")), Vector3(D("0"), D("-28"), D("30"))),
    SpiralMember(8, ClosedConstructorName.COG, Vector3(D("25"), D("25"), D("25")), Vector3(D("0"), D("28"), D("30"))),
)


def interacting_spiral_members(
    spec: InteractingSpiralsSpec,
) -> tuple[SpiralMember, ...]:
    if not isinstance(spec, InteractingSpiralsSpec):
        raise TypeError("spec must be InteractingSpiralsSpec")
    if spec.profile is InteractingSpiralProfile.INTERLEAVED_EIGHT_V1:
        return _INTERLEAVED_EIGHT
    raise GenerationError(f"unsupported interacting spiral profile: {spec.profile}")


def _section_index(document: Document, name: bytes) -> int:
    matches = [
        index
        for index, record in enumerate(document.records)
        if isinstance(record, SectionRecord)
        and record.name == name
        and record.occurrence == 0
    ]
    if len(matches) != 1:
        raise TemplateMismatchError(f"expected one section {name!r}")
    return matches[0]


def _replace_header_count(records: list[object], count: int) -> None:
    matches = [
        index
        for index, record in enumerate(records)
        if isinstance(record, KeyValueRecord)
        and record.section == b"Header"
        and record.section_occurrence == 0
        and record.key == b"NumHolons"
    ]
    if len(matches) != 1:
        raise TemplateMismatchError("expected one Header.NumHolons")
    index = matches[0]
    record = records[index]
    assert isinstance(record, KeyValueRecord)
    value = str(count).encode("ascii")
    records[index] = replace(record, content=b"NumHolons=" + value, value=value)


def _member_block(member: SpiralMember) -> tuple[object, ...]:
    source = parse_bytes(
        compile_closed_constructor(
            ClosedConstructorSpec(
                member.constructor,
                scale=member.scale,
                position=member.position,
            )
        )
    )
    start = _section_index(source, b"Holon\\1")
    end = _section_index(source, b"Gradients")
    old_section = b"Holon\\1"
    new_section = f"Holon\\{member.holon_index}".encode("ascii")
    old_mm = old_section + b"\\MM\\0"
    new_mm = new_section + b"\\MM\\0"
    rewritten: list[object] = []
    for record in source.records[start:end]:
        if isinstance(record, SectionRecord) and record.name in (old_section, old_mm):
            name = new_section if record.name == old_section else new_mm
            rewritten.append(
                replace(record, content=b"[" + name + b"]", name=name, occurrence=0)
            )
            continue
        if isinstance(record, KeyValueRecord) and record.section in (old_section, old_mm):
            section = new_section if record.section == old_section else new_mm
            updated = replace(record, section=section, section_occurrence=0)
            if record.section == old_section and record.key == b"ID":
                value = str(member.holon_index).encode("ascii")
                updated = replace(updated, content=b"ID=" + value, value=value)
            elif record.section == old_section and record.key == b"Name":
                value = f"{member.constructor.value}{member.holon_index + 1}".encode("ascii")
                updated = replace(updated, content=b"Name=" + value, value=value)
            rewritten.append(updated)
            continue
        rewritten.append(record)
    return tuple(rewritten)


def _audit(data: bytes, members: tuple[SpiralMember, ...]) -> None:
    if parse_bytes(data).to_bytes() != data:
        raise TemplateMismatchError("interacting spiral failed exact parser round trip")
    scene = describe_xdx_scene(data, SceneBinding("0" * 64, "0" * 64))
    if scene.xdx_version != "1.220" or scene.declared_holon_count != 9:
        raise TemplateMismatchError("interacting spiral header does not match profile")
    if scene.diagnostics or len(scene.nodes) != 9:
        raise TemplateMismatchError("interacting spiral scene has structural diagnostics")
    root = scene.nodes[0]
    if (root.holon_index, root.id, root.name, root.group_id) != (0, 0, "Group1", 0):
        raise TemplateMismatchError("interacting spiral root does not match profile")
    document = parse_bytes(data)
    for node, member in zip(scene.nodes[1:], members):
        expected_name = f"{member.constructor.value}{member.holon_index + 1}"
        section = f"Holon\\{member.holon_index}".encode("ascii")
        transform_records = [
            record
            for record in document.records
            if isinstance(record, KeyValueRecord)
            and record.section == section
            and record.section_occurrence == 0
            and record.key == b"Transform"
        ]
        transform_matches = False
        if len(transform_records) == 1:
            tokens = transform_records[0].value.split()
            try:
                actual = tuple(
                    Decimal(tokens[index].decode("ascii"))
                    for index in (0, 1, 2, 9, 10, 11)
                )
                transform_matches = actual == (
                    member.scale.x,
                    member.scale.y,
                    member.scale.z,
                    member.position.x,
                    member.position.y,
                    member.position.z,
                )
            except (ArithmeticError, UnicodeDecodeError):
                transform_matches = False
        if (
            node.holon_index != member.holon_index
            or node.id != member.holon_index
            or node.name != expected_name
            or node.group_id != 0
            or node.constructor != member.constructor.value
            or node.recognition is not Recognition.VERIFIED
            or node.allowed_operations
            != (SceneOperation.SET_SCALE, SceneOperation.SET_POSITION)
            or not transform_matches
        ):
            raise TemplateMismatchError(
                f"interacting spiral member {member.holon_index} failed semantic audit"
            )


def compile_interacting_spirals(spec: InteractingSpiralsSpec | None = None) -> bytes:
    project = spec if spec is not None else InteractingSpiralsSpec()
    if not isinstance(project, InteractingSpiralsSpec):
        raise TypeError("spec must be InteractingSpiralsSpec")
    members = interacting_spiral_members(project)
    scaffold = parse_bytes(
        compile_closed_constructor(
            ClosedConstructorSpec(
                members[0].constructor,
                scale=members[0].scale,
                position=members[0].position,
            )
        )
    )
    object_start = _section_index(scaffold, b"Holon\\1")
    tail_start = _section_index(scaffold, b"Gradients")
    records: list[object] = list(scaffold.records[:object_start])
    _replace_header_count(records, 9)
    for member in members:
        records.extend(_member_block(member))
    records.extend(scaffold.records[tail_start:])
    output = Document(tuple(records)).to_bytes()
    _audit(output, members)
    return output
