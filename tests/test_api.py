from decimal import Decimal
from fastapi.testclient import TestClient

from app import models
from tests.conftest import create_client_with_db, seed_products, cleanup_overrides


def test_listar_produtos():
    client, SessionLocal, _ = create_client_with_db()
    try:
        with SessionLocal() as s:
            seed_products(s)
        resp = client.get("/produtos")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 2
        assert {d["nome"] for d in data} >= {"Produto A", "Produto B"}
    finally:
        cleanup_overrides()


def test_criar_e_buscar_pedido():
    client, SessionLocal, _ = create_client_with_db()
    try:
        with SessionLocal() as s:
            prods = seed_products(s)
            a, b = prods[0], prods[1]
            a_id, b_id = a.id, b.id

        payload = {
            "itens": [
                {"produto_id": a_id, "quantidade": 2},
                {"produto_id": b_id, "quantidade": 3},
            ]
        }
        r = client.post("/pedidos", json=payload)
        assert r.status_code == 201, r.text
        pedido = r.json()
        assert "id" in pedido and pedido["id"] > 0
        assert pedido["status"] == "criado"

        # total esperado: 2*10.50 + 3*5.00 = 36.00
        assert abs(pedido["total"] - 36.00) < 1e-6
        assert len(pedido["itens"]) == 2

        pedido_id = pedido["id"]
        r2 = client.get(f"/pedidos/{pedido_id}")
        assert r2.status_code == 200
        pedido2 = r2.json()
        assert pedido2["id"] == pedido_id
        assert abs(pedido2["total"] - 36.00) < 1e-6
    finally:
        cleanup_overrides()

