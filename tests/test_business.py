from decimal import Decimal
import pytest

from app.services import compute_total


def test_compute_total_basic():
    items = [
        (Decimal("10.50"), 2),  # 21.00
        (Decimal("5.00"), 3),   # 15.00
    ]
    total = compute_total(items)
    assert total == Decimal("36.00")


def test_compute_total_zero_and_rounding():
    items = [
        (Decimal("0.00"), 10),
        (Decimal("1.005"), 1),  # quantize to 2 decimals after sum
    ]
    total = compute_total(items)
    assert total == Decimal("1.01")


def test_compute_total_negative_quantity_raises():
    with pytest.raises(ValueError):
        compute_total([(Decimal("10.00"), -1)])

