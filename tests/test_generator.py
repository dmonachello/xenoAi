from __future__ import annotations

from decimal import Decimal
from hashlib import sha256
from pathlib import Path

import pytest

from xenodream_xxp.diffing import diff_documents
from xenodream_xxp.document import SectionRecord, parse_bytes
from xenodream_xxp.generator import (
    CubeSpec,
    GenerationError,
    ThreeCubeProjectSpec,
    Vector3,
    compile_cube,
    compile_three_cubes,
)


BASE = (
    Path(__file__).parents[1]
    / "experiments"
    / "group-creation"
    / "cube_base.xxp"
)
ACCEPTANCE = (
    Path(__file__).parents[1] / "experiments" / "m3-generated-cube"
)
ELONGATED_ACCEPTANCE = (
    Path(__file__).parents[1]
    / "experiments"
    / "m3-generated-elongated-cube"
)
THREE_CUBE_REFERENCE = (
    Path(__file__).parents[1]
    / "experiments"
    / "three-cube-positions"
    / "3_cube_positions.xxp"
)
THREE_CUBE_ACCEPTANCE = (
    Path(__file__).parents[1]
    / "experiments"
    / "m3-generated-three-cubes"
)
D = Decimal


def test_default_cube_is_byte_identical_to_verified_template() -> None:
    expected = BASE.read_bytes()
    generated = compile_cube()

    assert generated == expected
    assert sha256(generated).hexdigest() == (
        "fcba6d61f2af4cf79c1e86a20b570a0bb0039db3fb79c9d73c84e842430fc7a0"
    )
    assert parse_bytes(generated).to_bytes() == generated


def test_compiler_changes_only_verified_cube_fields() -> None:
    spec = CubeSpec(
        scale=Vector3(D("25"), D("50"), D("100")),
        rotation=Vector3(D("10"), D("20"), D("30")),
        position=Vector3(D("-5"), D("0"), D("5")),
        color_density=D("0.5"),
        face_warp=D("0.25"),
    )

    generated = compile_cube(spec)
    differences = diff_documents(parse_bytes(BASE.read_bytes()), parse_bytes(generated))

    assert [
        (item["section"], item["key"], item.get("token_index"))
        for item in differences
    ] == [
        ("Holon\\1", "Transform", 0),
        ("Holon\\1", "Transform", 2),
        ("Holon\\1", "Transform", 6),
        ("Holon\\1", "Transform", 7),
        ("Holon\\1", "Transform", 8),
        ("Holon\\1", "Transform", 9),
        ("Holon\\1", "Transform", 11),
        ("Holon\\1", "GradDensity", None),
        ("Holon\\1\\MM\\0", "Pars", 0),
    ]
    assert generated.count(b"\r\n") == 194
    assert b"\n" not in generated.replace(b"\r\n", b"")
    assert compile_cube(spec) == generated


def test_compiler_rejects_non_decimal_and_non_finite_values() -> None:
    with pytest.raises(TypeError, match="must be Decimal"):
        Vector3(1, D("0"), D("0"))  # type: ignore[arg-type]

    with pytest.raises(GenerationError, match="must be finite"):
        CubeSpec(face_warp=D("NaN"))


def test_compiler_rejects_values_that_need_rounding() -> None:
    spec = CubeSpec(position=Vector3(D("0.000001"), D("0"), D("0")))

    with pytest.raises(GenerationError, match="5-place precision"):
        compile_cube(spec)


def test_xenodream_resaved_generated_cube_without_byte_changes() -> None:
    generated = (ACCEPTANCE / "m3_generated_cube.xxp").read_bytes()
    resaved = (ACCEPTANCE / "m3_generated_cube_resaved.xxp").read_bytes()

    assert generated == resaved == compile_cube()
    assert len(generated) == 3_377
    assert sha256(resaved).hexdigest() == (
        "fcba6d61f2af4cf79c1e86a20b570a0bb0039db3fb79c9d73c84e842430fc7a0"
    )


def test_xenodream_resaved_generated_elongated_cube_without_changes() -> None:
    generated = (
        ELONGATED_ACCEPTANCE / "m3_generated_elongated_cube.xxp"
    ).read_bytes()
    resaved = (
        ELONGATED_ACCEPTANCE / "m3_generated_elongated_cube_resaved.xxp"
    ).read_bytes()
    spec = CubeSpec(scale=Vector3(D("25"), D("50"), D("100")))

    assert generated == resaved == compile_cube(spec)
    assert len(generated) == 3_378
    assert sha256(resaved).hexdigest() == (
        "a8b5b9d5963f5f1ef424d224871e00dd8c8391059e9117ca4579d3035159024d"
    )


def test_default_three_cubes_are_byte_identical_to_reference() -> None:
    expected = THREE_CUBE_REFERENCE.read_bytes()
    generated = compile_three_cubes()

    assert generated == expected
    assert len(generated) == 4_826
    assert sha256(generated).hexdigest() == (
        "caff33da71c7a24e6a79a7c4448a17daeefdc3c1915d3bc7d85ab167fe05654d"
    )
    assert parse_bytes(generated).to_bytes() == generated
    assert compile_three_cubes() == generated

    sections = [
        record.name.decode("ascii")
        for record in parse_bytes(generated).records
        if isinstance(record, SectionRecord)
    ]
    assert sections[:8] == [
        "Header",
        "Holon\\0",
        "Holon\\1",
        "Holon\\1\\MM\\0",
        "Holon\\2",
        "Holon\\2\\MM\\0",
        "Holon\\3",
        "Holon\\3\\MM\\0",
    ]
    assert sections[8] == "Gradients"


def test_three_cube_compiler_changes_only_each_cubes_verified_fields() -> None:
    spec = ThreeCubeProjectSpec(
        cubes=(
            CubeSpec(
                scale=Vector3(D("25"), D("50"), D("50")),
                position=Vector3(D("-75"), D("0"), D("0")),
            ),
            CubeSpec(rotation=Vector3(D("0"), D("30"), D("0"))),
            CubeSpec(
                position=Vector3(D("100"), D("0"), D("0")),
                color_density=D("0.5"),
                face_warp=D("0.25"),
            ),
        )
    )

    generated = compile_three_cubes(spec)
    differences = diff_documents(
        parse_bytes(THREE_CUBE_REFERENCE.read_bytes()), parse_bytes(generated)
    )

    assert [
        (item["section"], item["key"], item.get("token_index"))
        for item in differences
    ] == [
        ("Holon\\1", "Transform", 0),
        ("Holon\\2", "Transform", 7),
        ("Holon\\3", "Transform", 9),
        ("Holon\\3", "GradDensity", None),
        ("Holon\\3\\MM\\0", "Pars", 0),
    ]


def test_three_cube_project_rejects_unsupported_shapes() -> None:
    with pytest.raises(TypeError, match="tuple"):
        ThreeCubeProjectSpec(cubes=[CubeSpec()] * 3)  # type: ignore[arg-type]

    with pytest.raises(GenerationError, match="exactly 3"):
        ThreeCubeProjectSpec(cubes=(CubeSpec(),))  # type: ignore[arg-type]

    with pytest.raises(TypeError, match=r"cubes\[1\]"):
        ThreeCubeProjectSpec(
            cubes=(CubeSpec(), object(), CubeSpec())  # type: ignore[arg-type]
        )


def test_three_cube_compiler_rejects_rounding_on_later_cube() -> None:
    spec = ThreeCubeProjectSpec(
        cubes=(
            CubeSpec(position=Vector3(D("-75"), D("0"), D("0"))),
            CubeSpec(),
            CubeSpec(position=Vector3(D("75.000001"), D("0"), D("0"))),
        )
    )

    with pytest.raises(GenerationError, match="5-place precision"):
        compile_three_cubes(spec)


def test_xenodream_resaved_generated_three_cubes_without_changes() -> None:
    generated = (THREE_CUBE_ACCEPTANCE / "m3_generated_three_cubes.xxp").read_bytes()
    resaved = (
        THREE_CUBE_ACCEPTANCE / "m3_generated_three_cubes_resaved.xxp"
    ).read_bytes()

    assert generated == resaved == compile_three_cubes()
    assert len(generated) == 4_826
    assert sha256(resaved).hexdigest() == (
        "caff33da71c7a24e6a79a7c4448a17daeefdc3c1915d3bc7d85ab167fe05654d"
    )
