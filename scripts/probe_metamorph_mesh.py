"""Prepare and summarize isolated XenoDream metamorph mesh probes."""

from __future__ import annotations

import argparse
from dataclasses import replace
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
from pathlib import Path
import re
import sys
from typing import Any

from xenodream_xxp.diffing import diff_documents
from xenodream_xxp.document import Document, KeyValueRecord, parse_bytes
from xenodream_xxp.metamorph import load_metamorph_registry


class ProbeError(ValueError):
    pass


def _hash(data: bytes) -> str:
    return sha256(data).hexdigest()


def _records(
    document: Document, section: bytes, key: bytes
) -> list[tuple[int, KeyValueRecord]]:
    return [
        (index, record)
        for index, record in enumerate(document.records)
        if isinstance(record, KeyValueRecord)
        and record.section == section
        and record.section_occurrence == 0
        and record.key == key
    ]


def _one_value(document: Document, section: bytes, key: bytes) -> bytes:
    matches = _records(document, section, key)
    if len(matches) != 1:
        raise ProbeError(
            f"expected one {section.decode()}.{key.decode()} record, found {len(matches)}"
        )
    return matches[0][1].value


def _operation(document: Document, holon: int) -> tuple[bytes, dict[str, Any]]:
    section = f"Holon\\{holon}\\MM\\0".encode("ascii")
    style = _one_value(document, section, b"Style").decode("ascii")
    count_text = _one_value(document, section, b"NumPars").decode("ascii")
    header_version = _one_value(document, b"Header", b"Progversion").decode("ascii")
    try:
        count = int(count_text)
    except ValueError as error:
        raise ProbeError(f"invalid NumPars value {count_text!r}") from error
    registry = load_metamorph_registry()
    definition = next(
        (item for item in registry["operations"] if str(item["style"]) == style),
        None,
    )
    if definition is None:
        raise ProbeError(f"Style {style} is not in the packaged registry")
    if (
        header_version not in definition.get("format_versions", [])
        or count not in definition.get("verified_num_pars", [])
    ):
        raise ProbeError(
            f"Style {style} does not match a verified {header_version} schema"
        )
    tokens = _one_value(document, section, b"Pars").split()
    if len(tokens) != count:
        raise ProbeError(f"NumPars declares {count}, but Pars contains {len(tokens)} tokens")
    return section, definition


def _numeric_value(raw: str, descriptor: dict[str, Any], source_token: bytes) -> bytes:
    try:
        value = Decimal(raw)
    except InvalidOperation as error:
        raise ProbeError(f"{raw!r} is not a decimal value") from error
    if not value.is_finite():
        raise ProbeError("probe values must be finite")
    minimum = Decimal(descriptor["minimum"])
    maximum = Decimal(descriptor["maximum"])
    if not minimum <= value <= maximum:
        raise ProbeError(f"value {value} is outside native range {minimum}..{maximum}")
    places = int(descriptor["decimal_places"])
    quantum = Decimal(1).scaleb(-places)
    if value.quantize(quantum) != value:
        raise ProbeError(f"value {value} exceeds native {places}-place precision")
    match = re.fullmatch(rb"[+-]?\d+(?:\.(\d*))?", source_token)
    if match is None:
        raise ProbeError(f"source token {source_token!r} is not fixed-point decimal")
    persisted_places = len(match.group(1) or b"")
    return format(value, f".{persisted_places}f").encode("ascii")


def _choice_value(raw: str, descriptor: dict[str, Any]) -> bytes:
    choices = list(descriptor["choices"])
    if raw in choices:
        return str(choices.index(raw)).encode("ascii")
    try:
        index = int(raw)
    except ValueError as error:
        raise ProbeError(f"choice must be one of {choices!r} or its integer index") from error
    if not 0 <= index < len(choices):
        raise ProbeError(f"choice index {index} is outside 0..{len(choices) - 1}")
    return str(index).encode("ascii")


def _replace_token(
    document: Document,
    section: bytes,
    token_index: int,
    replacement: bytes,
) -> Document:
    matches = _records(document, section, b"Pars")
    if len(matches) != 1:
        raise ProbeError(f"expected one {section.decode()}.Pars record")
    record_index, record = matches[0]
    tokens = list(re.finditer(rb"\S+", record.value))
    if token_index >= len(tokens):
        raise ProbeError(f"Pars token {token_index} is missing")
    token = tokens[token_index]
    value = record.value[: token.start()] + replacement + record.value[token.end() :]
    separator = record.content.find(b"=")
    if separator < 0:
        raise ProbeError("Pars record lost its separator")
    updated = replace(
        record,
        content=record.content[: separator + 1] + value,
        value=value,
    )
    records = list(document.records)
    records[record_index] = updated
    return Document(tuple(records))


def build_variant(
    source: bytes, holon: int, parameter: str, raw_value: str
) -> tuple[bytes, dict[str, Any]]:
    document = parse_bytes(source)
    section, operation = _operation(document, holon)
    descriptor = next(
        (
            item
            for item in operation.get("token_bindings", [])
            if item["name"].casefold() == parameter.casefold()
        ),
        None,
    )
    if descriptor is None:
        raise ProbeError(f"{operation['name']} has no recovered parameter {parameter!r}")
    token_index = int(descriptor["token_index"])
    source_token = _one_value(document, section, b"Pars").split()[token_index]
    if descriptor["kind"] == "numeric":
        replacement = _numeric_value(raw_value, descriptor, source_token)
    elif descriptor["kind"] == "choice":
        replacement = _choice_value(raw_value, descriptor)
    else:
        raise ProbeError(f"unsupported descriptor kind {descriptor['kind']!r}")
    variant = _replace_token(document, section, token_index, replacement)
    differences = diff_documents(document, variant)
    if replacement == source_token:
        if differences:
            raise ProbeError("baseline replacement changed unrelated bytes")
    elif differences != [
        {
            "kind": "value_token_changed",
            "section": section.decode("ascii"),
            "section_occurrence": 0,
            "key": "Pars",
            "key_occurrence": 0,
            "token_index": token_index,
            "before": source_token.decode("ascii"),
            "after": replacement.decode("ascii"),
        }
    ]:
        raise ProbeError(f"variant changed unexpected fields: {differences!r}")
    output = variant.to_bytes()
    if parse_bytes(output).to_bytes() != output:
        raise ProbeError("variant failed exact parser round trip")
    return output, {
        "requested": raw_value,
        "persisted": replacement.decode("ascii"),
        "source_token": source_token.decode("ascii"),
        "diff": differences,
    }


def prepare_probe(
    source_path: Path,
    output_directory: Path,
    holon: int,
    parameter: str,
    values: list[str],
) -> dict[str, Any]:
    if output_directory.exists():
        raise ProbeError(f"output directory already exists: {output_directory}")
    if not values:
        raise ProbeError("at least one probe value is required")
    source = source_path.read_bytes()
    document = parse_bytes(source)
    section, operation = _operation(document, holon)
    descriptor = next(
        (
            item
            for item in operation["token_bindings"]
            if item["name"].casefold() == parameter.casefold()
        ),
        None,
    )
    if descriptor is None:
        raise ProbeError(f"{operation['name']} has no recovered parameter {parameter!r}")
    prepared = []
    for index, value in enumerate(values):
        data, facts = build_variant(source, holon, parameter, value)
        prepared.append(
            {
                "index": index,
                "file": f"variant-{index:03d}.xxp",
                "sha256": _hash(data),
                **facts,
                "data": data,
            }
        )
    output_directory.mkdir(parents=True)
    variants = []
    for item in prepared:
        data = item.pop("data")
        (output_directory / item["file"]).write_bytes(data)
        variants.append(item)
    manifest = {
        "schema": "xenosculpt-metamorph-probe/v1",
        "source": {
            "path": str(source_path.resolve()),
            "sha256": _hash(source),
            "bytes": len(source),
        },
        "metamorph": {
            "section": section.decode("ascii"),
            "holon": holon,
            "style": operation["style"],
            "operation": operation["name"],
            "parameter": descriptor,
        },
        "variants": variants,
        "claims": {
            "native_acceptance": False,
            "geometric_effect": False,
            "printable": False,
        },
    }
    (output_directory / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def summarize_probe(manifest_path: Path, report_paths: list[Path]) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != "xenosculpt-metamorph-probe/v1":
        raise ProbeError("unsupported probe manifest")
    variants = {item["sha256"]: item for item in manifest["variants"]}
    runs = []
    for path in report_paths:
        report = json.loads(path.read_text(encoding="utf-8"))
        digest = report.get("input", {}).get("source_sha256_before")
        if digest not in variants:
            raise ProbeError(f"report {path} does not match a manifest variant")
        stl = report.get("stl")
        accepted = report.get("outcome") == "succeeded" and stl is not None
        runs.append(
            {
                "variant": variants[digest],
                "report": str(path.resolve()),
                "outcome": report.get("outcome"),
                "accepted": accepted,
                "stl": stl,
            }
        )
    reported = {run["variant"]["sha256"] for run in runs}
    missing = [digest for digest in variants if digest not in reported]
    if missing:
        raise ProbeError(f"missing reports for variant hashes: {missing!r}")
    runs.sort(key=lambda item: (item["variant"]["index"], item["report"]))
    baseline_runs = [run for run in runs if run["variant"]["index"] == 0]
    accepted_baselines = [run["stl"] for run in baseline_runs if run["accepted"]]
    baseline = accepted_baselines[0] if accepted_baselines else None
    baseline_variation = None
    if accepted_baselines:
        baseline_variation = {
            "triangle_count_span": max(
                item["triangle_count"] for item in accepted_baselines
            )
            - min(item["triangle_count"] for item in accepted_baselines),
            "absolute_volume_span": max(
                abs(item["signed_volume"]) for item in accepted_baselines
            )
            - min(abs(item["signed_volume"]) for item in accepted_baselines),
            "dimension_spans": [
                max(item["dimensions"][axis] for item in accepted_baselines)
                - min(item["dimensions"][axis] for item in accepted_baselines)
                for axis in range(3)
            ],
            "replicates": len(accepted_baselines),
        }
    for run in runs:
        stl = run["stl"]
        if baseline is None or stl is None:
            run["delta_from_baseline"] = None
            continue
        run["delta_from_baseline"] = {
            "triangle_count": stl["triangle_count"] - baseline["triangle_count"],
            "dimensions": [
                stl["dimensions"][axis] - baseline["dimensions"][axis]
                for axis in range(3)
            ],
            "absolute_volume": abs(stl["signed_volume"])
            - abs(baseline["signed_volume"]),
            "connected_components": stl["connected_components"]
            - baseline["connected_components"],
            "boundary_edges": stl["boundary_edges"] - baseline["boundary_edges"],
            "non_manifold_edges": stl["non_manifold_edges"]
            - baseline["non_manifold_edges"],
        }
        delta = run["delta_from_baseline"]
        run["exceeds_observed_baseline_variation"] = (
            baseline_variation is not None
            and (
                abs(delta["triangle_count"])
                > baseline_variation["triangle_count_span"]
                or abs(delta["absolute_volume"])
                > baseline_variation["absolute_volume_span"]
                or any(
                    abs(delta["dimensions"][axis])
                    > baseline_variation["dimension_spans"][axis]
                    for axis in range(3)
                )
            )
        )
    accepted_all = all(run["accepted"] for run in runs)
    topology_valid_all = accepted_all and all(
        run["stl"]["degenerate_triangles"] == 0
        and run["stl"]["boundary_edges"] == 0
        and run["stl"]["non_manifold_edges"] == 0
        and run["stl"]["inconsistent_winding_edges"] == 0
        and run["stl"]["connected_components"] == 1
        and run["stl"]["signed_volume"] != 0
        for run in runs
    )
    changed = any(
        run["delta_from_baseline"] is not None
        and any(
            value != 0
            for key, value in run["delta_from_baseline"].items()
            for value in (value if isinstance(value, list) else [value])
        )
        for run in runs
        if run["variant"]["index"] != 0
    )
    return {
        "schema": "xenosculpt-metamorph-probe-summary/v1",
        "manifest": str(manifest_path.resolve()),
        "operation": manifest["metamorph"]["operation"],
        "parameter": manifest["metamorph"]["parameter"]["name"],
        "all_native_exports_succeeded": accepted_all,
        "all_basic_topology_valid": topology_valid_all,
        "measured_mesh_change": changed,
        "baseline_variation": baseline_variation,
        "any_change_exceeds_observed_baseline_variation": any(
            run.get("exceeds_observed_baseline_variation", False)
            for run in runs
            if run["variant"]["index"] != 0
        ),
        "printable": False,
        "runs": runs,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare")
    prepare.add_argument("source", type=Path)
    prepare.add_argument("output_directory", type=Path)
    prepare.add_argument("--holon", type=int, required=True)
    prepare.add_argument("--parameter", required=True)
    prepare.add_argument("--value", action="append", required=True)
    summarize = commands.add_parser("summarize")
    summarize.add_argument("manifest", type=Path)
    summarize.add_argument("--report", type=Path, action="append", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare_probe(
                args.source,
                args.output_directory,
                args.holon,
                args.parameter,
                args.value,
            )
        else:
            result = summarize_probe(args.manifest, args.report)
    except (OSError, ProbeError) as error:
        print(str(error), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
