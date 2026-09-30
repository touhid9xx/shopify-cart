#!/bin/sh
# Docker entrypoint — runs migrations then starts the app.
# Used by docker-compose if you want auto-migrate on boot.

set -e

echo "[entrypoint] Waiting for MySQL..."
until python -c "
import sys
from sqlalchemy import create_engine, text
from shopify_cart.config import get_settings
try:
    engine = create_engine(get_settings().database_url, pool_pre_ping=True)
    with engine.connect() as conn:
        conn.execute(text('SELECT 1'))
    sys.exit(0)
except Exception as e:
    print(f'  DB not ready: {e}', file=sys.stderr)
    sys.exit(1)
"; do
    sleep 2
done

echo "[entrypoint] Running Alembic migrations..."
alembic upgrade head

echo "[entrypoint] Starting application..."
exec uvicorn shopify_cart.main:app \
    --host "${APP_HOST:-0.0.0.0}" \
    --port "${APP_PORT:-8000}" \
    --log-config /dev/null \
    --access-log
