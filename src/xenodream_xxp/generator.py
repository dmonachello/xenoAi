"""Evidence-gated generation of native XenoDream X projects."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TypeAlias


COMPILER_PROFILE = "xdx-1.220-cube-evidence-2026-10-15"
TWO_CUBE_COMPILER_PROFILE = "xdx-1.220-two-cube-evidence-2026-10-15"
THREE_CUBE_COMPILER_PROFILE = "xdx-1.220-three-cube-evidence-2026-10-15"


class GenerationError(ValueError):
    """A requested value cannot be encoded by the verified compiler."""


class TemplateMismatchError(GenerationError):
    """The packaged XDX template does not match its evidence contract."""


def _require_finite_decimal(value: object, field: str) -> None:
    if not isinstance(value, Decimal):
        raise TypeError(f"{field} must be Decimal")
    if not value.is_finite():
        raise GenerationError(f"{field} must be finite")


@dataclass(frozen=True, slots=True)
class Vector3:
    x: Decimal = Decimal("0")
    y: Decimal = Decimal("0")
    z: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        _require_finite_decimal(self.x, "x")
        _require_finite_decimal(self.y, "y")
        _require_finite_decimal(self.z, "z")


@dataclass(frozen=True, slots=True)
class CubeSpec:
    """Verified editable fields of the XDX 1.220 cube project."""

    scale: Vector3 = Vector3(Decimal("50"), Decimal("50"), Decimal("50"))
    rotation: Vector3 = Vector3()
    position: Vector3 = Vector3()
    color_density: Decimal = Decimal("1")
    face_warp: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        if not isinstance(self.scale, Vector3):
            raise TypeError("scale must be Vector3")
        if not isinstance(self.rotation, Vector3):
            raise TypeError("rotation must be Vector3")
        if not isinstance(self.position, Vector3):
            raise TypeError("position must be Vector3")
        _require_finite_decimal(self.color_density, "color_density")
        _require_finite_decimal(self.face_warp, "face_warp")


SupportedCubes: TypeAlias = (
    tuple[CubeSpec]
    | tuple[CubeSpec, CubeSpec]
    | tuple[CubeSpec, CubeSpec, CubeSpec]
)


@dataclass(frozen=True, slots=True)
class CubeProjectSpec:
    """The verified Group1 shape containing one, two, or three cubes."""

    cubes: SupportedCubes = (CubeSpec(),)

    def __post_init__(self) -> None:
        if not isinstance(self.cubes, tuple):
            raise TypeError("cubes must be a tuple")
        if len(self.cubes) not in (1, 2, 3):
            raise GenerationError("cube projects require exactly 1, 2, or 3 cubes")
        for index, cube in enumerate(self.cubes):
            if not isinstance(cube, CubeSpec):
                raise TypeError(f"cubes[{index}] must be CubeSpec")


@dataclass(frozen=True, slots=True)
class ThreeCubeProjectSpec:
    """The observed Group1 project shape containing exactly three cubes."""

    cubes: tuple[CubeSpec, CubeSpec, CubeSpec] = (
        CubeSpec(position=Vector3(Decimal("-75"), Decimal("0"), Decimal("0"))),
        CubeSpec(),
        CubeSpec(position=Vector3(Decimal("75"), Decimal("0"), Decimal("0"))),
    )

    def __post_init__(self) -> None:
        if not isinstance(self.cubes, tuple):
            raise TypeError("cubes must be a tuple")
        if len(self.cubes) != 3:
            raise GenerationError("three-cube projects require exactly 3 cubes")
        for index, cube in enumerate(self.cubes):
            if not isinstance(cube, CubeSpec):
                raise TypeError(f"cubes[{index}] must be CubeSpec")


def compile_cube(spec: CubeSpec | None = None) -> bytes:
    """Compile one Group1/Cube2 project from verified XDX 1.220 evidence."""

    cube = spec if spec is not None else CubeSpec()
    return compile_cube_project(CubeProjectSpec(cubes=(cube,)))


def compile_cube_project(spec: CubeProjectSpec | None = None) -> bytes:
    """Compile a verified Group1 project containing one to three cubes."""

    from ._cube_project_template import compile_project_template

    project = spec if spec is not None else CubeProjectSpec()
    if not isinstance(project, CubeProjectSpec):
        raise TypeError("spec must be CubeProjectSpec")
    return compile_project_template(project)


def compile_three_cubes(spec: ThreeCubeProjectSpec | None = None) -> bytes:
    """Compile the evidenced Group1 project containing Cube2 through Cube4."""

    project = spec if spec is not None else ThreeCubeProjectSpec()
    return compile_cube_project(CubeProjectSpec(cubes=project.cubes))
