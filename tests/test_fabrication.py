from __future__ import annotations

from decimal import Decimal as D

import pytest

from xenodream_xxp.fabrication import (
    CheckCode,
    CheckStatus,
    FabricationConstraints,
    FabricationCheck,
    FabricationError,
    FabricationVerdict,
    constraints_from_dict,
    derive_fabrication_verdict,
    evaluate_fabrication,
)
from xenodream_xxp.generator import Vector3
from xenodream_xxp.mesh import StlReport


def _mesh(*, dimensions=(100.0, 80.0, 60.0), boundary_edges=0) -> StlReport:
    return StlReport(
        path="mesh.stl",
        bytes=684,
        sha256="a" * 64,
        triangle_count=12,
        bounds_min=(0.0, 0.0, 0.0),
        bounds_max=dimensions,
        dimensions=dimensions,
        max_dimension=max(dimensions),
        degenerate_triangles=0,
        boundary_edges=boundary_edges,
        non_manifold_edges=0,
        inconsistent_winding_edges=0,
        connected_components=1,
        signed_volume=1000.0,
    )


def _by_code(checks):
    return {item.code: item for item in checks}


def test_assessment_passes_known_checks_and_keeps_unknown_checks_explicit() -> None:
    checks = evaluate_fabrication(
        _mesh(),
        constraints=FabricationConstraints(
            process="FDM",
            build_volume_mm=Vector3(D("220"), D("220"), D("250")),
            min_feature_mm=D("1.2"),
        ),
    )
    by_code = _by_code(checks)

    assert tuple(item.code for item in checks) == tuple(CheckCode)
    assert by_code[CheckCode.BASIC_MESH].status is CheckStatus.PASS
    assert by_code[CheckCode.BUILD_VOLUME].status is CheckStatus.PASS
    assert by_code[CheckCode.BUILD_VOLUME].measured_mm == (100.0, 80.0, 60.0)
    assert by_code[CheckCode.BUILD_VOLUME].limit_mm == (
        D("220"), D("220"), D("250")
    )
    assert by_code[CheckCode.SELF_INTERSECTIONS].status is CheckStatus.NOT_EVALUATED
    assert by_code[CheckCode.MINIMUM_FEATURE].status is CheckStatus.NOT_EVALUATED
    assert by_code[CheckCode.PROCESS].status is CheckStatus.NOT_EVALUATED
    assert derive_fabrication_verdict(checks) is FabricationVerdict.INCOMPLETE


def test_assessment_fails_when_current_orientation_exceeds_one_build_axis() -> None:
    checks = evaluate_fabrication(
        _mesh(dimensions=(221.0, 80.0, 60.0)),
        constraints=FabricationConstraints(
            build_volume_mm=Vector3(D("220"), D("220"), D("250"))
        ),
    )

    assert _by_code(checks)[CheckCode.BUILD_VOLUME].status is CheckStatus.FAIL
    assert derive_fabrication_verdict(checks) is FabricationVerdict.FAIL


def test_missing_optional_constraints_are_not_applicable_not_passing() -> None:
    checks = evaluate_fabrication(_mesh(), constraints=FabricationConstraints())
    by_code = _by_code(checks)

    assert by_code[CheckCode.BUILD_VOLUME].status is CheckStatus.NOT_APPLICABLE
    assert by_code[CheckCode.MINIMUM_FEATURE].status is CheckStatus.NOT_APPLICABLE
    assert by_code[CheckCode.PROCESS].status is CheckStatus.NOT_APPLICABLE
    assert derive_fabrication_verdict(checks) is FabricationVerdict.INCOMPLETE


def test_basic_mesh_failure_rejects_even_with_unevaluated_checks() -> None:
    checks = evaluate_fabrication(
        _mesh(boundary_edges=3), constraints=FabricationConstraints()
    )

    assert _by_code(checks)[CheckCode.BASIC_MESH].status is CheckStatus.FAIL
    assert derive_fabrication_verdict(checks) is FabricationVerdict.FAIL


def test_verdict_rejects_missing_or_duplicate_check_codes() -> None:
    checks = evaluate_fabrication(_mesh(), constraints=FabricationConstraints())

    with pytest.raises(FabricationError, match="exactly one result"):
        derive_fabrication_verdict(checks[:-1])
    with pytest.raises(FabricationError, match="exactly one result"):
        derive_fabrication_verdict(checks + (checks[0],))


def test_v1_policy_rejects_claimed_evidence_that_it_cannot_produce() -> None:
    checks = list(evaluate_fabrication(_mesh(), constraints=FabricationConstraints()))
    position = next(
        index
        for index, check in enumerate(checks)
        if check.code is CheckCode.SELF_INTERSECTIONS
    )
    checks[position] = FabricationCheck(
        CheckCode.SELF_INTERSECTIONS,
        CheckStatus.PASS,
        "claimed without analyzer evidence",
    )

    with pytest.raises(FabricationError, match="self-intersections"):
        derive_fabrication_verdict(tuple(checks))


def test_evaluator_rejects_an_unknown_policy_version() -> None:
    from xenodream_xxp.fabrication import PolicyIdentity

    with pytest.raises(FabricationError, match="unsupported fabrication policy"):
        evaluate_fabrication(
            _mesh(),
            constraints=FabricationConstraints(),
            policy=PolicyIdentity("workspace-constraints", "2"),
        )


def test_build_volume_comparison_preserves_decimal_limit_precision() -> None:
    checks = evaluate_fabrication(
        _mesh(dimensions=(0.1, 0.1, 0.1)),
        constraints=FabricationConstraints(
            build_volume_mm=Vector3(
                D("0.100000000000000004"),
                D("1"),
                D("1"),
            )
        ),
    )

    assert _by_code(checks)[CheckCode.BUILD_VOLUME].status is CheckStatus.FAIL


def test_constraint_decoder_normalizes_invalid_decimal_errors() -> None:
    with pytest.raises(FabricationError, match="invalid numeric value"):
        constraints_from_dict(
            {
                "process": None,
                "build_volume_mm": None,
                "min_feature_mm": "not-a-number",
            }
        )
