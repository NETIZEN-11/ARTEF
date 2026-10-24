from typing import Any
from uuid import UUID

from sqlalchemy import String
from sqlalchemy.types import TypeDecorator


class UUIDString(TypeDecorator):
    """A UUID stored as VARCHAR(36).

    Ids are strings in the database, but the API layer passes uuid.UUID objects. Without
    this conversion a UUID parameter never matches the stored string on SQLite and is a
    type error on asyncpg, so filters such as `TestCase.suite_id == suite_id` silently
    returned nothing.
    """

    impl = String(36)
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        return str(value) if isinstance(value, UUID) else value
