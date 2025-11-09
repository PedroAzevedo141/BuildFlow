from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from decimal import Decimal
from typing import List, Optional
import time
from sqlalchemy.exc import OperationalError

from app.database import Base, engine, get_db
from app import models
from app.schemas import ProdutoOut, PedidoCreateIn, PedidoOut, ItemPedidoOut
from app.services import compute_total


app = FastAPI(title="BuildFlow API", version="0.1.0")


# Create tables on startup (demo convenience). In production use migrations.
@app.on_event("startup")
def on_startup():
    # Simple retry to wait for DB when running in containers
    retries = 10
    delay = 2
    for attempt in range(retries):
        try:
            Base.metadata.create_all(bind=engine)
            db = next(get_db())
            try:
                if db.query(models.Produto).count() == 0:
                    seed = [
                        models.Produto(nome="Furadeira 500W", preco=Decimal("249.90"), estoque=25),
                        models.Produto(nome="Parafusadeira 12V", preco=Decimal("199.90"), estoque=40),
                        models.Produto(nome="Serra Circular 1500W", preco=Decimal("549.90"), estoque=10),
                    ]
                    db.add_all(seed)
                    db.commit()
            finally:
                db.close()
            break
        except OperationalError:
            if attempt == retries - 1:
                raise
            time.sleep(delay)


@app.get("/produtos", response_model=List[ProdutoOut])
def listar_produtos(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    produtos = db.query(models.Produto).offset(skip).limit(limit).all()
    return [
        ProdutoOut(
            id=p.id,
            nome=p.nome,
            preco=float(p.preco),
            estoque=p.estoque,
        )
        for p in produtos
    ]


@app.post("/pedidos", response_model=PedidoOut, status_code=201)
def criar_pedido(payload: PedidoCreateIn, db: Session = Depends(get_db)):
    if not payload.itens:
        raise HTTPException(status_code=400, detail="Pedido deve conter ao menos um item")

    # Validar produtos e preparar itens
    itens_out: List[ItemPedidoOut] = []
    itens_models: list[models.ItemPedido] = []
    precos_e_qtds: list[tuple[Decimal, int]] = []

    for item in payload.itens:
        produto = db.query(models.Produto).filter(models.Produto.id == item.produto_id).first()
        if not produto:
            raise HTTPException(status_code=404, detail=f"Produto {item.produto_id} não encontrado")
        if item.quantidade <= 0:
            raise HTTPException(status_code=400, detail="Quantidade deve ser maior que zero")

        preco_unit = Decimal(produto.preco)
        precos_e_qtds.append((preco_unit, item.quantidade))
        itens_models.append(
            models.ItemPedido(
                produto_id=produto.id,
                quantidade=item.quantidade,
                preco_unitario=preco_unit,
            )
        )
        itens_out.append(
            ItemPedidoOut(
                produto_id=produto.id,
                quantidade=item.quantidade,
                preco_unitario=float(preco_unit),
            )
        )

    total = compute_total(precos_e_qtds)
    pedido = models.Pedido(status="criado", total=total)
    pedido.itens = itens_models
    db.add(pedido)
    db.commit()
    db.refresh(pedido)

    return PedidoOut(
        id=pedido.id,
        status=pedido.status,
        total=float(pedido.total),
        itens=itens_out,
    )


@app.get("/pedidos/{pedido_id}", response_model=PedidoOut)
def obter_pedido(pedido_id: int, db: Session = Depends(get_db)):
    pedido = (
        db.query(models.Pedido)
        .filter(models.Pedido.id == pedido_id)
        .first()
    )
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    itens = [
        ItemPedidoOut(
            produto_id=it.produto_id,
            quantidade=it.quantidade,
            preco_unitario=float(it.preco_unitario),
        )
        for it in pedido.itens
    ]
    return PedidoOut(
        id=pedido.id,
        status=pedido.status,
        total=float(pedido.total),
        itens=itens,
    )


# Root for quick health check
@app.get("/")
def root():
    return {"name": "BuildFlow API", "status": "ok"}
