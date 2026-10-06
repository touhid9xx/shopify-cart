# backend/Dockerfile
# syntax=docker/dockerfile:1.7

# ═══════════════════════════════════════════════════════════════════
# Stage 1 — Builder (deps only, source NOT copied)
# ═══════════════════════════════════════════════════════════════════
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

# Build tools for native extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        g++ \
        libffi-dev \
        libssl-dev \
        default-libmysqlclient-dev \
        pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Metadata only — cached unless pyproject.toml changes
COPY pyproject.toml README.md ./

# Create venv early so its layer caches forever
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --upgrade pip wheel setuptools

# ── Runtime deps — mirror pyproject.toml [project.dependencies] ──
RUN pip install --no-cache-dir \
    "fastapi==0.115.5" \
    "uvicorn[standard]>=0.32.0" \
    "python-multipart>=0.0.12" \
    "pydantic==2.9.2" \
    "pydantic-settings>=2.6.0" \
    "email-validator>=2.2.0" \
    "sqlalchemy>=2.0.36" \
    "alembic>=1.14.0" \
    "pymysql>=1.1.1" \
    "cryptography>=43.0.0" \
    "pyjwt>=2.10.0" \
    "passlib[argon2]>=1.7.4" \
    "argon2-cffi>=23.1.0" \
    "structlog>=24.4.0" \
    "aiokafka>=0.12.0" \
    "datasets>=3.1.0" \
    "huggingface-hub>=0.27.0" \
    "pillow>=11.0.0" \
    "numpy>=2.1.0" \
    "pandas>=2.2.0" \
    "scikit-learn>=1.5.0" \
    "matplotlib>=3.9.0" \
    "mlflow>=2.19.0" \
    "optuna>=4.1.0" \
    "streamlit>=1.40.0" \
    "httpx>=0.27.0" \
    "requests>=2.32.0"

# ── CPU-only torch (biggest download, most stable layer) ──
RUN pip install --no-cache-dir \
    --index-url https://download.pytorch.org/whl/cpu \
    torch==2.6.0 torchvision==0.21.0


# ═══════════════════════════════════════════════════════════════════
# Stage 2 — Runtime
# ═══════════════════════════════════════════════════════════════════
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app/src" \
    APP_HOST=0.0.0.0 \
    APP_PORT=8000

# Runtime system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        libgomp1 \
        libglib2.0-0 \
        libgl1 \
        libmariadb3 \
        tini \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 appuser

# Copy the ready venv from builder
COPY --from=builder /opt/venv /opt/venv

WORKDIR /app

# ── SOURCE LAYERS LAST — only these invalidate on code edits ──
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser alembic/ ./alembic/
COPY --chown=appuser:appuser alembic.ini ./
COPY --chown=appuser:appuser scripts/ ./scripts/

# Writable dirs for uploads / logs
RUN mkdir -p /app/data/uploads /app/logs \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# ── Health check (single source of truth — no compose override) ──
HEALTHCHECK --interval=15s --timeout=10s --start-period=60s --retries=5 \
    CMD curl -fsS --connect-timeout 3 --max-time 8 http://127.0.0.1:8000/health || exit 1

ENTRYPOINT ["/usr/bin/tini", "--"]

CMD ["uvicorn", "shopify_cart.main:app", "--host", "0.0.0.0", "--port", "8000"]
