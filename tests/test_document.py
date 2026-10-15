from __future__ import annotations

from pathlib import Path

import pytest

from xenodream_xxp.document import (
    BlankRecord,
    KeyValueRecord,
    RawRecord,
    SectionRecord,
    parse_bytes,
)


SAMPLE = (
    Path(__file__).parents[1]
    / "samples"
    / "originals"
    / "20061109Sirps08.xxp"
)


@pytest.mark.parametrize(
    "source",
    [
        b"[A]\r\nKey=value\r\n",
        b"[A]\nKey=value\n",
        b"[A]\rKey=value\r",
        b"[A]\r\nKey=value",
        b"",
    ],
)
def test_unchanged_document_serializes_to_identical_bytes(source: bytes) -> None:
    assert parse_bytes(source).to_bytes() == source


def test_preserves_unknown_repeated_empty_and_long_values() -> None:
    long_value = b"x" * 10_000
    source = (
        b"[Unknown Section]\r\n"
        b"Unknown=first\r\n"
        b"Unknown=second\r\n"
        b"Empty=\r\n"
        b"Long=" + long_value + b"\r\n"
    )

    document = parse_bytes(source)

    assert document.to_bytes() == source
    values = [
        record.value
        for record in document.records
        if isinstance(record, KeyValueRecord) and record.key == b"Unknown"
    ]
    assert values == [b"first", b"second"]
    assert document.sections[0].name == b"Unknown Section"


def test_classifies_records_without_discarding_unrecognized_lines() -> None:
    source = b"preamble\r\n\r\n[Section]\r\nKey=a=b\r\n"
    document = parse_bytes(source)

    assert [type(record) for record in document.records] == [
        RawRecord,
        BlankRecord,
        SectionRecord,
        KeyValueRecord,
    ]
    key_value = document.records[-1]
    assert isinstance(key_value, KeyValueRecord)
    assert key_value.key == b"Key"
    assert key_value.value == b"a=b"


@pytest.mark.parametrize(
    "malformed",
    [
        b"[missing-close",
        b"missing-open]",
        b"arbitrary text without a separator",
    ],
)
def test_preserves_malformed_records_inside_a_document(malformed: bytes) -> None:
    source = b"[Valid]\r\nBefore=1\r\n" + malformed + b"\r\nAfter=2\r\n"

    document = parse_bytes(source)

    assert document.to_bytes() == source
    assert isinstance(document.records[2], RawRecord)
    assert document.records[2].content == malformed


def test_reference_sample_roundtrips_byte_for_byte() -> None:
    source = SAMPLE.read_bytes()

    document = parse_bytes(source)

    assert document.to_bytes() == source
    assert len(document.records) == 1001
    assert len(document.sections) == 38
    assert max(len(record.content) for record in document.records) == 3018
