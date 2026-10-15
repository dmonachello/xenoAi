"""Re-run the M1 acceptance checks against the preserved reference sample."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import sys


ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "src"))

from xenodream_xxp.diffing import diff_documents  # noqa: E402
from xenodream_xxp.document import parse_bytes  # noqa: E402
from xenodream_xxp.report import inspect_document  # noqa: E402


EXPECTED_SHA256 = "0f9a2a22f23b5ba587548285f8cb9821a0ebb1814920c7955296e0f8c6095bae"
SAMPLE = ROOT / "samples" / "originals" / "20061109Sirps08.xxp"


def main() -> int:
    source = SAMPLE.read_bytes()
    document = parse_bytes(source)
    serialized = document.to_bytes()
    report = inspect_document(document)
    differences = diff_documents(document, parse_bytes(serialized))

    checks = {
        "source_bytes": len(source) == 19_797,
        "source_sha256": sha256(source).hexdigest() == EXPECTED_SHA256,
        "byte_identical_roundtrip": serialized == source,
        "roundtrip_diff_empty": differences == [],
        "sections": report["record_counts"]["section"] == 38,
        "key_values": report["record_counts"]["key_value"] == 925,
        "holons": len(report["holons"]) == 26,
        "crlf_records": report["file"]["line_endings"]["crlf"] == 1001,
        "max_line_bytes": report["file"]["max_line_bytes"] == 3018,
    }
    result = {
        "sample": str(SAMPLE.relative_to(ROOT)),
        "sha256": sha256(source).hexdigest(),
        "checks": checks,
        "verified": all(checks.values()),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

