"""Health and readiness probes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from asguard.api.deps import get_app_state, get_db_session
from asguard.app.state import AppState

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "asguard"}


@router.get("/ready")
async def ready(
    state: AppState = Depends(get_app_state),
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    import json

    payload = {"status": "ready", "database": "ok"}
    status = 200
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        payload = {"status": "not_ready", "database": "unavailable"}
        status = 503
    return Response(
        content=json.dumps(payload),
        status_code=status,
        media_type="application/json",
    )
