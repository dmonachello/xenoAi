from decimal import Decimal

import pytest

from xenosculpt.moi import CylinderSpec


def test_cylinder_spec_canonicalizes_positive_dimensions() -> None:
    spec = CylinderSpec(Decimal("15.000"), Decimal("40.0"))

    assert spec.radius_mm == Decimal("15")
    assert spec.height_mm == Decimal("40")
    assert spec.to_dict() == {"radius_mm": "15", "height_mm": "40"}


@pytest.mark.parametrize("value", ["0", "-1", "NaN", "Infinity", "10001", "0.0001", "1.0000001", "1234567890123"])
def test_cylinder_spec_rejects_unsafe_dimensions(value: str) -> None:
    with pytest.raises(ValueError):
        CylinderSpec(Decimal(value), Decimal("40"))
