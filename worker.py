import json
import logging
import os
from typing import Callable, Optional

import pika
from sqlalchemy.orm import Session

from app import models
from app.database import SessionLocal
from app.services import build_item_specs

logger = logging.getLogger(__name__)

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
PEDIDOS_QUEUE = os.getenv("PEDIDOS_QUEUE", "pedidos")

SessionFactory = Callable[[], Session]


def process_order_message(message: dict, session_factory: Optional[SessionFactory] = None) -> bool:
    """Processa uma mensagem individual vinda da fila."""
    session_factory = session_factory or SessionLocal
    try:
        pedido_id = int(message["pedido_id"])
    except (KeyError, TypeError, ValueError):
        logger.error("Mensagem inválida recebida: %s", message)
        return False

    itens_payload = message.get("itens") or []
    db = session_factory()
    try:
        pedido = (
            db.query(models.Pedido)
            .filter(models.Pedido.id == pedido_id)
            .first()
        )
        if not pedido:
            logger.error("Pedido %s não encontrado para processamento", pedido_id)
            return False

        if pedido.status != "PENDENTE":
            logger.info("Pedido %s ignorado (status atual: %s)", pedido_id, pedido.status)
            return False

        pedido.status = "PROCESSANDO"
        specs, total = build_item_specs(db, itens_payload)

        pedido.itens = [
            models.ItemPedido(
                pedido_id=pedido.id,
                produto_id=spec.produto_id,
                quantidade=spec.quantidade,
                preco_unitario=spec.preco_unitario,
            )
            for spec in specs
        ]
        pedido.total = total
        pedido.status = "CRIADO"
        db.commit()
        logger.info("Pedido %s processado com sucesso", pedido_id)
        return True
    except Exception:
        db.rollback()
        logger.exception("Erro ao processar pedido %s", pedido_id)
        try:
            pedido = (
                db.query(models.Pedido)
                .filter(models.Pedido.id == pedido_id)
                .first()
            )
            if pedido:
                pedido.itens = []
                pedido.status = "CANCELADO"
                db.commit()
        except Exception:
            db.rollback()
            logger.exception("Falha ao cancelar pedido %s após erro", pedido_id)
        return False
    finally:
        db.close()


def _consume_once(channel, method, properties, body):
    try:
        message = json.loads(body)
    except json.JSONDecodeError:
        logger.error("Mensagem malformada: %s", body)
        channel.basic_ack(delivery_tag=method.delivery_tag)
        return

    process_order_message(message)
    channel.basic_ack(delivery_tag=method.delivery_tag)


def start_worker() -> None:
    params = pika.URLParameters(RABBITMQ_URL)
    connection = pika.BlockingConnection(params)
    channel = connection.channel()
    channel.queue_declare(queue=PEDIDOS_QUEUE, durable=True)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=PEDIDOS_QUEUE, on_message_callback=_consume_once)

    logger.info("Worker aguardando mensagens na fila '%s'", PEDIDOS_QUEUE)
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        logger.info("Encerrando worker...")
        channel.stop_consuming()
    finally:
        connection.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    start_worker()
