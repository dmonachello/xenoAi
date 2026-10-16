"""Run a resumable, evidence-scoped XenoDream metamorph mesh sweep."""

from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
import re
import sys
from typing import Any

from xenodream_xxp.diffing import diff_documents
from xenodream_xxp.document import parse_bytes
from xenodream_xxp.generator import CYLINDER_COMPILER_PROFILE, compile_cylinder
from xenodream_xxp.metamorph import inspect_metamorphs

from probe_metamorph_mesh import ProbeError, build_variant
from run_xenodream_batch_stl import MeshExportSettings, run_export


SCHEMA_V1 = "xenosculpt-metamorph-sweep-plan/v1"
SCHEMA_V2 = "xenosculpt-metamorph-sweep-plan/v2"
SCHEMA_V3 = "xenosculpt-metamorph-sweep-plan/v3"
SCHEMA = SCHEMA_V1
PLAN_SCHEMAS = {SCHEMA_V1, SCHEMA_V2, SCHEMA_V3}
MANIFEST_SCHEMA = "xenosculpt-metamorph-sweep/v1"
SUMMARY_SCHEMA = "xenosculpt-metamorph-sweep-summary/v1"
DEFAULT_EXECUTABLE = Path(
    r"C:\Program Files (x86)\XenoDream Software\XenoDreamX\XenoDreamX.exe"
)
Exporter = Callable[
    [Path, Path, Path, Path, float, float, MeshExportSettings],
    dict[str, object],
]


class SweepError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class SweepSource:
    data: bytes
    identity: dict[str, str]


def _digest(data: bytes) -> str:
    return sha256(data).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SweepError(f"expected a JSON object in {path}")
    return value


def _case_id(value: object) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[a-z0-9][a-z0-9-]*", value) is None:
        raise SweepError("case ids must contain lowercase letters, digits, and hyphens")
    return value


def load_plan(path: Path) -> dict[str, Any]:
    plan = _read_json(path)
    if plan.get("schema") not in PLAN_SCHEMAS:
        raise SweepError("unsupported sweep plan schema")
    if plan.get("operation") not in {"Sphere", "Cylinder"}:
        raise SweepError("the current sweep supports Sphere and Cylinder")
    if isinstance(plan.get("holon"), bool) or not isinstance(plan.get("holon"), int):
        raise SweepError("holon must be an integer")
    replicates = plan.get("baseline_replicates")
    if isinstance(replicates, bool) or not isinstance(replicates, int) or replicates < 2:
        raise SweepError("baseline_replicates must be an integer of at least 2")
    cases = plan.get("cases")
    if not isinstance(cases, list) or not cases:
        raise SweepError("cases must be a non-empty list")
    ids: set[str] = set()
    parameters: set[str] = set()
    for case in cases:
        if not isinstance(case, dict):
            raise SweepError("each case must be an object")
        identifier = _case_id(case.get("id"))
        evidence = case.get("source")
        if identifier in ids:
            raise SweepError(f"duplicate case id {identifier!r}")
        if identifier == "baseline":
            raise SweepError("case id 'baseline' is reserved")
        if not isinstance(evidence, str) or not evidence:
            raise SweepError(f"case {identifier!r} needs a source citation")
        if plan["schema"] in {SCHEMA_V1, SCHEMA_V3}:
            parameter = case.get("parameter")
            value = case.get("value")
            if not isinstance(parameter, str) or not parameter:
                raise SweepError(f"case {identifier!r} needs a parameter")
            if (
                plan["schema"] == SCHEMA_V1
                and parameter.casefold() in parameters
            ):
                raise SweepError(f"duplicate parameter {parameter!r}")
            if not isinstance(value, str) or not value:
                raise SweepError(f"case {identifier!r} needs a string value")
            parameters.add(parameter.casefold())
        else:
            compare_to = case.get("compare_to")
            if compare_to != "baseline" and compare_to not in ids:
                raise SweepError(
                    f"case {identifier!r} compare_to must name baseline or an earlier case"
                )
            mutations = case.get("mutations")
            if not isinstance(mutations, list) or not mutations:
                raise SweepError(f"case {identifier!r} needs a non-empty mutations list")
            case_parameters: set[str] = set()
            for mutation in mutations:
                if not isinstance(mutation, dict):
                    raise SweepError(f"case {identifier!r} mutations must be objects")
                parameter = mutation.get("parameter")
                value = mutation.get("value")
                if not isinstance(parameter, str) or not parameter:
                    raise SweepError(f"case {identifier!r} has an unnamed mutation")
                if parameter.casefold() in case_parameters:
                    raise SweepError(
                        f"case {identifier!r} repeats parameter {parameter!r}"
                    )
                if not isinstance(value, str) or not value:
                    raise SweepError(
                        f"case {identifier!r} parameter {parameter!r} needs a string value"
                    )
                case_parameters.add(parameter.casefold())
        ids.add(identifier)
    source = plan.get("source")
    if plan["schema"] == SCHEMA_V3:
        if source != {"kind": "generated", "constructor": "Cylinder"}:
            raise SweepError(
                "v3 source must be the recovered generated Cylinder constructor"
            )
    elif not isinstance(source, str) or not source:
        raise SweepError("source must be a path string")
    return plan


def _case_mutations(
    plan: dict[str, Any], case: dict[str, Any]
) -> tuple[list[dict[str, str]], str]:
    if plan["schema"] in {SCHEMA_V1, SCHEMA_V3}:
        return (
            [{"parameter": case["parameter"], "value": case["value"]}],
            "baseline",
        )
    return list(case["mutations"]), case["compare_to"]


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _resolve_source(plan_path: Path, source: object) -> SweepSource:
    if isinstance(source, str):
        path = (plan_path.parent / source).resolve(strict=True)
        data = path.read_bytes()
        return SweepSource(
            data,
            {"kind": "file", "path": str(path), "sha256": _digest(data)},
        )
    if source == {"kind": "generated", "constructor": "Cylinder"}:
        data = compile_cylinder()
        return SweepSource(
            data,
            {
                "kind": "generated",
                "constructor": "Cylinder",
                "compiler_profile": CYLINDER_COMPILER_PROFILE,
                "sha256": _digest(data),
            },
        )
    raise SweepError("unsupported sweep source")


def _require_plan_operation(source: bytes, holon: int, expected: str) -> None:
    report = inspect_metamorphs(parse_bytes(source))
    matches = [
        item
        for item in report["metamorphs"]
        if item["holon_index"] == holon and item["metamorph_index"] == 0
    ]
    actual = None if len(matches) != 1 else matches[0]["operation"]["name"]
    if actual != expected:
        raise SweepError(
            f"source operation {actual!r} does not match plan operation {expected!r}"
        )


def prepare_sweep(
    plan_path: Path,
    output_directory: Path,
    settings: MeshExportSettings,
) -> dict[str, Any]:
    plan_bytes = plan_path.read_bytes()
    plan = load_plan(plan_path)
    resolved_source = _resolve_source(plan_path, plan["source"])
    source = resolved_source.data
    _require_plan_operation(source, plan["holon"], plan["operation"])
    manifest_path = output_directory / "manifest.json"
    if manifest_path.exists():
        manifest = _read_json(manifest_path)
        if manifest.get("schema") != MANIFEST_SCHEMA:
            raise SweepError("existing output has an unsupported manifest")
        if manifest.get("plan", {}).get("sha256") != _digest(plan_bytes):
            raise SweepError("existing output belongs to a different sweep plan")
        if manifest.get("source", {}).get("sha256") != _digest(source):
            raise SweepError("sweep source changed after preparation")
        if manifest.get("settings") != asdict(settings):
            raise SweepError("existing output uses different mesh settings")
        for job in manifest["jobs"]:
            path = output_directory / job["file"]
            if not path.is_file() or _digest(path.read_bytes()) != job["sha256"]:
                raise SweepError(f"prepared variant is missing or changed: {path}")
        return manifest
    if output_directory.exists() and any(output_directory.iterdir()):
        raise SweepError(f"output directory is not empty: {output_directory}")
    output_directory.mkdir(parents=True, exist_ok=True)
    variants = output_directory / "variants"
    variants.mkdir()
    jobs: list[dict[str, Any]] = []
    for index in range(plan["baseline_replicates"]):
        identifier = f"baseline-{index + 1}"
        file_name = f"variants/{identifier}.xxp"
        (output_directory / file_name).write_bytes(source)
        jobs.append(
            {
                "id": identifier,
                "kind": "baseline",
                "file": file_name,
                "sha256": _digest(source),
                "diff": [],
            }
        )
    for case in plan["cases"]:
        data = source
        mutations, compare_to = _case_mutations(plan, case)
        mutation_facts = []
        for mutation in mutations:
            try:
                data, facts = build_variant(
                    data,
                    plan["holon"],
                    mutation["parameter"],
                    mutation["value"],
                )
            except ProbeError as error:
                raise SweepError(f"case {case['id']}: {error}") from error
            mutation_facts.append(
                {
                    "parameter": mutation["parameter"],
                    "requested": mutation["value"],
                    "persisted": facts["persisted"],
                    "changed": facts["persisted"] != facts["source_token"],
                }
            )
        differences = diff_documents(parse_bytes(source), parse_bytes(data))
        if len(differences) != sum(item["changed"] for item in mutation_facts):
            raise SweepError(f"case {case['id']} cumulative diff count is inconsistent")
        file_name = f"variants/{case['id']}.xxp"
        (output_directory / file_name).write_bytes(data)
        job = {
            "id": case["id"],
            "kind": "case",
            "selection_source": case["source"],
            "compare_to": compare_to,
            "file": file_name,
            "sha256": _digest(data),
            "diff": differences,
            "mutations": mutation_facts,
        }
        if plan["schema"] in {SCHEMA_V1, SCHEMA_V3}:
            job.update(
                {
                    "parameter": case["parameter"],
                    "requested": case["value"],
                    "persisted": mutation_facts[0]["persisted"],
                }
            )
        jobs.append(job)
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "plan": {"path": str(plan_path.resolve()), "sha256": _digest(plan_bytes)},
        "source": resolved_source.identity,
        "operation": plan["operation"],
        "holon": plan["holon"],
        "settings": asdict(settings),
        "jobs": jobs,
        "claims": {"native_acceptance": False, "printable": False},
    }
    _write_json(manifest_path, manifest)
    return manifest


def _successful_report(path: Path, digest: str) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    report = _read_json(path)
    if (
        report.get("outcome") == "succeeded"
        and report.get("input", {}).get("source_sha256_before") == digest
        and isinstance(report.get("stl"), dict)
    ):
        return report
    return None


def _topology_valid(stl: dict[str, Any]) -> bool:
    return (
        stl["connected_components"] == 1
        and stl["boundary_edges"] == 0
        and stl["non_manifold_edges"] == 0
        and stl["inconsistent_winding_edges"] == 0
        and stl["degenerate_triangles"] == 0
        and stl["signed_volume"] != 0
    )


def _job_mutations(job: dict[str, Any]) -> list[dict[str, Any]]:
    mutations = job.get("mutations")
    if isinstance(mutations, list):
        return mutations
    return [
        {
            "parameter": job["parameter"],
            "requested": job["requested"],
            "persisted": job["persisted"],
            "changed": bool(job.get("diff")),
        }
    ]


def summarize_sweep(
    manifest: dict[str, Any], output_directory: Path
) -> dict[str, Any]:
    completed: list[dict[str, Any]] = []
    missing: list[str] = []
    execution: list[dict[str, Any]] = []
    for job in manifest["jobs"]:
        reports = sorted((output_directory / "runs" / job["id"]).glob("attempt-*/report.json"))
        report_values = [_read_json(path) for path in reports]
        execution.append(
            {
                "id": job["id"],
                "attempts": len(report_values),
                "outcomes": [report.get("outcome") for report in report_values],
            }
        )
        report = next(
            (
                candidate
                for path in reports
                if (candidate := _successful_report(path, job["sha256"])) is not None
            ),
            None,
        )
        if report is None:
            missing.append(job["id"])
        else:
            completed.append({"job": job, "report": report})
    baselines = [item for item in completed if item["job"]["kind"] == "baseline"]
    baseline = baselines[0]["report"]["stl"] if baselines else None
    completed_by_id = {item["job"]["id"]: item for item in completed}
    baseline_variation = None
    if baselines:
        meshes = [item["report"]["stl"] for item in baselines]
        baseline_variation = {
            "replicates": len(meshes),
            "triangle_count_span": max(x["triangle_count"] for x in meshes)
            - min(x["triangle_count"] for x in meshes),
            "absolute_volume_span": max(abs(x["signed_volume"]) for x in meshes)
            - min(abs(x["signed_volume"]) for x in meshes),
            "dimension_spans": [
                max(x["dimensions"][axis] for x in meshes)
                - min(x["dimensions"][axis] for x in meshes)
                for axis in range(3)
            ],
        }
    results = []
    missing_controls: list[str] = []
    if baseline is not None:
        for item in completed:
            if item["job"]["kind"] != "case":
                continue
            compare_to = item["job"].get("compare_to", "baseline")
            if compare_to == "baseline":
                control = baseline
                control_sha256 = manifest["source"]["sha256"]
            else:
                control_item = completed_by_id.get(compare_to)
                if control_item is None:
                    missing_controls.append(f"{item['job']['id']}->{compare_to}")
                    continue
                control = control_item["report"]["stl"]
                control_sha256 = control_item["job"]["sha256"]
            stl = item["report"]["stl"]
            dimension_delta = [
                stl["dimensions"][axis] - control["dimensions"][axis]
                for axis in range(3)
            ]
            volume_delta = abs(stl["signed_volume"]) - abs(control["signed_volume"])
            dimension_fraction = max(
                abs(dimension_delta[axis]) / control["dimensions"][axis]
                for axis in range(3)
            )
            volume_fraction = abs(volume_delta) / abs(control["signed_volume"])
            observed_effects = []
            if baseline_variation is not None:
                if (
                    abs(stl["triangle_count"] - control["triangle_count"])
                    > baseline_variation["triangle_count_span"]
                ):
                    observed_effects.append("triangle_count")
                if abs(volume_delta) > baseline_variation["absolute_volume_span"]:
                    observed_effects.append("absolute_volume")
                if any(
                    abs(dimension_delta[axis])
                    > baseline_variation["dimension_spans"][axis]
                    for axis in range(3)
                ):
                    observed_effects.append("dimensions")
            result = {
                "id": item["job"]["id"],
                "parameter": item["job"].get("parameter")
                or " + ".join(
                    mutation["parameter"] for mutation in _job_mutations(item["job"])
                ),
                "selection_source": item["job"]["selection_source"],
                "compare_to": compare_to,
                "control_source_sha256": control_sha256,
                "source_sha256": item["job"]["sha256"],
                "stl_sha256": stl["sha256"],
                "mutations": _job_mutations(item["job"]),
                "dimensions": stl["dimensions"],
                "triangle_count": stl["triangle_count"],
                "absolute_volume": abs(stl["signed_volume"]),
                "delta": {
                    "dimensions": dimension_delta,
                    "triangle_count": stl["triangle_count"]
                    - control["triangle_count"],
                    "absolute_volume": volume_delta,
                },
                "impact_score": max(dimension_fraction, volume_fraction),
                "changes_exceeding_observed_baseline": observed_effects,
                "basic_topology_valid": _topology_valid(stl),
            }
            if "requested" in item["job"]:
                result["requested"] = item["job"]["requested"]
                result["persisted"] = item["job"]["persisted"]
            results.append(result)
    results.sort(key=lambda item: (-item["impact_score"], item["id"]))
    return {
        "schema": SUMMARY_SCHEMA,
        "complete": not missing and not missing_controls,
        "missing_jobs": missing,
        "missing_controls": missing_controls,
        "execution": execution,
        "settings": manifest["settings"],
        "baseline": baseline,
        "baseline_variation": baseline_variation,
        "ranked_results": results,
        "all_basic_topology_valid": bool(results)
        and all(item["basic_topology_valid"] for item in results),
        "printable": False,
    }


def run_sweep(
    plan_path: Path,
    output_directory: Path,
    *,
    executable: Path = DEFAULT_EXECUTABLE,
    attempts: int = 2,
    timeout_seconds: float = 150,
    poll_seconds: float = 1,
    settings: MeshExportSettings = MeshExportSettings(100, 25),
    exporter: Exporter = run_export,
) -> dict[str, Any]:
    if attempts < 1:
        raise SweepError("attempts must be at least 1")
    manifest = prepare_sweep(plan_path, output_directory, settings)
    for job in manifest["jobs"]:
        job_root = output_directory / "runs" / job["id"]
        attempt_numbers = [
            int(match.group(1))
            for path in job_root.glob("attempt-*")
            if (match := re.fullmatch(r"attempt-([0-9]+)", path.name)) is not None
        ]
        prior = sorted(job_root.glob("attempt-*/report.json"))
        if any(_successful_report(path, job["sha256"]) for path in prior):
            continue
        first_attempt = max(attempt_numbers, default=0) + 1
        for attempt in range(first_attempt, attempts + 1):
            run_directory = job_root / f"attempt-{attempt:03d}"
            report_path = run_directory / "report.json"
            exporter(
                executable,
                output_directory / job["file"],
                run_directory,
                report_path,
                timeout_seconds,
                poll_seconds,
                settings,
            )
            if _successful_report(report_path, job["sha256"]) is not None:
                break
    summary = summarize_sweep(manifest, output_directory)
    _write_json(output_directory / "summary.json", summary)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("plan", type=Path)
    parser.add_argument("output_directory", type=Path)
    parser.add_argument("--executable", type=Path, default=DEFAULT_EXECUTABLE)
    parser.add_argument("--attempts", type=int, default=2)
    parser.add_argument("--timeout-seconds", type=float, default=150)
    parser.add_argument("--stl-max-dimension-mm", type=int, default=100)
    parser.add_argument("--mesh-size-percent", type=int, default=25)
    args = parser.parse_args(argv)
    try:
        summary = run_sweep(
            args.plan,
            args.output_directory,
            executable=args.executable,
            attempts=args.attempts,
            timeout_seconds=args.timeout_seconds,
            settings=MeshExportSettings(
                args.stl_max_dimension_mm, args.mesh_size_percent
            ),
        )
    except (OSError, RuntimeError, ProbeError, SweepError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
