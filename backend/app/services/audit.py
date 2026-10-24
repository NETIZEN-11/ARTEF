from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


async def record_audit(
    session: AsyncSession,
    user_id: str | None,
    action: str,
    resource_type: str,
    resource_id: Any,
    details: dict[str, Any] | None = None,
) -> AuditLog:
    """Append an audit record in the caller's transaction (committed with the change it
    describes, so the change and its audit trail succeed or fail together)."""
    entry = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        details=details or {},
    )
    session.add(entry)
    await session.flush()
    return entry
