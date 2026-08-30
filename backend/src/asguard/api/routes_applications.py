"""Application (protected AI) management APIs.

Upstream API keys are write-only: they are stored so ASGuard can authenticate
to the upstream AI, but they are NEVER returned by any endpoint.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from asguard.api.deps import get_db_session
from asguard.audit import record_action
from asguard.persistence import repository as repo

router = APIRouter(prefix="/api/applications")


class ApplicationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    upstream_url: str = Field(..., min_length=1, max_length=500)
    upstream_api_key: str | None = Field(None, max_length=500)
    auth_type: str = Field("bearer", pattern="^(none|bearer)$")
    policy_profile: str = Field("default", max_length=100)
    timeout_ms: int = Field(60000, ge=1000, le=600000)
    rate_limit_rpm: int = Field(120, ge=1, le=100000)
    logging_mode: str = Field("metadata", pattern="^(metadata|content_preview)$")

    @field_validator("upstream_url")
    @classmethod
    def _validate_url(cls, value: str) -> str:
        if not value.startswith(("http://", "https://")):
            raise ValueError("upstream_url must be an http(s) URL")
        return value.rstrip("/")


class ApplicationUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    upstream_url: str | None = Field(None, min_length=1, max_length=500)
    upstream_api_key: str | None = Field(None, max_length=500)
    auth_type: str | None = Field(None, pattern="^(none|bearer)$")
    policy_profile: str | None = Field(None, max_length=100)
    timeout_ms: int | None = Field(None, ge=1000, le=600000)
    rate_limit_rpm: int | None = Field(None, ge=1, le=100000)
    logging_mode: str | None = Field(None, pattern="^(metadata|content_preview)$")
    is_active: bool | None = None

    @field_validator("upstream_url")
    @classmethod
    def _validate_url(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if not value.startswith(("http://", "https://")):
            raise ValueError("upstream_url must be an http(s) URL")
        return value.rstrip("/")


def _app_dict(app, requests: int = 0, avg_risk: float = 0.0) -> dict:
    last_activity = app.last_activity_at.isoformat() if app.last_activity_at else None
    online = False
    if app.is_active and last_activity:
        delta = datetime.now(timezone.utc) - app.last_activity_at
        online = delta.total_seconds() < 300
    return {
        "id": app.id,
        "name": app.name,
        "upstream_url": app.upstream_url,
        "has_upstream_api_key": bool(app.upstream_api_key),
        "auth_type": app.auth_type,
        "policy_profile": app.policy_profile,
        "timeout_ms": app.timeout_ms,
        "rate_limit_rpm": app.rate_limit_rpm,
        "logging_mode": app.logging_mode,
        "is_active": app.is_active,
        "status": "ONLINE" if online else "OFFLINE",
        "created_at": app.created_at.isoformat(),
        "last_activity_at": last_activity,
        "requests": requests,
        "avg_risk": avg_risk,
    }


@router.get("")
async def list_applications(db: AsyncSession = Depends(get_db_session)) -> dict:
    apps = await repo.list_applications(db)
    out = []
    for app in apps:
        stats = await _app_stats(db, app.id)
        out.append(_app_dict(app, **stats))
    return {"applications": out}


async def _app_stats(db: AsyncSession, app_id: str) -> dict:
    from sqlalchemy import func, select

    from asguard.persistence.orm import SecurityEvent

    row = (
        await db.execute(
            select(func.count(), func.avg(SecurityEvent.risk_score))
            .where(SecurityEvent.application_id == app_id)
        )
    ).one()
    return {"requests": int(row[0] or 0), "avg_risk": round(float(row[1] or 0), 1)}


@router.post("")
async def create_application(
    payload: ApplicationCreate,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    apps = await repo.list_applications(db)
    if any(a.name == payload.name for a in apps):
        raise HTTPException(status_code=409, detail="application name already exists")
    app = await repo.create_application(db, **payload.model_dump())
    await record_action(db, action="application.create", entity="application",
                        entity_id=app.id, detail={"name": app.name})
    return _app_dict(app)


@router.put("/{app_id}")
async def update_application(
    app_id: str,
    payload: ApplicationUpdate,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    app = await repo.get_application(db, app_id)
    if app is None:
        raise HTTPException(status_code=404, detail="application not found")
    fields = payload.model_dump(exclude_none=True)
    if "upstream_api_key" in fields and not fields["upstream_api_key"]:
        del fields["upstream_api_key"]  # never clear/blank a key accidentally
    app = await repo.update_application(db, app, **fields)
    await record_action(db, action="application.update", entity="application",
                        entity_id=app_id, detail={"fields": sorted(fields)})
    stats = await _app_stats(db, app_id)
    return _app_dict(app, **stats)


@router.delete("/{app_id}")
async def delete_application(
    app_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    app = await repo.get_application(db, app_id)
    if app is None:
        raise HTTPException(status_code=404, detail="application not found")
    await repo.delete_application(db, app)
    await record_action(db, action="application.delete", entity="application", entity_id=app_id)
    return {"deleted": True}
