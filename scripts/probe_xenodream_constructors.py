"""Build and natively evaluate closed, research-only XenoDream constructors."""

from __future__ import annotations

import argparse
from dataclasses import replace
from decimal import Decimal, InvalidOperation
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

_ANCHOR_SHA256_BY_STYLE = {
    6: frozenset(
        {
            "efff50e65bfc0361d8d689088b7b4db0289c47fd0a44883ad1bb02cfc4dce948",
            "f69f0cfc004b4784289dafbc2ff5106050e084df93592f8e72ffa71e87c7a070",
            "9d2b83725113ec63684fec7adcc868217656b455f05d8c035d4d5f1a5681b704",
        }
    ),
    11: frozenset(
        {
            "9821f8693729d8129d7aef3043afd29e776787c4efe4e540cdde8b1690bcb4f7",
            "5374bb71c794840b5442decd4b12d88c7f40615fc69831fd7e2412abf8f24f60",
            "5fa9c06d9f138702703aa7c6c2a5afdde929208717156fe1859b08c74b1bd065",
            "efff50e65bfc0361d8d689088b7b4db0289c47fd0a44883ad1bb02cfc4dce948",
            "da97ffef21ed689c821cbb0ce67975169ce46c312464f8cb7940e3bdc6275920",
            "9d2b83725113ec63684fec7adcc868217656b455f05d8c035d4d5f1a5681b704",
            "18fa57706f5a2154bb39ba072a86aaf793ed3f315055914e7e9e52ad96a4f5c4",
            "374de4271a6b61d65b8382c350f8bd4f48defeaffd9ca4a76dce3d0c50bd5eff",
            "688bcef8b1c54ecc9a58dcaed71ba566fc76b07b0dc31d9061c71c21a367b9ce",
            "120dde250cdec5b0cd2ddf6ec546f1c40638d1cae58e63129c636343ab64ccdc",
        }
    ),
    42: frozenset(
        {
            "999c6eaa789fbe9d00f236e5e35c5a74986463ebdd748cc5069cf2fc378cd18a",
            "64a69d7a645ad89515ad6cdc02b68aa697ed512a8fb3230d3909cc02609db2e0",
            "2da86735b56485aa09414f67bab2cdfcf721d4b6b8d06c52e0e41fb8d9bcd2d8",
            "5fa9c06d9f138702703aa7c6c2a5afdde929208717156fe1859b08c74b1bd065",
            "d3498070477e2164fa6e41dad28b6a502b9bed6658bc54997e4bd5dcc02c740f",
            "b7a0cc50963bfef23832f2161c1d1538df58d5206744e61be8b609dd5cbe3ce0",
            "be8f2c315bf3c215ef6e402190cef4250af9e79c3a9b49bde597f5ab364aa9aa",
            "ad15cade3302f53272e5632cc5f57394958acb63a9da07b6f3230fd73b1dd13d",
            "92dd45252287e4af984e5332b17dad57c84c487aa1923d626be1d8e8becf30a1",
            "9d35bcf5b2ab0f84fe8c5dd44fe570a06a11a8a6156f61851e7cc346cc9a58b6",
        }
    ),
    62: frozenset(
        {
            "5fa9c06d9f138702703aa7c6c2a5afdde929208717156fe1859b08c74b1bd065",
            "da97ffef21ed689c821cbb0ce67975169ce46c312464f8cb7940e3bdc6275920",
            "18fa57706f5a2154bb39ba072a86aaf793ed3f315055914e7e9e52ad96a4f5c4",
        }
    ),
    65: frozenset(
        {
            "9d35bcf5b2ab0f84fe8c5dd44fe570a06a11a8a6156f61851e7cc346cc9a58b6",
            "cb16567f2a038b5bfdf41a09a81c011b3179710a8bc3f792e1cf34e7bce8d7dd",
        }
    ),
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


def _unique_value(document: Document, section: bytes, key: bytes) -> bytes | None:
    values = [
        record.value
        for record in document.records
        if isinstance(record, KeyValueRecord)
        and record.section == section
        and record.section_occurrence == 0
        and record.key == key
    ]
    return values[0] if len(values) == 1 else None


def _tokens_are_numeric(tokens: list[bytes]) -> bool:
    for token in tokens:
        try:
            text = token.decode("ascii")
            value = Decimal(text)
            if not value.is_finite():
                return False
        except (UnicodeDecodeError, InvalidOperation):
            return False
    return True


def corpus_anchors(
    root: Path, style: int, descriptors: list[dict[str, Any]]
) -> list[dict[str, object]]:
    """Return bounded structurally matching pinned historical XDX records."""

    anchors: list[dict[str, object]] = []
    for path in sorted(root.rglob("*.xxp")):
        try:
            data = path.read_bytes()
            document = parse_bytes(data)
        except (OSError, ValueError):
            continue
        digest = sha256(data).hexdigest()
        if digest not in _ANCHOR_SHA256_BY_STYLE[style]:
            continue
        if _unique_value(document, b"Header", b"Program") != b"XDX":
            continue
        match: dict[str, object] | None = None
        for record in document.records:
            if not (
                isinstance(record, KeyValueRecord)
                and record.section.endswith(b"\\MM\\0")
                and record.section_occurrence == 0
                and record.key == b"Style"
                and record.value == str(style).encode("ascii")
            ):
                continue
            holon = record.section.removesuffix(b"\\MM\\0")
            if _unique_value(document, holon, b"Type") != b"1":
                continue
            declared = _unique_value(document, record.section, b"NumPars")
            pars = _unique_value(document, record.section, b"Pars")
            if declared is None or pars is None:
                continue
            tokens = pars.split()
            try:
                declared_count = int(declared.decode("ascii"))
            except (UnicodeDecodeError, ValueError):
                continue
            if declared_count != len(tokens) or not _tokens_are_numeric(tokens):
                continue
            name = _unique_value(document, holon, b"Name")
            match = {
                "path": str(path),
                "sha256": digest,
                "xdx_version": (_unique_value(document, b"Header", b"Progversion") or b"").decode(
                    "ascii", errors="backslashreplace"
                ),
                "section": record.section.decode("ascii"),
                "name": None
                if name is None
                else name.decode("ascii", errors="backslashreplace"),
                "parameter_count": len(tokens),
                "pars_sha256": sha256(pars).hexdigest(),
            }
            break
        if match is None:
            continue
        anchors.append(match)
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
        report = getattr(validation, "report")
        verified = (
            bool(getattr(validation, "native_model_valid"))
            and bool(getattr(validation, "evaluates_to_3d"))
            and bool(getattr(validation, "basic_mesh_valid"))
            and report.get("cleanup_confirmed") is True
        )
        if not anchors:
            disposition = "INCONCLUSIVE"
        elif outcome == "succeeded":
            disposition = "VERIFIED" if verified else "NOT_VERIFIED"
        else:
            disposition = "INCONCLUSIVE"
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
    anchors = corpus_anchors(
        args.corpus_root, CONSTRUCTORS[args.constructor], operation["descriptors"]
    )
    if not anchors:
        error = "no structurally matching pinned historical XDX anchor"
    else:
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
        anchors,
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
