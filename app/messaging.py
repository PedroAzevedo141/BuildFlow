import json
import logging
import os
from typing import Optional, Sequence

import pika

logger = logging.getLogger(__name__)

DEFAULT_RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
DEFAULT_PEDIDOS_QUEUE = os.getenv("PEDIDOS_QUEUE", "pedidos")


class PedidoQueuePublisher:
    """Thin wrapper around pika to publish mensagens de pedidos."""

    def __init__(self, amqp_url: Optional[str] = None, queue_name: Optional[str] = None):
        self.amqp_url = amqp_url or DEFAULT_RABBITMQ_URL
        self.queue_name = queue_name or DEFAULT_PEDIDOS_QUEUE

    def publish_pedido(self, pedido_id: int, itens: Sequence[dict]) -> None:
        message = {"pedido_id": pedido_id, "itens": list(itens)}
        self._publish(message)

    def _publish(self, message: dict) -> None:
        logger.debug("Publicando pedido %s na fila %s", message.get("pedido_id"), self.queue_name)
        params = pika.URLParameters(self.amqp_url)
        connection = pika.BlockingConnection(params)
        channel = connection.channel()
        channel.queue_declare(queue=self.queue_name, durable=True)
        channel.basic_publish(
            exchange="",
            routing_key=self.queue_name,
            body=json.dumps(message).encode("utf-8"),
            properties=pika.BasicProperties(delivery_mode=2),
        )
        connection.close()


_publisher: Optional[PedidoQueuePublisher] = None


def get_queue_publisher() -> PedidoQueuePublisher:
    global _publisher
    if _publisher is None:
        _publisher = PedidoQueuePublisher()
    return _publisher


__all__ = ["PedidoQueuePublisher", "get_queue_publisher"]
