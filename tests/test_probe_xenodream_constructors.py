from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace

from xenodream_xxp.document import KeyValueRecord, parse_bytes


ROOT = Path(__file__).parents[1]
RECOVERY_SPEC = importlib.util.spec_from_file_location(
    "recover_metamorph_descriptors",
    ROOT / "scripts" / "recover_metamorph_descriptors.py",
)
assert RECOVERY_SPEC is not None and RECOVERY_SPEC.loader is not None
recovery = importlib.util.module_from_spec(RECOVERY_SPEC)
sys.modules[RECOVERY_SPEC.name] = recovery
RECOVERY_SPEC.loader.exec_module(recovery)

PROBE_SPEC = importlib.util.spec_from_file_location(
    "probe_xenodream_constructors",
    ROOT / "scripts" / "probe_xenodream_constructors.py",
)
assert PROBE_SPEC is not None and PROBE_SPEC.loader is not None
probe = importlib.util.module_from_spec(PROBE_SPEC)
sys.modules[PROBE_SPEC.name] = probe
PROBE_SPEC.loader.exec_module(probe)


def _report() -> dict[str, object]:
    operations = []
    for name, style in probe.CONSTRUCTORS.items():
        descriptors = [
            {
                "kind": "numeric",
                "slot": 0,
                "name": "Value",
                "default": 1.0,
                "decimal_places": 3,
            },
            {
                "kind": "choice",
                "slot": 1,
                "name": "Mode",
                "default": 0,
            },
        ]
        operations.append(
            {"name": name, "style": style, "descriptors": descriptors}
        )
    return {"operations": operations}


def _value(data: bytes, section: bytes, key: bytes) -> bytes:
    values = [
        record.value
        for record in parse_bytes(data).records
        if isinstance(record, KeyValueRecord)
        and record.section == section
        and record.key == key
    ]
    assert len(values) == 1
    return values[0]


def test_build_candidate_uses_closed_style_identity_and_descriptor_defaults() -> None:
    candidate = probe.build_candidate("Pipe", _report())

    assert _value(candidate, b"Holon\\1", b"Name") == b"Pipe2"
    assert _value(candidate, b"Holon\\1\\MM\\0", b"Style") == b"11"
    assert _value(candidate, b"Holon\\1\\MM\\0", b"NumPars") == b"2"
    assert _value(candidate, b"Holon\\1\\MM\\0", b"Pars") == b"1.000 0 "
    assert parse_bytes(candidate).to_bytes() == candidate


def test_manifest_never_authorizes_a_writer() -> None:
    candidate = probe.build_candidate("Cog", _report())
    manifest = probe._manifest(
        "Cog",
        candidate,
        next(item for item in _report()["operations"] if item["name"] == "Cog"),
        [],
        None,
        "not run",
    )

    assert manifest["disposition"] == "INCONCLUSIVE"
    assert manifest["writer_authorized"] is False
    assert manifest["registry_promoted"] is False
    assert manifest["fabrication_suitable"] is False


def test_automation_failure_is_inconclusive_not_a_constructor_rejection() -> None:
    candidate = probe.build_candidate("Torus", _report())
    validation = SimpleNamespace(
        id="validation",
        outcome="automation_failed",
        native_model_valid=False,
        evaluates_to_3d=False,
        basic_mesh_valid=False,
        fabrication_suitable=False,
        mesh_sha256=None,
        report={"cleanup_confirmed": True, "error": "chooser timeout", "stl": None},
    )

    manifest = probe._manifest(
        "Torus",
        candidate,
        next(item for item in _report()["operations"] if item["name"] == "Torus"),
        [],
        validation,
        None,
    )

    assert manifest["disposition"] == "INCONCLUSIVE"
    assert manifest["validation"]["error"] == "chooser timeout"
