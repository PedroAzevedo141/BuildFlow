from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable, List, Sequence, Tuple

from sqlalchemy.orm import Session

from app import models


def compute_total(items: Iterable[Tuple[Decimal, int]]) -> Decimal:
    total = Decimal("0.00")
    for price, qty in items:
        if qty < 0:
            raise ValueError("Quantidade não pode ser negativa")
        total += (price * qty)
    # pad to 2 decimal places without rounding issues for representation
    return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class PedidoItemSpec:
    produto_id: int
    quantidade: int
    preco_unitario: Decimal


def build_item_specs(
    db: Session,
    itens_payload: Sequence[dict],
) -> Tuple[List[PedidoItemSpec], Decimal]:
    specs: List[PedidoItemSpec] = []
    for raw_item in itens_payload:
        try:
            produto_id = int(raw_item["produto_id"])
            quantidade = int(raw_item["quantidade"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Payload de item inválido") from exc

        if quantidade <= 0:
            raise ValueError("Quantidade deve ser maior que zero")

        produto = (
            db.query(models.Produto)
            .filter(models.Produto.id == produto_id)
            .first()
        )
        if not produto:
            raise LookupError(f"Produto {produto_id} não encontrado")

        preco_unitario = Decimal(produto.preco)
        specs.append(
            PedidoItemSpec(
                produto_id=produto.id,
                quantidade=quantidade,
                preco_unitario=preco_unitario,
            )
        )

    total = compute_total((spec.preco_unitario, spec.quantidade) for spec in specs)
    return specs, total
