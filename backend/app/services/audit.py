from typing import Any

from sqlalchemy.orm import Session

from app.models.audit import AuditLog


def add_audit_event(
    db: Session,
    *,
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    actor_user_id: int | None = None,
    metadata: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    """Add a non-PII audit event; callers decide when to commit the transaction."""

    event = AuditLog(
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        actor_user_id=actor_user_id,
        metadata_json=metadata,
        ip_address=ip_address,
    )
    db.add(event)
    return event
