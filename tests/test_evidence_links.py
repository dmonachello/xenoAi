from __future__ import annotations

import csv
import json
from pathlib import Path
import re


ROOT = Path(__file__).parents[1]
EVIDENCE_ID = re.compile(r"ev_[0-9a-f]{64}")


def _retained_evidence() -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for path in (ROOT / "evidence" / "rea").glob("*.json"):
        bundle = json.loads(path.read_text(encoding="utf-8"))
        result.update({record["evidence_id"]: record for record in bundle["records"]})
    return result


def _procedure_address(record: dict[str, object]) -> str | None:
    normalized = record.get("normalized_result")
    if isinstance(normalized, dict):
        procedure = normalized.get("procedure")
        if not isinstance(procedure, dict):
            value = normalized.get("value")
            if isinstance(value, dict):
                procedure = value.get("procedure")
        if isinstance(procedure, dict):
            address = procedure.get("address")
            if isinstance(address, str):
                return address
    parameters = record.get("parameters")
    if isinstance(parameters, dict):
        requested = parameters.get("procedure")
        return requested if isinstance(requested, str) else None
    return None


def test_all_recorded_rea_evidence_ids_are_retained() -> None:
    retained = _retained_evidence()
    knowledge = json.loads((ROOT / "spec" / "xdx-knowledge.json").read_text())
    json_ids = {
        evidence["evidence_id"]
        for claim in knowledge["claims"]
        for evidence in claim["binary_evidence"]
        if "evidence_id" in evidence
    }
    with (ROOT / "docs" / "rea-cross-validation.tsv").open(
        encoding="utf-8", newline=""
    ) as stream:
        tsv_ids = {
            evidence_id
            for row in csv.DictReader(stream, delimiter="\t")
            for evidence_id in EVIDENCE_ID.findall(row["binary_evidence"])
        }

    assert json_ids <= retained.keys()
    assert tsv_ids <= retained.keys()

    function_evidence = [
        evidence
        for claim in knowledge["claims"]
        for evidence in claim["binary_evidence"]
        if "function" in evidence and "evidence_id" in evidence
    ]
    assert {
        (evidence["function"], _procedure_address(retained[evidence["evidence_id"]]))
        for evidence in function_evidence
    } == {(evidence["function"], evidence["function"]) for evidence in function_evidence}


def test_checked_in_inventory_contains_no_absolute_local_paths() -> None:
    inventory = (ROOT / "evidence" / "corpus" / "xdx-corpus-inventory.json").read_text()

    assert "C:\\\\Users\\\\" not in inventory
    assert "C:\\\\Program Files" not in inventory
