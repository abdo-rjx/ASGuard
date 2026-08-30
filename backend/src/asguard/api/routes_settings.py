"""Settings + audit APIs."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from asguard.api.deps import get_app_state, get_db_session
from asguard.app.settings_service import merge_defaults, validate_settings
from asguard.app.state import AppState
from asguard.audit import record_action, recent_actions
from asguard.persistence import repository as repo

router = APIRouter(prefix="/api")


@router.get("/settings")
async def get_settings(
    state: AppState = Depends(get_app_state),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    stored = await repo.get_settings_doc(db)
    return merge_defaults(stored)


@router.put("/settings")
async def put_settings(
    data: dict,
    state: AppState = Depends(get_app_state),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    errors = validate_settings(data)
    if errors:
        raise HTTPException(status_code=422, detail="; ".join(errors))
    current = await repo.get_settings_doc(db)
    merged_input = merge_defaults(current)
    for section, values in data.items():
        if isinstance(values, dict) and isinstance(merged_input.get(section), dict):
            merged_input[section].update(values)
        else:
            merged_input[section] = values
    saved = await repo.put_settings_doc(db, merged_input)
    state.apply_settings(saved)
    await record_action(db, action="settings.update", entity="settings",
                        detail={"sections": sorted(data.keys())})
    return merge_defaults(saved)


@router.get("/audit")
async def audit(
    limit: int = 50,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    rows = await recent_actions(db, limit=min(limit, 200))
    return {
        "entries": [
            {
                "id": r.id,
                "actor": r.actor,
                "action": r.action,
                "entity": r.entity,
                "entity_id": r.entity_id,
                "detail": r.detail,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]
    }
