# backend/Dockerfile
# syntax=docker/dockerfile:1.7

# ═══════════════════════════════════════════════════════════════════
# Stage 1 — Builder
# ═══════════════════════════════════════════════════════════════════
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

# Build tools
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

# Copy metadata first — better layer caching
COPY pyproject.toml README.md ./

# Copy source so setuptools can find package
COPY src/ ./src/

# Create the venv we'll copy into runtime
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install the app (NOT editable) — this copies source into site-packages.
# Use --no-cache-dir to keep the layer small.
RUN pip install --upgrade pip wheel setuptools \
    && pip install --no-cache-dir .

# Install CPU-only torch AFTER the project install, overriding the torch
# version that came from PyPI (cu124 wheels are ~2.5 GB; cpu wheels ~200 MB).
RUN pip install --no-cache-dir --force-reinstall \
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
    APP_ENV=production \
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

# Copy source (used by PYTHONPATH=/app/src)
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser alembic/ ./alembic/
COPY --chown=appuser:appuser alembic.ini ./
COPY --chown=appuser:appuser scripts/ ./scripts/

# Writable dirs for uploads / logs
RUN mkdir -p /app/data/uploads /app/logs \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=5 \
    CMD curl -fsS --connect-timeout 3 --max-time 8 http://127.0.0.1:8000/health || exit 1

ENTRYPOINT ["/usr/bin/tini", "--"]

CMD ["uvicorn", "shopify_cart.main:app", "--host", "0.0.0.0", "--port", "8000"]
