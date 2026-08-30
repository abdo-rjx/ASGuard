"""Audit service — records configuration changes in the audit log.

The audit trail is stored in ASGuard's own metadata database via
``asguard.persistence.repository.add_audit``; this module provides the
application-level helpers used by the API routes.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from asguard.persistence.repository import add_audit, list_audit

__all__ = ["record_action", "recent_actions"]


async def record_action(
    db: AsyncSession,
    action: str,
    entity: str,
    entity_id: str | None = None,
    actor: str = "dashboard",
    detail: dict | None = None,
) -> None:
    await add_audit(db, action=action, entity=entity, entity_id=entity_id, actor=actor, detail=detail)


async def recent_actions(db: AsyncSession, limit: int = 50) -> list:
    return await list_audit(db, limit=limit)
