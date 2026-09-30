"""Async Kafka consumer with a background task loop.

Milestone 0: consumes + logs. Real handlers are registered from Milestone 9.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
from collections.abc import Awaitable, Callable
from typing import Any

from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaConnectionError, KafkaError

from shopify_cart.config import Settings
from shopify_cart.kafka.handlers import build_handlers
from shopify_cart.logging_config import get_logger

logger = get_logger(__name__)

Handler = Callable[[str, dict[str, Any]], Awaitable[None]]


class KafkaConsumer:
    """Async Kafka consumer wrapper.

    Milestone 0: connects, optionally runs a background consume loop that
    just logs. Milestone 9 will register real per-topic handlers.
    """

    def __init__(
        self,
        settings: Settings,
        topics: list[str],
        *,
        group_id: str | None = None,
    ) -> None:
        self._settings = settings
        self._topics = topics
        # NOTE: our Settings field is `kafka_consumer_group`, not `kafka_group_id`.
        self._group_id = group_id or settings.kafka_consumer_group
        self._consumer: AIOKafkaConsumer | None = None
        self._connected = False
        self._task: asyncio.Task[None] | None = None
        self._handlers: dict[str, Handler] = {}
        self._stop_event = asyncio.Event()

    @property
    def is_connected(self) -> bool:
        return self._connected

    def register_handler(self, topic: str, handler: Handler) -> None:
        self._handlers[topic] = handler

    async def start(self) -> None:
        if not self._settings.kafka_enabled:
            logger.warning("kafka_consumer_disabled")
            return

        try:
            self._consumer = AIOKafkaConsumer(
                *self._topics,
                bootstrap_servers=self._settings.kafka_bootstrap_servers,
                group_id=self._group_id,
                client_id=f"{self._settings.kafka_client_id}-consumer",
                value_deserializer=lambda v: json.loads(v.decode("utf-8")),
                auto_offset_reset="earliest",
                enable_auto_commit=True,
                request_timeout_ms=5000,
            )
            await self._consumer.start()
            self._connected = True
            logger.info(
                "kafka_consumer_started",
                topics=self._topics,
                group_id=self._group_id,
            )
        except (KafkaConnectionError, KafkaError, OSError) as exc:
            self._connected = False
            logger.warning(
                "kafka_consumer_unavailable",
                error=str(exc),
                hint="App will run without Kafka consumer.",
            )

    async def stop(self) -> None:
        self._stop_event.set()

        # ── cancel background loop, wait briefly, swallow cancellation ──
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None

        # ── stop the underlying consumer ──
        if self._consumer is not None:
            with contextlib.suppress(Exception):
                await self._consumer.stop()
            self._consumer = None
            self._connected = False
            logger.info("kafka_consumer_stopped")

    def spawn(self) -> None:
        """Start consuming in a background task."""
        if self._connected and self._consumer is not None:
            self._stop_event.clear()
            self._task = asyncio.create_task(self._run(), name="kafka-consumer")

    async def _run(self) -> None:
        assert self._consumer is not None
        try:
            async for msg in self._consumer:
                if self._stop_event.is_set():
                    break

                topic = msg.topic
                raw = msg.value
                # aiokafka types this as Any | None; narrow before use.
                if not isinstance(raw, dict):
                    logger.warning(
                        "kafka_event_invalid_payload",
                        topic=topic,
                        payload_type=type(raw).__name__,
                    )
                    continue
                payload: dict[str, Any] = raw

                logger.info(
                    "kafka_event_received",
                    topic=topic,
                    partition=msg.partition,
                    offset=msg.offset,
                )

                handler = self._handlers.get(topic)
                if handler is None:
                    continue

                try:
                    await handler(topic, payload)
                except Exception:
                    logger.exception("kafka_handler_failed", topic=topic)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.error("kafka_consumer_loop_crashed", error=str(exc))


def build_default_consumer(settings: Settings) -> KafkaConsumer:
    """Construct a KafkaConsumer preloaded with default handlers."""
    consumer = KafkaConsumer(
        settings,
        topics=list(build_handlers().keys()),
    )
    for topic, handler in build_handlers().items():
        consumer.register_handler(topic, handler)
    return consumer
