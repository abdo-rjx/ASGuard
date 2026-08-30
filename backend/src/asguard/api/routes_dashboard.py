"""Dashboard APIs: metrics, timeseries, security events."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from asguard.api.deps import get_app_state, get_db_session
from asguard.app.state import AppState
from asguard.persistence import repository as repo

router = APIRouter(prefix="/api")


def _event_dict(event, detections=None) -> dict:
    data = {
        "id": event.id,
        "request_id": event.request_id,
        "application_id": event.application_id,
        "application_name": event.application_name,
        "direction": event.direction,
        "decision": event.decision,
        "risk_score": event.risk_score,
        "threat_types": event.threat_types,
        "policy_triggered": event.policy_triggered,
        "stages": event.stage_trace,
        "input_latency_ms": event.input_latency_ms,
        "output_latency_ms": event.output_latency_ms,
        "upstream_latency_ms": event.upstream_latency_ms,
        "total_latency_ms": event.total_latency_ms,
        "upstream_status": event.upstream_status,
        "error_code": event.error_code,
        "content_preview": event.content_preview,
        "created_at": event.created_at.isoformat(),
    }
    if detections is not None:
        data["detections"] = [
            {
                "detector": d.detector,
                "direction": d.direction,
                "category": d.category,
                "detected": d.detected,
                "confidence": d.confidence,
                "signals": d.signals,
                "latency_ms": d.latency_ms,
            }
            for d in detections
        ]
    return data


@router.get("/dashboard/metrics")
async def metrics(
    window_hours: int = Query(24, ge=1, le=720),
    state: AppState = Depends(get_app_state),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    data = await repo.dashboard_metrics(db, window_hours=window_hours)
    return data


@router.get("/dashboard/timeseries")
async def timeseries(
    hours: int = Query(24, ge=1, le=168),
    db: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    return await repo.timeseries(db, hours=hours)


@router.get("/events")
async def events(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    direction: str | None = None,
    decision: str | None = None,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    rows, total = await repo.list_events(db, limit=limit, offset=offset,
                                         direction=direction, decision=decision)
    return {"total": total, "events": [_event_dict(e) for e in rows]}


@router.get("/events/{event_id}")
async def event_detail(
    event_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    event = await repo.get_event(db, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="event not found")
    detections = await repo.event_detections(db, event_id)
    return _event_dict(event, detections)
