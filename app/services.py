from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable, Tuple


def compute_total(items: Iterable[Tuple[Decimal, int]]) -> Decimal:
    total = Decimal("0.00")
    for price, qty in items:
        if qty < 0:
            raise ValueError("Quantidade não pode ser negativa")
        total += (price * qty)
    # pad to 2 decimal places without rounding issues for representation
    return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
