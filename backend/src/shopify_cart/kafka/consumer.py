"""Async Kafka consumer with a background task loop.

Milestone 0: consumes + logs. Real handlers are registered from Milestone 9.

Startup behavior:
  The broker may accept TCP connections before its consumer group coordinator
  is ready. Subscribing during that window produces noisy errors like
  "Group Coordinator Request failed: [Error 15] GroupCoordinatorNotAvailableError".
  We poll the admin API first and only subscribe once the broker reports a
  usable cluster.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
from collections.abc import Awaitable, Callable
from typing import Any

from aiokafka import AIOKafkaConsumer
from aiokafka.admin import AIOKafkaAdminClient
from aiokafka.errors import KafkaConnectionError, KafkaError

from shopify_cart.config import Settings
from shopify_cart.kafka.handlers import build_handlers
from shopify_cart.logging_config import get_logger

logger = get_logger(__name__)

Handler = Callable[[str, dict[str, Any]], Awaitable[None]]

# Broker readiness tuning
_READY_POLL_INTERVAL_SECONDS = 1.0
_READY_TIMEOUT_SECONDS = 60.0


async def wait_for_broker_ready(
    bootstrap_servers: str,
    *,
    timeout: float = _READY_TIMEOUT_SECONDS,
) -> bool:
    """Poll Kafka until the broker is ready to accept client operations.

    Returns True if the broker became ready, False on timeout. Never raises.

    We use AIOKafkaAdminClient because it performs the same bootstrap
    handshake as the consumer but without the group-coordinator dependency.
    Once `list_topics()` succeeds, the cluster metadata is available and
    the consumer's group join will succeed cleanly.
    """
    admin: AIOKafkaAdminClient | None = None
    try:
        admin = AIOKafkaAdminClient(
            bootstrap_servers=bootstrap_servers,
            request_timeout_ms=5000,
        )
        await admin.start()

        loop = asyncio.get_event_loop()
        deadline = loop.time() + timeout
        last_exc: Exception | None = None

        while loop.time() < deadline:
            try:
                await admin.list_topics()
                logger.info("kafka_broker_ready", bootstrap=bootstrap_servers)
                return True
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                await asyncio.sleep(_READY_POLL_INTERVAL_SECONDS)

        logger.warning(
            "kafka_broker_not_ready_timeout",
            bootstrap=bootstrap_servers,
            timeout_seconds=timeout,
            last_error=str(last_exc) if last_exc else None,
        )
        return False
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "kafka_admin_client_unavailable",
            bootstrap=bootstrap_servers,
            error=str(exc),
        )
        return False
    finally:
        if admin is not None:
            with contextlib.suppress(Exception):
                await admin.close()


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

        # ── Wait for the broker's group coordinator to be ready ──
        # This eliminates the initial flood of
        # "Group Coordinator Request failed" / "Topic not available"
        # errors on first boot.
        ready = await wait_for_broker_ready(
            self._settings.kafka_bootstrap_servers,
        )
        if not ready:
            self._connected = False
            logger.warning(
                "kafka_consumer_skipped",
                reason="broker_not_ready",
                hint="App will run without Kafka consumer.",
            )
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
                request_timeout_ms=10000,
                # Give the group coordinator time to stabilize without
                # spamming rebalance requests.
                session_timeout_ms=30000,
                heartbeat_interval_ms=10000,
                # Slow down topic-metadata retries during auto-create.
                metadata_max_age_ms=30000,
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
