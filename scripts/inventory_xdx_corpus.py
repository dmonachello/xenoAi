"""Inventory XenoDream projects and metamorph presets without interpreting them."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
import re
import sys
from typing import Any


ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "src"))

from xenodream_xxp.document import KeyValueRecord, parse_bytes  # noqa: E402


HOLON = re.compile(rb"Holon\\(\d+)$")
METAMORPH = re.compile(rb"Holon\\(\d+)\\MM\\(\d+)$")


def _text(value: bytes | None) -> str | None:
    if value is None:
        return None
    return value.decode("latin-1")


def _fields(data: bytes) -> dict[bytes, dict[bytes, bytes]]:
    result: dict[bytes, dict[bytes, bytes]] = defaultdict(dict)
    for record in parse_bytes(data).records:
        if isinstance(record, KeyValueRecord) and record.section is not None:
            result[record.section][record.key] = record.value
    return result


def inspect_project(path: Path, corpus: Path) -> dict[str, Any]:
    data = path.read_bytes()
    document = parse_bytes(data)
    fields = _fields(data)
    holons: list[dict[str, Any]] = []
    metamorphs: list[dict[str, Any]] = []

    for section, values in fields.items():
        holon_match = HOLON.fullmatch(section)
        if holon_match:
            holons.append(
                {
                    "section_index": int(holon_match.group(1)),
                    "id": _text(values.get(b"ID")),
                    "group_id": _text(values.get(b"GroupID")),
                    "type": _text(values.get(b"Type")),
                    "name": _text(values.get(b"Name")),
                }
            )
            continue

        metamorph_match = METAMORPH.fullmatch(section)
        if metamorph_match:
            pars = values.get(b"Pars", b"").split()
            num_pars_raw = values.get(b"NumPars")
            try:
                num_pars = int(num_pars_raw) if num_pars_raw is not None else None
            except ValueError:
                num_pars = None
            metamorphs.append(
                {
                    "holon_section_index": int(metamorph_match.group(1)),
                    "metamorph_index": int(metamorph_match.group(2)),
                    "style": _text(values.get(b"Style")),
                    "num_pars": num_pars,
                    "pars_token_count": len(pars),
                    "num_pars_matches": num_pars == len(pars),
                }
            )

    holons.sort(key=lambda item: item["section_index"])
    metamorphs.sort(
        key=lambda item: (item["holon_section_index"], item["metamorph_index"])
    )
    header = fields.get(b"Header", {})
    try:
        declared_holons = int(header.get(b"NumHolons", b""))
    except ValueError:
        declared_holons = None

    return {
        "path": path.relative_to(corpus).as_posix(),
        "bytes": len(data),
        "sha256": sha256(data).hexdigest(),
        "program": _text(header.get(b"Program")),
        "version": _text(header.get(b"Progversion")),
        "declared_holons": declared_holons,
        "actual_holons": len(holons),
        "num_holons_matches": declared_holons == len(holons),
        "byte_identical_roundtrip": document.to_bytes() == data,
        "holons": holons,
        "metamorphs": metamorphs,
    }


def inspect_presets(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    section: str | None = None
    sections: dict[str, list[dict[str, Any]]] = defaultdict(list)
    malformed_rows = 0
    for raw_line in data.splitlines():
        line = raw_line.decode("latin-1")
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1]
        elif section is not None and "=" in line:
            name, payload = line.split("=", 1)
            tokens = payload.split()
            try:
                declared = int(tokens[0])
            except (IndexError, ValueError):
                declared = None
            matches = declared == len(tokens) - 1
            malformed_rows += not matches
            sections[section].append(
                {
                    "name": name,
                    "declared_payload_tokens": declared,
                    "payload_token_count": max(0, len(tokens) - 1),
                    "count_matches": matches,
                }
            )

    return {
        "file": path.name,
        "bytes": len(data),
        "sha256": sha256(data).hexdigest(),
        "section_count": len(sections),
        "row_count": sum(len(rows) for rows in sections.values()),
        "rows_with_count_mismatch": malformed_rows,
        "sections": [
            {"name": name, "rows": rows} for name, rows in sorted(sections.items())
        ],
    }


def build_inventory(corpus: Path, presets: Path) -> dict[str, Any]:
    projects = [inspect_project(path, corpus) for path in sorted(corpus.rglob("*.xxp"))]
    versions: Counter[str] = Counter()
    holon_types: Counter[str] = Counter()
    metamorph_indexes: Counter[str] = Counter()
    style_num_pars: Counter[tuple[str, str, str]] = Counter()
    name_style: Counter[tuple[str, str]] = Counter()

    for project in projects:
        versions[project["version"] or "<missing>"] += 1
        holon_by_index = {h["section_index"]: h for h in project["holons"]}
        for holon in project["holons"]:
            holon_types[holon["type"] or "<missing>"] += 1
        for metamorph in project["metamorphs"]:
            metamorph_indexes[str(metamorph["metamorph_index"])] += 1
            style = metamorph["style"] or "<missing>"
            num_pars = str(metamorph["num_pars"])
            version = project["version"] or "<missing>"
            style_num_pars[(version, style, num_pars)] += 1
            if metamorph["metamorph_index"] == 0:
                holon = holon_by_index.get(metamorph["holon_section_index"])
                if holon and holon["type"] == "1" and holon["name"]:
                    name_style[(holon["name"], style)] += 1

    return {
        "schema": "xenodream-corpus-inventory/v1",
        "semantic_policy": (
            "Counts and correlations are observations. Names, styles, and physical-geometry "
            "suitability remain candidates until cross-validated against binary or runtime evidence."
        ),
        "corpus": {
            "source": corpus.name,
            "project_count": len(projects),
            "all_roundtrip_exact": all(p["byte_identical_roundtrip"] for p in projects),
            "all_num_holons_match": all(p["num_holons_matches"] for p in projects),
            "all_num_pars_match": all(
                mm["num_pars_matches"] for p in projects for mm in p["metamorphs"]
            ),
            "versions": dict(sorted(versions.items())),
            "holon_types": dict(sorted(holon_types.items())),
            "metamorph_indexes": dict(sorted(metamorph_indexes.items())),
            "style_num_pars_by_version": [
                {"version": key[0], "style": key[1], "num_pars": key[2], "count": count}
                for key, count in sorted(style_num_pars.items())
            ],
            "type1_mm0_name_style_candidates": [
                {"name": key[0], "style": key[1], "count": count}
                for key, count in sorted(name_style.items())
            ],
            "projects": projects,
        },
        "presets": inspect_presets(presets),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--presets", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args(argv)

    inventory = build_inventory(args.corpus.resolve(), args.presets.resolve())
    output = args.output_json.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(inventory, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "projects": inventory["corpus"]["project_count"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
