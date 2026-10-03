"""Shared pytest fixtures.

Design rules:
  * Never import `shopify_cart.main.app` at module scope — the app must be
    built *inside* fixtures so monkeypatches land before lifespan runs.
  * Kafka is always mocked — no test may touch a real broker.
  * Settings are re-read per test via `get_settings.cache_clear()`.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport

from shopify_cart.config import Settings, get_settings

# ───────────────────────────────────────────────────────────
# 1) Force test env BEFORE any app import
# ───────────────────────────────────────────────────────────
os.environ["APP_ENV"] = "test"
os.environ["APP_DEBUG"] = "false"
os.environ["KAFKA_ENABLED"] = "false"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-do-not-use-in-production"
os.environ["JWT_ACCESS_TOKEN_EXPIRE_MINUTES"] = "15"
os.environ["JWT_REFRESH_TOKEN_EXPIRE_DAYS"] = "7"


# ───────────────────────────────────────────────────────────
# 2) Settings fixtures
# ───────────────────────────────────────────────────────────
@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Session-scoped Settings with test-safe values."""
    get_settings.cache_clear()
    return Settings()


@pytest.fixture(autouse=True)
def _reset_settings_cache() -> Iterator[None]:
    """Each test starts with a fresh Settings cache."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


# ───────────────────────────────────────────────────────────
# 3) Mock Kafka producer
# ───────────────────────────────────────────────────────────
@pytest.fixture
def mock_kafka_producer() -> AsyncMock:
    """AsyncMock standing in for KafkaProducer.

    - `start()`, `stop()` are no-ops
    - `publish()` returns True
    - `is_connected` is True
    - `publish.await_args_list` lets tests assert what was emitted
    """
    producer = AsyncMock(spec=object)  # loose spec — we add attrs below
    producer.start = AsyncMock(return_value=None)
    producer.stop = AsyncMock(return_value=None)
    producer.publish = AsyncMock(return_value=True)
    producer.is_connected = True
    return producer


# ───────────────────────────────────────────────────────────
# 4) Test client with Kafka patched
# ───────────────────────────────────────────────────────────
@pytest.fixture
def client(
    test_settings: Settings,
    mock_kafka_producer: AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[TestClient]:
    """Sync TestClient with KafkaProducer replaced by a mock."""
    monkeypatch.setattr(
        "shopify_cart.kafka.producer.KafkaProducer",
        lambda settings: mock_kafka_producer,
    )
    # If `main.py` re-exports KafkaProducer, patch that reference too.
    monkeypatch.setattr(
        "shopify_cart.main.KafkaProducer",
        lambda settings: mock_kafka_producer,
        raising=False,
    )

    from shopify_cart.main import create_app

    app = create_app()
    with TestClient(app) as c:
        assert app.state.kafka_producer is mock_kafka_producer, (
            "KafkaProducer was not patched — check monkeypatch target"
        )
        yield c


# ───────────────────────────────────────────────────────────
# 5) Async client (ASGI transport — no real socket)
# ───────────────────────────────────────────────────────────
@pytest.fixture
async def async_client(
    test_settings: Settings,
    mock_kafka_producer: AsyncMock,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[httpx.AsyncClient]:
    """Async HTTP client wired to the ASGI app.

    NOTE: ASGITransport does NOT run the app's lifespan.
    Tests that need startup/shutdown should use `client` (sync) instead.
    """
    monkeypatch.setattr(
        "shopify_cart.kafka.producer.KafkaProducer",
        lambda settings: mock_kafka_producer,
    )
    monkeypatch.setattr(
        "shopify_cart.main.KafkaProducer",
        lambda settings: mock_kafka_producer,
        raising=False,
    )

    from shopify_cart.main import create_app

    app = create_app()
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ───────────────────────────────────────────────────────────
# 6) Misc
# ───────────────────────────────────────────────────────────
@pytest.fixture
def anyio_backend() -> str:
    """Force asyncio backend for anyio-based async tests."""
    return "asyncio"
