from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.models import Base

settings = get_settings()

_is_sqlite = settings.DATABASE_URL.startswith("sqlite")


def _json_default(obj):
    # JSON columns (evidence, snapshots) contain datetimes; serialise them as ISO strings.
    from datetime import date, datetime

    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def _json_serializer(value) -> str:
    import json

    return json.dumps(value, default=_json_default)


def _engine_options(pooled: bool) -> dict:
    """Engine options for this database. pooled=False gives a NullPool engine for code that
    runs in its own event loop (Celery tasks), where pooled connections must not be shared."""
    from sqlalchemy.pool import NullPool, StaticPool

    if _is_sqlite:
        import sqlite3
        import uuid

        sqlite3.register_adapter(uuid.UUID, lambda u: str(u))

        in_memory = ":memory:" in settings.DATABASE_URL
        return {
            # 30s busy timeout: the API and a worker may write to the same file concurrently.
            "connect_args": {"check_same_thread": False, "timeout": 30},
            # An in-memory database exists only on one connection; a file can use one per session.
            "poolclass": StaticPool if in_memory else NullPool,
            "echo": settings.DEBUG,
            "json_serializer": _json_serializer,
        }
    if not pooled:
        return {"poolclass": NullPool, "echo": settings.DEBUG, "json_serializer": _json_serializer}
    return {
        "json_serializer": _json_serializer,
        "pool_size": settings.DATABASE_POOL_SIZE,
        "max_overflow": settings.DATABASE_MAX_OVERFLOW,
        "pool_timeout": settings.DATABASE_POOL_TIMEOUT,
        "pool_pre_ping": True,
        "echo": settings.DEBUG,
    }


engine = create_async_engine(settings.DATABASE_URL, **_engine_options(pooled=True))

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


def create_task_session_maker():
    """A fresh engine + session factory for one Celery task (one event loop)."""
    task_engine = create_async_engine(settings.DATABASE_URL, **_engine_options(pooled=False))
    return task_engine, async_sessionmaker(
        task_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )


@asynccontextmanager
async def get_async_session():
    """Yield a session, committing on clean exit and rolling back on failure.

    Routes only call ``flush()``; without the commit below the implicit
    transaction is discarded when the session closes and every write is lost.
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def get_session_context():
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    await engine.dispose()
