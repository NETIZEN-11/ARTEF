"""
SQLite compatibility shim for PostgreSQL-specific SQLAlchemy types.
Import this early (before any models) to replace JSONB, ARRAY, UUID.
"""
import json
import os
import sys
import types
from datetime import date, datetime

from sqlalchemy import JSON, String, Text
from sqlalchemy.types import TypeDecorator

try:
    from app.core.config import get_settings
    DATABASE_URL = get_settings().DATABASE_URL
except Exception:
    DATABASE_URL = os.environ.get("DATABASE_URL", "")

IS_SQLITE = DATABASE_URL.startswith("sqlite")


def _datetime_safe_serializer(obj):
    """JSON serializer that converts datetime/date to ISO strings."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


class DatetimeAwareJSON(JSON):
    """JSON column type that can serialize datetime objects."""

    def bind_processor(self, dialect):
        def process(value):
            if value is None:
                return None
            return json.dumps(value, default=_datetime_safe_serializer)
        return process

    def result_processor(self, dialect, coltype):
        def process(value):
            if value is None:
                return None
            if isinstance(value, str):
                return json.loads(value)
            return value
        return process


class ArrayAsJSON(TypeDecorator):
    """Store arrays as JSON strings in SQLite."""
    impl = Text
    cache_ok = True

    def __init__(self, item_type=None, **kw):
        super().__init__(**kw)

    def process_bind_param(self, value, dialect):
        if value is None:
            return "[]"
        return json.dumps(list(value), default=_datetime_safe_serializer)

    def process_result_value(self, value, dialect):
        if value is None:
            return []
        return json.loads(value)


if IS_SQLITE:
    import sqlite3
    import uuid
    sqlite3.register_adapter(uuid.UUID, lambda u: str(u))
    pg_mod = types.ModuleType("sqlalchemy.dialects.postgresql")
    pg_mod.JSONB = DatetimeAwareJSON
    pg_mod.ARRAY = ArrayAsJSON
    pg_mod.UUID = String
    sys.modules["sqlalchemy.dialects.postgresql"] = pg_mod

    import sqlalchemy.sql.sqltypes as _sqltypes
    _orig_json_impl = _sqltypes.JSON.JSONIndexType

    from sqlalchemy import event
    from sqlalchemy.engine import Engine

    @event.listens_for(Engine, "connect")
    def set_sqlite_json_serializer(dbapi_connection, connection_record):
        pass

try:
    import bcrypt
    if not hasattr(bcrypt, "__about__"):
        bcrypt.__about__ = types.SimpleNamespace(__version__="4.0.0")
    if not getattr(bcrypt, "_has_72_patch", False):
        _orig_hashpw = bcrypt.hashpw
        bcrypt.hashpw = lambda p, s: _orig_hashpw(p[:72], s)
        _orig_checkpw = bcrypt.checkpw
        bcrypt.checkpw = lambda p, s: _orig_checkpw(p[:72], s)
        bcrypt._has_72_patch = True
except Exception:
    pass


