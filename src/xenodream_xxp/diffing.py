"""Structural comparisons that retain section and key occurrences."""

from __future__ import annotations

from typing import Any

from .document import Document, KeyValueRecord


Locator = tuple[bytes | None, int | None, bytes, int]


def _entries(document: Document) -> tuple[list[Locator], dict[Locator, bytes]]:
    order: list[Locator] = []
    values: dict[Locator, bytes] = {}
    counts: dict[tuple[bytes | None, int | None, bytes], int] = {}
    for record in document.records:
        if not isinstance(record, KeyValueRecord):
            continue
        base = (record.section, record.section_occurrence, record.key)
        occurrence = counts.get(base, 0)
        counts[base] = occurrence + 1
        locator = (*base, occurrence)
        order.append(locator)
        values[locator] = record.value
    return order, values


def _text(value: bytes | None) -> str | None:
    if value is None:
        return None
    return value.decode("ascii", errors="backslashreplace")


def _base_difference(kind: str, locator: Locator) -> dict[str, Any]:
    section, section_occurrence, key, key_occurrence = locator
    return {
        "kind": kind,
        "section": _text(section),
        "section_occurrence": section_occurrence,
        "key": _text(key),
        "key_occurrence": key_occurrence,
    }


def diff_documents(before: Document, after: Document) -> list[dict[str, Any]]:
    before_order, before_values = _entries(before)
    after_order, after_values = _entries(after)
    locators = list(before_order)
    locators.extend(locator for locator in after_order if locator not in before_values)
    differences: list[dict[str, Any]] = []

    for locator in locators:
        if locator not in before_values:
            difference = _base_difference("key_added", locator)
            difference["after"] = _text(after_values[locator])
            differences.append(difference)
            continue
        if locator not in after_values:
            difference = _base_difference("key_removed", locator)
            difference["before"] = _text(before_values[locator])
            differences.append(difference)
            continue

        before_value = before_values[locator]
        after_value = after_values[locator]
        if before_value == after_value:
            continue
        before_tokens = before_value.split()
        after_tokens = after_value.split()
        if len(before_tokens) == len(after_tokens) and len(before_tokens) > 1:
            for index, (before_token, after_token) in enumerate(
                zip(before_tokens, after_tokens, strict=True)
            ):
                if before_token == after_token:
                    continue
                difference = _base_difference("value_token_changed", locator)
                difference.update(
                    {
                        "token_index": index,
                        "before": _text(before_token),
                        "after": _text(after_token),
                    }
                )
                differences.append(difference)
        else:
            difference = _base_difference("value_changed", locator)
            difference.update(
                {"before": _text(before_value), "after": _text(after_value)}
            )
            differences.append(difference)

    if not differences and before.to_bytes() != after.to_bytes():
        differences.append(
            {
                "kind": "raw_bytes_changed",
                "before_bytes": len(before.to_bytes()),
                "after_bytes": len(after.to_bytes()),
            }
        )
    return differences

