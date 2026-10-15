from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from xenodream_xxp import (
    CubeSpec,
    GenerationError,
    SphereSpec,
    Vector3,
    centered_x_row,
    compile_project,
)


D = Decimal
ROOT = Path(__file__).parents[1]


@pytest.mark.parametrize(
    ("objects", "spacing", "reference"),
    [
        (
            (CubeSpec(),),
            D("100"),
            ROOT / "experiments" / "group-creation" / "cube_base.xxp",
        ),
        (
            (CubeSpec(), CubeSpec()),
            D("100"),
            ROOT / "experiments" / "two-cube-positions" / "two_cubesV2.xxp",
        ),
        (
            (CubeSpec(), CubeSpec(), CubeSpec()),
            D("75"),
            ROOT
            / "experiments"
            / "three-cube-positions"
            / "3_cube_positions.xxp",
        ),
        (
            (SphereSpec(),),
            D("100"),
            ROOT
            / "experiments"
            / "m4-generated-sphere"
            / "m4_generated_sphere_resaved.xxp",
        ),
        (
            (CubeSpec(), SphereSpec()),
            D("100"),
            ROOT / "experiments" / "cube-sphere" / "cube_sphere.xxp",
        ),
    ],
)
def test_centered_x_row_reproduces_accepted_profiles(
    objects, spacing: Decimal, reference: Path
) -> None:
    project = centered_x_row(objects, spacing=spacing)

    assert compile_project(project) == reference.read_bytes()


def test_centered_x_row_uses_center_and_preserves_non_position_fields() -> None:
    first = CubeSpec(
        scale=Vector3(D("25"), D("50"), D("100")),
        rotation=Vector3(D("10"), D("20"), D("30")),
        position=Vector3(D("999"), D("999"), D("999")),
        color_density=D("0.5"),
        face_warp=D("0.25"),
    )
    second = CubeSpec(position=Vector3(D("-999"), D("-999"), D("-999")))
    center = Vector3(D("20"), D("10"), D("-5"))

    project = centered_x_row((first, second), spacing=D("80"), center=center)

    assert project.objects[0].position == Vector3(D("-20"), D("10"), D("-5"))
    assert project.objects[1].position == Vector3(D("60"), D("10"), D("-5"))
    assert project.objects[0].scale == first.scale
    assert project.objects[0].rotation == first.rotation
    assert project.objects[0].color_density == first.color_density
    assert project.objects[0].face_warp == first.face_warp
    assert first.position == Vector3(D("999"), D("999"), D("999"))


def test_centered_x_row_allows_zero_and_negative_spacing() -> None:
    overlapped = centered_x_row((CubeSpec(), CubeSpec()), spacing=D("0"))
    reversed_row = centered_x_row((CubeSpec(), SphereSpec()), spacing=D("-100"))

    assert [item.position.x for item in overlapped.objects] == [D("0"), D("0")]
    assert [item.position.x for item in reversed_row.objects] == [D("50"), D("-50")]


@pytest.mark.parametrize("spacing", [1, D("NaN"), D("Infinity")])
def test_centered_x_row_rejects_invalid_spacing(spacing) -> None:
    error = TypeError if not isinstance(spacing, Decimal) else GenerationError
    with pytest.raises(error, match="spacing"):
        centered_x_row((CubeSpec(),), spacing=spacing)


def test_centered_x_row_rejects_invalid_center_and_unsupported_sequence() -> None:
    with pytest.raises(TypeError, match="center"):
        centered_x_row((CubeSpec(),), spacing=D("100"), center=(0, 0, 0))

    with pytest.raises(GenerationError, match="supported object sequences"):
        centered_x_row((SphereSpec(), CubeSpec()), spacing=D("100"))


def test_compiler_rejects_row_positions_beyond_verified_precision() -> None:
    project = centered_x_row(
        (CubeSpec(), SphereSpec()),
        spacing=D("0.00001"),
    )

    with pytest.raises(GenerationError, match="verified 5-place precision"):
        compile_project(project)
