import logging
import time
from decimal import Decimal
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from redis import Redis

from app import models
from app.database import Base, engine, get_db
from app.cache import cache_get, cache_set, get_redis_client
from app.messaging import PedidoQueuePublisher, get_queue_publisher
from app.schemas import ItemPedidoOut, PedidoCreateIn, PedidoOut, ProdutoOut
from app.services import build_item_specs


app = FastAPI(title="BuildFlow API", version="0.1.0")
logger = logging.getLogger(__name__)


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
def listar_produtos(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    cache: Optional[Redis] = Depends(get_redis_client),
):
    cache_key = f"produtos:{skip}:{limit}"
    cached = cache_get(cache, cache_key)
    if cached is not None:
        return cached

    produtos = db.query(models.Produto).offset(skip).limit(limit).all()
    data = [
        ProdutoOut(
            id=p.id,
            nome=p.nome,
            preco=float(p.preco),
            estoque=p.estoque,
        )
        for p in produtos
    ]
    cache_set(cache, cache_key, [item.dict() for item in data])
    return data


@app.post("/pedidos", response_model=PedidoOut, status_code=201)
def criar_pedido(
    payload: PedidoCreateIn,
    db: Session = Depends(get_db),
    publisher: PedidoQueuePublisher = Depends(get_queue_publisher),
):
    if not payload.itens:
        raise HTTPException(status_code=400, detail="Pedido deve conter ao menos um item")

    itens_payload = [item.dict() for item in payload.itens]
    try:
        specs, total = build_item_specs(db, itens_payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    pedido = models.Pedido(status="PENDENTE", total=total)
    db.add(pedido)

    try:
        db.flush()
        publisher.publish_pedido(pedido.id, itens_payload)
        db.commit()
    except Exception as exc:  # pragma: no cover - defensive logging em produção
        db.rollback()
        logger.exception("Falha ao publicar pedido %s na fila", getattr(pedido, "id", "?"))
        raise HTTPException(status_code=503, detail="Não foi possível enfileirar o pedido") from exc

    db.refresh(pedido)
    itens_out = [
        ItemPedidoOut(
            produto_id=spec.produto_id,
            quantidade=spec.quantidade,
            preco_unitario=float(spec.preco_unitario),
        )
        for spec in specs
    ]

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
