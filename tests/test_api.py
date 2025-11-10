from tests.conftest import cleanup_overrides, create_client_with_db, seed_products
from worker import process_order_message


def test_listar_produtos():
    client, SessionLocal, _, _, cache = create_client_with_db()
    try:
        with SessionLocal() as s:
            seed_products(s)
        resp = client.get("/produtos")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 2
        assert {d["nome"] for d in data} >= {"Produto A", "Produto B"}

        cache_key = "produtos:0:100"
        assert cache_key in cache.store
        cached_payload = cache.store[cache_key]
        assert '"Produto A"' in cached_payload

        # segundo request deve reutilizar cache (simulado)
        resp_cached = client.get("/produtos")
        assert resp_cached.status_code == 200
        assert resp_cached.json() == data
    finally:
        cleanup_overrides()


def test_criar_e_buscar_pedido():
    client, SessionLocal, _, publisher, _ = create_client_with_db()
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
        assert pedido["status"] == "PENDENTE"

        # total esperado: 2*10.50 + 3*5.00 = 36.00
        assert abs(pedido["total"] - 36.00) < 1e-6
        assert len(pedido["itens"]) == 2

        assert publisher.messages, "Pedido não foi publicado na fila de testes"
        message = publisher.messages[-1]
        assert message["pedido_id"] == pedido["id"]

        # Simula o worker processando a fila
        processed = process_order_message(message, session_factory=SessionLocal)
        assert processed is True

        pedido_id = pedido["id"]
        r2 = client.get(f"/pedidos/{pedido_id}")
        assert r2.status_code == 200
        pedido2 = r2.json()
        assert pedido2["id"] == pedido_id
        assert pedido2["status"] == "CRIADO"
        assert len(pedido2["itens"]) == 2
        assert abs(pedido2["total"] - 36.00) < 1e-6
    finally:
        cleanup_overrides()
