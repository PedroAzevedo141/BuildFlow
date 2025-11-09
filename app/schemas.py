from typing import List
from decimal import Decimal
from pydantic import BaseModel, Field, conint, validator


class ProdutoOut(BaseModel):
    id: int
    nome: str
    preco: float
    estoque: int

    class Config:
        orm_mode = True


class ItemPedidoIn(BaseModel):
    produto_id: int = Field(..., gt=0)
    quantidade: conint(gt=0)  # type: ignore


class PedidoCreateIn(BaseModel):
    itens: List[ItemPedidoIn]

    @validator("itens")
    def itens_nao_vazios(cls, v):
        if not v:
            raise ValueError("A lista de itens não pode ser vazia")
        return v


class ItemPedidoOut(BaseModel):
    produto_id: int
    quantidade: int
    preco_unitario: float

    class Config:
        orm_mode = True


class PedidoOut(BaseModel):
    id: int
    status: str
    total: float
    itens: List[ItemPedidoOut]

    class Config:
        orm_mode = True

