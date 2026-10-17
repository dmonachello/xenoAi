"""Domain values for the bounded MoI cylinder integration."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from xenosculpt.core import Revision
from xenosculpt.mesh import StlReport


def _dimension(value: Decimal, name: str) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite() or value < Decimal("0.001") or value > 10_000:
        raise ValueError(f"{name} must be between 0.001 and 10000 mm")
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    significant = text.lstrip("-0").replace(".", "")
    scale = len(text.partition(".")[2])
    if len(significant) > 12 or scale > 6:
        raise ValueError(f"{name} supports at most 12 significant digits and 6 decimal places")
    return Decimal(text)


@dataclass(frozen=True, slots=True)
class CylinderSpec:
    radius_mm: Decimal
    height_mm: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(self, "radius_mm", _dimension(self.radius_mm, "radius_mm"))
        object.__setattr__(self, "height_mm", _dimension(self.height_mm, "height_mm"))

    def to_dict(self) -> dict[str, str]:
        return {"radius_mm": format(self.radius_mm, "f"), "height_mm": format(self.height_mm, "f")}

    @classmethod
    def from_dict(cls, value: dict[str, object]) -> "CylinderSpec":
        if set(value) != {"radius_mm", "height_mm"} or not all(isinstance(v, str) for v in value.values()):
            raise ValueError("stored MoI cylinder specification is invalid")
        return cls(Decimal(value["radius_mm"]), Decimal(value["height_mm"]))


@dataclass(frozen=True, slots=True)
class MoiInstallation:
    executable: str
    file_version: str
    executable_sha256: str


@dataclass(frozen=True, slots=True)
class MoiEvidence:
    schema: str
    installation: MoiInstallation
    request_sha256: str
    create_script_sha256: str
    reopen_script_sha256: str
    native_sha256: str
    native_bytes: int
    stl_sha256: str
    stl_bytes: int
    create_seconds: float
    reopen_seconds: float
    mesh: StlReport


@dataclass(frozen=True, slots=True)
class MoiStatus:
    root: str
    application_id: str
    document_kind: str
    head: Revision
    cylinder: CylinderSpec
    evidence: MoiEvidence
