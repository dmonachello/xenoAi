"""Recover bounded XenoDream metamorph descriptors from executable metadata."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import struct
from typing import Any


TARGET_SHA256 = "1674590ed60cea95cfeef076dfdafce4384fb86f118f087c42e23fd9429f1b6e"
OPERATION_TABLE_VA = 0x7F4390
OPERATION_COUNT = 246

NUMERIC_ATTRIBUTE_MARKER = struct.pack("<II", 0x631AE4, 0x67A0B8)
CHOICE_ATTRIBUTE_MARKER = struct.pack("<II", 0x631CF8, 0x67A15C)


@dataclass(frozen=True)
class OperationProfile:
    style: int
    name: str
    expected_descriptors: int
    end_style: int


@dataclass(frozen=True)
class NumericDescriptor:
    kind: str
    slot: int
    name: str
    minimum: float
    maximum: float
    default: float
    step: float
    decimal_places: int
    control_arg_30: int
    control_arg_34: int
    control_flag_38: int
    source_va: str
    payload_hex: str


@dataclass(frozen=True)
class ChoiceDescriptor:
    kind: str
    slot: int
    name: str
    default: int
    choices: tuple[str, ...]
    unresolved_tail_hex: str
    source_va: str
    payload_hex: str


PROFILES = (
    OperationProfile(style=1, name="Sphere", expected_descriptors=12, end_style=2),
    OperationProfile(style=5, name="Cube", expected_descriptors=9, end_style=6),
    OperationProfile(style=13, name="Cylinder", expected_descriptors=7, end_style=14),
)


class RecoveryError(ValueError):
    pass


class PeImage:
    def __init__(self, data: bytes) -> None:
        self.data = data
        if len(data) < 0x40 or data[:2] != b"MZ":
            raise RecoveryError("not a DOS/PE image")
        pe_offset = struct.unpack_from("<I", data, 0x3C)[0]
        if data[pe_offset : pe_offset + 4] != b"PE\0\0":
            raise RecoveryError("missing PE signature")
        coff = pe_offset + 4
        section_count = struct.unpack_from("<H", data, coff + 2)[0]
        optional_size = struct.unpack_from("<H", data, coff + 16)[0]
        optional = coff + 20
        if struct.unpack_from("<H", data, optional)[0] != 0x10B:
            raise RecoveryError("expected a PE32 image")
        self.image_base = struct.unpack_from("<I", data, optional + 28)[0]
        section_table = optional + optional_size
        self.sections: list[tuple[int, int, int, int]] = []
        for index in range(section_count):
            entry = section_table + index * 40
            virtual_size, virtual_address, raw_size, raw_pointer = struct.unpack_from(
                "<IIII", data, entry + 8
            )
            self.sections.append(
                (virtual_address, max(virtual_size, raw_size), raw_pointer, raw_size)
            )

    def file_offset(self, virtual_address: int) -> int:
        rva = virtual_address - self.image_base
        for section_rva, mapped_size, raw_pointer, raw_size in self.sections:
            if section_rva <= rva < section_rva + mapped_size:
                delta = rva - section_rva
                if delta >= raw_size:
                    raise RecoveryError(f"VA 0x{virtual_address:x} has no file bytes")
                return raw_pointer + delta
        raise RecoveryError(f"VA 0x{virtual_address:x} is not mapped")

    def read(self, virtual_address: int, length: int) -> bytes:
        offset = self.file_offset(virtual_address)
        result = self.data[offset : offset + length]
        if len(result) != length:
            raise RecoveryError(f"short read at VA 0x{virtual_address:x}")
        return result


def _string(payload: bytes, offset: int) -> tuple[str, int]:
    if offset + 2 > len(payload):
        raise RecoveryError("truncated descriptor string length")
    length = struct.unpack_from("<H", payload, offset)[0]
    start = offset + 2
    end = start + length
    if end > len(payload):
        raise RecoveryError("truncated descriptor string")
    try:
        return payload[start:end].decode("ascii"), end
    except UnicodeDecodeError as error:
        raise RecoveryError("descriptor string is not ASCII") from error


def _parse_numeric(payload: bytes, source_va: int) -> NumericDescriptor:
    if len(payload) < 4:
        raise RecoveryError("truncated numeric descriptor")
    slot = struct.unpack_from("<i", payload)[0]
    name, offset = _string(payload, 4)
    if len(payload) - offset != 29:
        raise RecoveryError(
            f"unexpected numeric descriptor tail for {name!r}: {len(payload) - offset} bytes"
        )
    minimum, maximum, default, step, decimal_places, arg_30, arg_34, flag_38 = struct.unpack_from(
        "<ffffiiiB", payload, offset
    )
    return NumericDescriptor(
        kind="numeric",
        slot=slot,
        name=name,
        minimum=minimum,
        maximum=maximum,
        default=default,
        step=step,
        decimal_places=decimal_places,
        control_arg_30=arg_30,
        control_arg_34=arg_34,
        control_flag_38=flag_38,
        source_va=f"0x{source_va:x}",
        payload_hex=payload.hex(),
    )


def _parse_choice(payload: bytes, source_va: int) -> ChoiceDescriptor:
    if len(payload) < 8:
        raise RecoveryError("truncated choice descriptor")
    slot = struct.unpack_from("<i", payload)[0]
    name, offset = _string(payload, 4)
    if offset + 8 > len(payload):
        raise RecoveryError(f"truncated choice count for {name!r}")
    count = struct.unpack_from("<i", payload, offset)[0]
    default = struct.unpack_from("<i", payload, offset + 4)[0]
    offset += 8
    if not 0 <= count <= 256:
        raise RecoveryError(f"invalid choice count for {name!r}: {count}")
    choices: list[str] = []
    for _ in range(count):
        choice, offset = _string(payload, offset)
        choices.append(choice)
    return ChoiceDescriptor(
        kind="choice",
        slot=slot,
        name=name,
        default=default,
        choices=tuple(choices),
        unresolved_tail_hex=payload[offset:].hex(),
        source_va=f"0x{source_va:x}",
        payload_hex=payload.hex(),
    )


def _scan_descriptors(data: bytes, start_va: int) -> list[NumericDescriptor | ChoiceDescriptor]:
    descriptors: list[NumericDescriptor | ChoiceDescriptor] = []
    for marker, parser in (
        (NUMERIC_ATTRIBUTE_MARKER, _parse_numeric),
        (CHOICE_ATTRIBUTE_MARKER, _parse_choice),
    ):
        offset = 0
        while True:
            marker_offset = data.find(marker, offset)
            if marker_offset < 0:
                break
            length_offset = marker_offset + len(marker)
            if length_offset + 2 > len(data):
                raise RecoveryError("truncated descriptor payload length")
            payload_length = struct.unpack_from("<H", data, length_offset)[0]
            payload_start = length_offset + 2
            payload_end = payload_start + payload_length
            if payload_end > len(data):
                raise RecoveryError("descriptor payload extends beyond operation metadata")
            descriptors.append(
                parser(data[payload_start:payload_end], start_va + marker_offset)
            )
            offset = payload_end
    descriptors.sort(key=lambda descriptor: descriptor.slot)
    slots = [descriptor.slot for descriptor in descriptors]
    if len(slots) != len(set(slots)):
        raise RecoveryError(f"duplicate descriptor slots: {slots}")
    return descriptors


def recover(executable: bytes) -> dict[str, Any]:
    digest = hashlib.sha256(executable).hexdigest()
    if digest != TARGET_SHA256:
        raise RecoveryError(
            f"unsupported executable SHA-256 {digest}; expected {TARGET_SHA256}"
        )
    image = PeImage(executable)
    table = image.read(OPERATION_TABLE_VA, OPERATION_COUNT * 4)
    operation_addresses = struct.unpack(f"<{OPERATION_COUNT}I", table)
    operations = []
    for profile in PROFILES:
        start = operation_addresses[profile.style]
        end = operation_addresses[profile.end_style]
        if not start < end:
            raise RecoveryError(
                f"invalid metadata range for Style {profile.style}: 0x{start:x}..0x{end:x}"
            )
        descriptors = _scan_descriptors(image.read(start, end - start), start)
        if len(descriptors) != profile.expected_descriptors:
            raise RecoveryError(
                f"Style {profile.style} expected {profile.expected_descriptors} descriptors, "
                f"found {len(descriptors)}"
            )
        if [descriptor.slot for descriptor in descriptors] != list(
            range(profile.expected_descriptors)
        ):
            raise RecoveryError(
                f"Style {profile.style} descriptor slots are not contiguous from zero"
            )
        operations.append(
            {
                "style": profile.style,
                "name": profile.name,
                "metadata_range": [f"0x{start:x}", f"0x{end:x}"],
                "descriptors": [asdict(descriptor) for descriptor in descriptors],
            }
        )
    return {
        "schema_version": 1,
        "target_sha256": digest,
        "operation_table_va": f"0x{OPERATION_TABLE_VA:x}",
        "operation_count": OPERATION_COUNT,
        "operations": operations,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("executable", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        report = recover(args.executable.read_bytes())
    except (OSError, RecoveryError) as error:
        parser.error(str(error))
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(rendered, end="")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
