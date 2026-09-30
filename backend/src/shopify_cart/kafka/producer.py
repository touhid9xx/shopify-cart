"""Async Kafka producer wrapper.

Fails gracefully if Kafka is unavailable: publishing is best-effort,
and the app stays responsive even when the broker is down.
"""

from __future__ import annotations

import json
from typing import Any

from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaConnectionError, KafkaError

from shopify_cart.config import Settings
from shopify_cart.kafka.events import BaseEvent
from shopify_cart.logging_config import get_logger

logger = get_logger(__name__)


class KafkaProducer:
    """Async Kafka producer wrapper. Fails gracefully if Kafka is unavailable."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._producer: AIOKafkaProducer | None = None
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def start(self) -> None:
        if not self._settings.kafka_enabled:
            logger.warning("kafka_producer_disabled")
            return

        try:
            self._producer = AIOKafkaProducer(
                bootstrap_servers=self._settings.kafka_bootstrap_servers,
                client_id=self._settings.kafka_client_id,
                value_serializer=lambda v: json.dumps(v, default=str, ensure_ascii=False).encode(
                    "utf-8"
                ),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                acks="all",
                enable_idempotence=True,
                request_timeout_ms=5000,
            )
            await self._producer.start()
            self._connected = True
            logger.info(
                "kafka_producer_started",
                bootstrap=self._settings.kafka_bootstrap_servers,
            )
        except (KafkaConnectionError, KafkaError, OSError) as exc:
            self._connected = False
            logger.warning(
                "kafka_producer_unavailable",
                error=str(exc),
                hint="App will run without Kafka; events will be dropped.",
            )

    async def stop(self) -> None:
        if self._producer is not None:
            try:
                await self._producer.stop()
            except Exception as exc:  # noqa: BLE001
                # Shutdown path: swallow anything so app exit never crashes.
                logger.warning("kafka_producer_stop_error", error=str(exc))
            finally:
                self._producer = None
                self._connected = False
                logger.info("kafka_producer_stopped")

    async def publish(
        self,
        topic: str,
        event: BaseEvent | dict[str, Any],
        *,
        key: str | None = None,
    ) -> bool:
        """Publish an event. Returns True on success, False otherwise."""
        if not self._connected or self._producer is None:
            logger.warning("kafka_publish_skipped_not_connected", topic=topic)
            return False

        payload = event.model_dump(mode="json") if isinstance(event, BaseEvent) else event
        try:
            await self._producer.send_and_wait(topic, value=payload, key=key)
            logger.info("kafka_event_published", topic=topic, key=key)
            return True
        except (KafkaError, OSError) as exc:
            logger.error("kafka_publish_failed", topic=topic, error=str(exc))
            return False
