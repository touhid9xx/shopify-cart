"""FastAPI application entry point."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from shopify_cart.config import Settings, get_settings
from shopify_cart.db.session import SessionLocal
from shopify_cart.exceptions import register_exception_handlers
from shopify_cart.kafka.consumer import build_default_consumer
from shopify_cart.kafka.producer import KafkaProducer
from shopify_cart.logging_config import configure_logging, get_logger
from shopify_cart.middleware import RequestContextMiddleware
from shopify_cart.ml.predict import load_predictor_at_startup

logger = get_logger(__name__)


# ----------------------------------------------------------------------
# Lifespan — startup + shutdown
# ----------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = app.state.settings

    # ---- Startup ----
    logger.info(
        "app_starting",
        app_name=settings.app_name,
        env=settings.app_env,
        version=settings.app_version,
    )

    # Kafka producer
    producer = KafkaProducer(settings)
    await producer.start()
    app.state.kafka_producer = producer

    # Kafka consumer (background task)
    consumer = build_default_consumer(settings)
    await consumer.start()
    consumer.spawn()
    app.state.kafka_consumer = consumer

    # ML predictor — startup load (fail-safe)
    predictor = load_predictor_at_startup()
    app.state.predictor = predictor

    logger.info(
        "app_started",
        kafka_producer_connected=producer.is_connected,
        kafka_consumer_connected=consumer.is_connected,
        predictor_loaded=predictor.is_loaded,
    )

    try:
        yield
    finally:
        # ---- Shutdown ----
        logger.info("app_stopping")
        await app.state.kafka_consumer.stop()
        await app.state.kafka_producer.stop()
        logger.info("app_stopped")


# ----------------------------------------------------------------------
# Application factory
# ----------------------------------------------------------------------
def create_app() -> FastAPI:
    """Application factory."""
    settings = get_settings()
    configure_logging(
        debug=settings.app_debug,
        json_logs=settings.is_production,
    )

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.app_debug,
        lifespan=lifespan,
    )
    app.state.settings = settings

    # ── Middleware ──
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.api_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Process-Time-Ms"],
    )

    # ── Exception handlers ──
    register_exception_handlers(app)

    # ── Routes ──
    # Deferred import to guarantee the router module finishes loading
    # before we ask FastAPI to include it.
    from shopify_cart.api.v1.routes import api_router

    app.include_router(api_router, prefix=settings.api_v1_prefix)

    # ------------------------------------------------------------------
    # Health / readiness endpoints
    # ------------------------------------------------------------------
    @app.get("/health", tags=["meta"])
    async def health() -> dict[str, Any]:
        """Liveness probe — always returns 200 if the process responds.

        The `components` dict is informational: it reports the status of
        dependencies (db, kafka, predictor) but does not change the HTTP
        status code. Use `/ready` for readiness-based traffic gating.
        """
        components: dict[str, str] = {}

        # DB
        db_ok = False
        db = None
        try:
            db = SessionLocal()
            db.execute(text("SELECT 1")).scalar()
            db_ok = True
        except Exception:  # noqa: BLE001
            db_ok = False
        finally:
            if db is not None:
                db.close()
        components["db"] = "ok" if db_ok else "error"

        # Kafka
        producer = getattr(app.state, "kafka_producer", None)
        kafka_ok = bool(producer and producer.is_connected)
        components["kafka"] = "ok" if kafka_ok else "error"

        # Predictor
        predictor = getattr(app.state, "predictor", None)
        predictor_ok = bool(predictor and predictor.is_loaded)
        components["predictor"] = "ok" if predictor_ok else "error"

        return {
            "status": "ok",
            "app": settings.app_name,
            "env": settings.app_env,
            "version": settings.app_version,
            "components": components,
        }

    @app.get("/ready", tags=["meta"])
    async def ready() -> Response:
        """Readiness probe — 503 if any critical dependency is down.

        Uses a single return point so Mypy/Pylance are satisfied that all
        code paths return a value.
        """
        db_ok = False
        db = None
        try:
            db = SessionLocal()
            db.execute(text("SELECT 1")).scalar()
            db_ok = True
        except Exception:  # noqa: BLE001
            db_ok = False
        finally:
            if db is not None:
                db.close()

        status_code = 200 if db_ok else 503
        body: dict[str, str] = (
            {"status": "ready"} if db_ok else {"status": "not_ready", "reason": "db_unavailable"}
        )
        return JSONResponse(status_code=status_code, content=body)

    @app.get("/health/db", tags=["meta"])
    async def health_db() -> dict[str, Any]:
        """Detailed DB health check."""
        try:
            db = SessionLocal()
            try:
                result = db.execute(text("SELECT 1")).scalar()
                assert result == 1
            finally:
                db.close()
        except SQLAlchemyError as exc:
            logger.error("health_db_failed", error=str(exc))
            return {
                "status": "error",
                "database": "unavailable",
                "detail": str(exc),
            }
        return {"status": "ok", "database": "connected"}

    @app.get("/health/kafka", tags=["meta"])
    async def health_kafka() -> dict[str, Any]:
        """Kafka health check — publishes a test event to verify the connection."""
        producer: KafkaProducer = app.state.kafka_producer
        if not producer.is_connected:
            return {"status": "error", "kafka": "not_connected"}

        test_event = {
            "event_id": "health-check",
            "occurred_at": "1970-01-01T00:00:00Z",
            "version": 1,
            "source": "health",
        }
        ok = await producer.publish("health.check", test_event)
        return {
            "status": "ok" if ok else "error",
            "kafka": "connected" if ok else "publish_failed",
            "bootstrap": settings.kafka_bootstrap_servers,
        }

    return app


app = create_app()
