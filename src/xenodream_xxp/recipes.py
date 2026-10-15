"""Procedural construction of supported XenoDream project specifications."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from typing import cast

from .generator import (
    ProjectSpec,
    SupportedObjects,
    Vector3,
    _require_finite_decimal,
)


def centered_x_row(
    objects: SupportedObjects,
    *,
    spacing: Decimal,
    center: Vector3 = Vector3(),
) -> ProjectSpec:
    """Place a supported object sequence at equal X-axis intervals."""

    _require_finite_decimal(spacing, "spacing")
    if not isinstance(center, Vector3):
        raise TypeError("center must be Vector3")

    source = ProjectSpec(objects=objects)
    midpoint = Decimal(len(source.objects) - 1) / Decimal("2")
    arranged = tuple(
        replace(
            item,
            position=Vector3(
                center.x + (Decimal(index) - midpoint) * spacing,
                center.y,
                center.z,
            ),
        )
        for index, item in enumerate(source.objects)
    )
    return ProjectSpec(objects=cast(SupportedObjects, arranged))
