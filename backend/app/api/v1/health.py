import asyncio

import boto3
import chromadb
import redis
from fastapi import APIRouter, Depends, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.config import get_settings
from app.core.security import TokenData, require_role

router = APIRouter()
settings = get_settings()


@router.get("/health")
async def health_check():
    """Liveness probe: the process is up and serving.

    It deliberately does not touch any dependency so that a transient
    dependency outage does not cause the orchestrator to restart the API.
    """
    return {"status": "healthy", "service": "redteam-framework"}


@router.get("/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """Readiness probe: check every dependency the deployment actually uses.

    Only the database is mandatory. Redis, ChromaDB and S3/MinIO are optional
    depending on the deployment (local evaluation mode does not need them), so
    they are reported but do not block readiness unless they are configured.
    """
    checks: dict[str, bool] = {}
    required: dict[str, bool] = {}

    # --- database (mandatory) ---
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception:
        checks["database"] = False
    required["database"] = checks["database"]

    # --- redis (required when a Celery worker runs the evaluations) ---
    if settings.CELERY_BROKER_URL:
        try:
            client = redis.from_url(settings.REDIS_URL)
            await asyncio.to_thread(client.ping)
            checks["redis"] = True
        except Exception:
            checks["redis"] = False
        # With CELERY_TASK_ALWAYS_EAGER the API runs evaluations itself and Redis is not used.
        if not settings.CELERY_TASK_ALWAYS_EAGER:
            required["redis"] = checks["redis"]

    # --- chromadb (optional: only when a vector store is configured) ---
    if settings.CHROMA_HOST:
        try:
            client = chromadb.HttpClient(host=settings.CHROMA_HOST, port=settings.CHROMA_PORT)
            await asyncio.to_thread(client.heartbeat)
            checks["chromadb"] = True
        except Exception:
            checks["chromadb"] = False

    # --- s3 / minio (optional: only when the S3 storage backend is selected) ---
    if settings.STORAGE_BACKEND == "s3":
        try:
            client = boto3.client("s3", endpoint_url=settings.S3_ENDPOINT_URL or None)
            await asyncio.to_thread(client.head_bucket, Bucket=settings.S3_BUCKET)
            checks["minio"] = True
        except Exception:
            checks["minio"] = False

    all_ready = all(required.values())
    return {"ready": all_ready, "checks": checks, "required": required}


@router.get("/metrics")
async def metrics(
    current_user: TokenData = Depends(require_role(["admin"])),
):
    from prometheus_client import generate_latest

    return Response(content=generate_latest(), media_type="text/plain")
