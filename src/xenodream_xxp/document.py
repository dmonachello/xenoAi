"""Ordered, byte-preserving records for XenoDream X parameter files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias


@dataclass(frozen=True, slots=True)
class BlankRecord:
    content: bytes
    ending: bytes


@dataclass(frozen=True, slots=True)
class RawRecord:
    content: bytes
    ending: bytes


@dataclass(frozen=True, slots=True)
class SectionRecord:
    content: bytes
    ending: bytes
    name: bytes
    occurrence: int


@dataclass(frozen=True, slots=True)
class KeyValueRecord:
    content: bytes
    ending: bytes
    key: bytes
    value: bytes
    section: bytes | None
    section_occurrence: int | None


Record: TypeAlias = BlankRecord | RawRecord | SectionRecord | KeyValueRecord


@dataclass(frozen=True, slots=True)
class Document:
    """A sequence of parsed records that retains every source byte."""

    records: tuple[Record, ...]

    @property
    def sections(self) -> tuple[SectionRecord, ...]:
        return tuple(
            record for record in self.records if isinstance(record, SectionRecord)
        )

    def to_bytes(self) -> bytes:
        return b"".join(record.content + record.ending for record in self.records)


def _physical_lines(data: bytes) -> list[tuple[bytes, bytes]]:
    lines: list[tuple[bytes, bytes]] = []
    start = 0
    index = 0
    while index < len(data):
        byte = data[index]
        if byte not in (10, 13):
            index += 1
            continue

        if byte == 13 and index + 1 < len(data) and data[index + 1] == 10:
            ending = b"\r\n"
            next_index = index + 2
        else:
            ending = data[index : index + 1]
            next_index = index + 1
        lines.append((data[start:index], ending))
        start = next_index
        index = next_index

    if start < len(data):
        lines.append((data[start:], b""))
    return lines


def parse_bytes(data: bytes) -> Document:
    """Parse syntax observed in an `.xxp` file without normalizing bytes."""

    records: list[Record] = []
    section_counts: dict[bytes, int] = {}
    current_section: bytes | None = None
    current_occurrence: int | None = None

    for content, ending in _physical_lines(data):
        if content == b"":
            records.append(BlankRecord(content, ending))
        elif content.startswith(b"[") and content.endswith(b"]"):
            name = content[1:-1]
            occurrence = section_counts.get(name, 0)
            section_counts[name] = occurrence + 1
            current_section = name
            current_occurrence = occurrence
            records.append(SectionRecord(content, ending, name, occurrence))
        elif b"=" in content:
            key, value = content.split(b"=", 1)
            records.append(
                KeyValueRecord(
                    content,
                    ending,
                    key,
                    value,
                    current_section,
                    current_occurrence,
                )
            )
        else:
            records.append(RawRecord(content, ending))

    return Document(tuple(records))


def parse_file(path: str | Path) -> Document:
    return parse_bytes(Path(path).read_bytes())

