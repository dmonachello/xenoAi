from __future__ import annotations

import importlib.util
from pathlib import Path
import struct
import sys

import pytest


ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location(
    "recover_metamorph_descriptors",
    ROOT / "scripts" / "recover_metamorph_descriptors.py",
)
assert SPEC is not None and SPEC.loader is not None
recovery = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = recovery
SPEC.loader.exec_module(recovery)


def _text(value: str) -> bytes:
    encoded = value.encode("ascii")
    return struct.pack("<H", len(encoded)) + encoded


def _attribute(marker: bytes, payload: bytes) -> bytes:
    return marker + struct.pack("<H", len(payload)) + payload


def test_scan_recovers_numeric_slot_and_bounds() -> None:
    payload = b"".join(
        (
            struct.pack("<i", 0),
            _text("Face Warp"),
            struct.pack("<ffffiiiB", -100.0, 100.0, 0.0, 0.01, 2, 7, 200, 0),
        )
    )

    descriptors = recovery._scan_descriptors(
        b"prefix" + _attribute(recovery.NUMERIC_ATTRIBUTE_MARKER, payload),
        0x500000,
    )

    assert len(descriptors) == 1
    descriptor = descriptors[0]
    assert descriptor.kind == "numeric"
    assert descriptor.slot == 0
    assert descriptor.name == "Face Warp"
    assert descriptor.minimum == pytest.approx(-100.0)
    assert descriptor.maximum == pytest.approx(100.0)
    assert descriptor.default == pytest.approx(0.0)
    assert descriptor.step == pytest.approx(0.01)
    assert descriptor.decimal_places == 2
    assert descriptor.source_va == "0x500006"


def test_scan_recovers_choice_slot_default_and_values() -> None:
    choices = ("Pyramid", "Pyramid 45", "Cone", "Bullet")
    payload = b"".join(
        (
            struct.pack("<i", 1),
            _text("Face Shape"),
            struct.pack("<ii", len(choices), 0),
            *(_text(choice) for choice in choices),
            bytes(28),
        )
    )

    descriptors = recovery._scan_descriptors(
        _attribute(recovery.CHOICE_ATTRIBUTE_MARKER, payload),
        0x600000,
    )

    assert len(descriptors) == 1
    descriptor = descriptors[0]
    assert descriptor.kind == "choice"
    assert descriptor.slot == 1
    assert descriptor.name == "Face Shape"
    assert descriptor.default == 0
    assert descriptor.choices == choices
    assert descriptor.unresolved_tail_hex == bytes(28).hex()


def test_scan_rejects_duplicate_slots() -> None:
    numeric = b"".join(
        (
            struct.pack("<i", 0),
            _text("A"),
            struct.pack("<ffffiiiB", -1.0, 1.0, 0.0, 0.1, 1, 1, 1, 0),
        )
    )
    duplicate = b"".join(
        (
            struct.pack("<i", 0),
            _text("B"),
            struct.pack("<ffffiiiB", -1.0, 1.0, 0.0, 0.1, 1, 1, 1, 0),
        )
    )

    with pytest.raises(recovery.RecoveryError, match="duplicate descriptor slots"):
        recovery._scan_descriptors(
            _attribute(recovery.NUMERIC_ATTRIBUTE_MARKER, numeric)
            + _attribute(recovery.NUMERIC_ATTRIBUTE_MARKER, duplicate),
            0x700000,
        )


def test_recover_rejects_unrecognized_executable() -> None:
    with pytest.raises(recovery.RecoveryError, match="unsupported executable SHA-256"):
        recovery.recover(b"not XenoDream")
