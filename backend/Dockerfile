# Build from the repository root:  docker build -f backend/Dockerfile .
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/backend \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Pinned, cross-platform lockfile generated from pyproject.toml (see README).
COPY requirements.lock ./
RUN pip install -r requirements.lock

COPY pyproject.toml ./
COPY backend ./backend
COPY evaluation ./evaluation
COPY scripts ./scripts
COPY demo ./demo

# The `app` package lives in backend/, so run from there (uvicorn app.main:app,
# celery -A app.workers.celery_app, python ../scripts/...).
WORKDIR /app/backend

FROM base AS development

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

FROM base AS production

RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=5 \
    CMD curl -fsS http://localhost:8000/api/v1/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
