"""Build and natively evaluate closed, research-only XenoDream constructors."""

from __future__ import annotations

import argparse
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from recover_metamorph_descriptors import recover
from xenodream_xxp.document import Document, KeyValueRecord, parse_bytes
from xenodream_xxp.errors import WorkspaceError
from xenodream_xxp.generator import compile_sphere
from xenodream_xxp.validation import ValidationProfileName
from xenodream_xxp.workspace import ProjectWorkspace


CONSTRUCTORS = {
    "RoundCube": 6,
    "Pipe": 11,
    "Torus": 42,
    "Cog": 62,
    "SpiralShell": 65,
}


def _replace_value(
    document: Document, section: bytes, key: bytes, expected: bytes, value: bytes
) -> Document:
    matches = [
        (index, record)
        for index, record in enumerate(document.records)
        if isinstance(record, KeyValueRecord)
        and record.section == section
        and record.section_occurrence == 0
        and record.key == key
    ]
    if len(matches) != 1 or matches[0][1].value != expected:
        raise ValueError(f"unexpected scaffold value for {section!r}.{key!r}")
    index, record = matches[0]
    separator = record.content.find(b"=")
    updated = replace(
        record,
        content=record.content[: separator + 1] + value,
        value=value,
    )
    records = list(document.records)
    records[index] = updated
    return Document(tuple(records))


def _default_token(descriptor: dict[str, Any]) -> str:
    if descriptor["kind"] == "choice":
        return str(int(descriptor["default"]))
    places = int(descriptor["decimal_places"])
    return f"{float(descriptor['default']):.{places}f}"


def build_candidate(constructor: str, report: dict[str, Any]) -> bytes:
    """Derive one research candidate from the normalized Sphere scaffold."""

    if constructor not in CONSTRUCTORS:
        raise ValueError(f"unsupported constructor probe: {constructor}")
    operation = next(
        (
            item
            for item in report["operations"]
            if item["style"] == CONSTRUCTORS[constructor]
            and item["name"] == constructor
        ),
        None,
    )
    if operation is None:
        raise ValueError(f"descriptor report is missing {constructor}")
    descriptors = operation["descriptors"]
    if [item["slot"] for item in descriptors] != list(range(len(descriptors))):
        raise ValueError(f"{constructor} descriptor slots are not contiguous")
    pars = (" ".join(_default_token(item) for item in descriptors) + " ").encode(
        "ascii"
    )

    document = parse_bytes(compile_sphere())
    section = b"Holon\\1"
    metamorph = b"Holon\\1\\MM\\0"
    for target, key, expected, value in (
        (section, b"Name", b"Sphere2", f"{constructor}2".encode("ascii")),
        (metamorph, b"Style", b"1", str(CONSTRUCTORS[constructor]).encode("ascii")),
        (metamorph, b"NumPars", b"12", str(len(descriptors)).encode("ascii")),
        (
            metamorph,
            b"Pars",
            b"0.00000 0 0.0000 0.00000 0.00000 0.00000 0.00000 0.0000 "
            b"0.0000 0.000 0 0 ",
            pars,
        ),
    ):
        document = _replace_value(document, target, key, expected, value)
    data = document.to_bytes()
    if parse_bytes(data).to_bytes() != data:
        raise ValueError("candidate failed exact parser round trip")
    return data


def corpus_anchors(root: Path, style: int) -> list[dict[str, object]]:
    """Return bounded historical files containing the exact style token."""

    anchors: list[dict[str, object]] = []
    for path in sorted(root.rglob("*.xxp")):
        try:
            data = path.read_bytes()
            document = parse_bytes(data)
        except (OSError, ValueError):
            continue
        if not any(
            isinstance(record, KeyValueRecord)
            and b"\\MM\\" in record.section
            and record.key == b"Style"
            and record.value == str(style).encode("ascii")
            for record in document.records
        ):
            continue
        anchors.append(
            {
                "path": str(path),
                "sha256": sha256(data).hexdigest(),
            }
        )
        if len(anchors) == 10:
            break
    return anchors


def _manifest(
    constructor: str,
    candidate: bytes,
    descriptors: dict[str, Any],
    anchors: list[dict[str, object]],
    validation: object | None,
    error: str | None,
) -> dict[str, object]:
    if validation is None:
        disposition = "INCONCLUSIVE"
        validation_payload = None
    else:
        outcome = str(getattr(validation, "outcome"))
        verified = (
            bool(getattr(validation, "native_model_valid"))
            and bool(getattr(validation, "evaluates_to_3d"))
            and bool(getattr(validation, "basic_mesh_valid"))
        )
        if outcome == "succeeded":
            disposition = "VERIFIED" if verified else "NOT_VERIFIED"
        else:
            disposition = "INCONCLUSIVE"
        report = getattr(validation, "report")
        validation_payload = {
            "id": getattr(validation, "id"),
            "outcome": outcome,
            "native_model_valid": getattr(validation, "native_model_valid"),
            "evaluates_to_3d": getattr(validation, "evaluates_to_3d"),
            "basic_mesh_valid": getattr(validation, "basic_mesh_valid"),
            "fabrication_suitable": getattr(validation, "fabrication_suitable"),
            "mesh_sha256": getattr(validation, "mesh_sha256"),
            "cleanup_confirmed": report.get("cleanup_confirmed"),
            "error": report.get("error"),
            "stl": report.get("stl"),
        }
    return {
        "schema": "xenosculpt-xenodream-constructor-probe/v1",
        "constructor": constructor,
        "style": CONSTRUCTORS[constructor],
        "candidate_sha256": sha256(candidate).hexdigest(),
        "descriptor_metadata": descriptors,
        "historical_anchors": anchors,
        "disposition": disposition,
        "validation": validation_payload,
        "error": error,
        "writer_authorized": False,
        "registry_promoted": False,
        "fabrication_suitable": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--constructor", choices=tuple(CONSTRUCTORS), required=True)
    parser.add_argument("--corpus-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--executable",
        type=Path,
        default=Path(
            r"C:\Program Files (x86)\XenoDream Software\XenoDreamX\XenoDreamX.exe"
        ),
    )
    args = parser.parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        parser.error("output directory must not exist or must be empty")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    report = recover(args.executable.read_bytes())
    operation = next(
        item for item in report["operations"] if item["name"] == args.constructor
    )
    candidate = build_candidate(args.constructor, report)
    candidate_path = args.output_dir / f"{args.constructor}.xxp"
    candidate_path.write_bytes(candidate)
    workspace_path = args.output_dir / "project.xsp"
    validation = None
    error = None
    try:
        workspace = ProjectWorkspace.create(workspace_path, candidate_path)
        validation = workspace.validate_profile(
            ValidationProfileName.PREVIEW,
            stl_max_dimension_mm=120,
            executable=args.executable,
        )
    except (OSError, ValueError, WorkspaceError) as caught:
        error = f"{type(caught).__name__}: {caught}"
    manifest = _manifest(
        args.constructor,
        candidate,
        operation,
        corpus_anchors(args.corpus_root, CONSTRUCTORS[args.constructor]),
        validation,
        error,
    )
    manifest_path = args.output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0 if manifest["disposition"] == "VERIFIED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
