"""Repositories: typed access to ASGuard's own metadata store."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import Integer, case, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from asguard.persistence.orm import (
    AppSetting,
    Application,
    AuditLog,
    DetectionResult,
    Policy,
    PolicyVersion,
    SecurityEvent,
    TestRun,
)


# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------

async def get_application_by_api_key(db: AsyncSession, api_key: str) -> Application | None:
    result = await db.execute(select(Application).where(Application.client_api_key == api_key))
    return result.scalar_one_or_none()


async def get_application(db: AsyncSession, app_id: str) -> Application | None:
    return await db.get(Application, app_id)


async def list_applications(db: AsyncSession) -> list[Application]:
    result = await db.execute(select(Application).order_by(Application.created_at))
    return list(result.scalars().all())


async def create_application(db: AsyncSession, **fields) -> Application:
    app = Application(**fields)
    db.add(app)
    await db.commit()
    await db.refresh(app)
    return app


async def update_application(db: AsyncSession, app: Application, **fields) -> Application:
    for key, value in fields.items():
        if value is not None:
            setattr(app, key, value)
    await db.commit()
    await db.refresh(app)
    return app


async def delete_application(db: AsyncSession, app: Application) -> None:
    await db.delete(app)
    await db.commit()


async def touch_application(db: AsyncSession, app_id: str) -> None:
    app = await db.get(Application, app_id)
    if app:
        app.last_activity_at = datetime.now(timezone.utc)
        await db.commit()


# ---------------------------------------------------------------------------
# Policies
# ---------------------------------------------------------------------------

async def list_policies(db: AsyncSession) -> list[Policy]:
    result = await db.execute(select(Policy).order_by(Policy.direction, Policy.category))
    return list(result.scalars().all())


async def get_policy(db: AsyncSession, policy_id: str) -> Policy | None:
    return await db.get(Policy, policy_id)


async def upsert_policy(db: AsyncSession, rule, changed_by: str = "dashboard", reason: str = "") -> Policy:
    """Create or update the policy for (direction, category) and version it."""
    result = await db.execute(
        select(Policy).where(Policy.direction == rule.direction, Policy.category == rule.category)
    )
    policy = result.scalar_one_or_none()
    if policy is None:
        policy = Policy(
            direction=rule.direction,
            category=rule.category,
            action=rule.action,
            threshold=rule.threshold,
            enabled=rule.enabled,
        )
        db.add(policy)
        await db.flush()
    else:
        policy.action = rule.action
        policy.threshold = rule.threshold
        policy.enabled = rule.enabled

    db.add(
        PolicyVersion(
            policy_id=policy.id,
            action=rule.action,
            threshold=rule.threshold,
            enabled=rule.enabled,
            changed_by=changed_by,
            reason=reason,
        )
    )
    await db.commit()
    await db.refresh(policy)
    return policy


async def list_policy_versions(db: AsyncSession, policy_id: str) -> list[PolicyVersion]:
    result = await db.execute(
        select(PolicyVersion)
        .where(PolicyVersion.policy_id == policy_id)
        .order_by(PolicyVersion.changed_at.desc())
    )
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Security events
# ---------------------------------------------------------------------------

async def record_event(db: AsyncSession, event) -> SecurityEvent:
    """Persist a SecurityEvent (pydantic) with its detection results."""
    row = SecurityEvent(
        id=event.event_id,
        request_id=event.request_id,
        application_id=event.application_id,
        application_name=event.application_name,
        direction=event.direction.value,
        decision=event.decision.value,
        risk_score=event.risk_score,
        threat_types=[t.value for t in event.threat_types],
        policy_triggered=event.policy_triggered,
        stage_trace=[s.model_dump(mode="json") for s in event.stages],
        input_latency_ms=event.input_latency_ms,
        output_latency_ms=event.output_latency_ms,
        upstream_latency_ms=event.upstream_latency_ms,
        detector_latency_ms=sum(d.latency_ms for d in event.detections),
        total_latency_ms=event.total_latency_ms,
        upstream_status=event.upstream_status,
        error_code=event.error_code,
        content_preview=event.content_preview,
    )
    for d in event.detections:
        db.add(
            DetectionResult(
                event_id=row.id,
                detector=d.detector,
                direction=event.direction.value,
                category=d.category.value,
                detected=d.detected,
                confidence=d.confidence,
                signals=d.signals,
                latency_ms=d.latency_ms,
            )
        )
    db.add(row)
    await db.commit()
    return row


async def get_event(db: AsyncSession, event_id: str) -> SecurityEvent | None:
    result = await db.execute(select(SecurityEvent).where(SecurityEvent.id == event_id))
    return result.scalar_one_or_none()


async def list_events(
    db: AsyncSession,
    limit: int = 50,
    offset: int = 0,
    direction: str | None = None,
    decision: str | None = None,
) -> tuple[list[SecurityEvent], int]:
    query = select(SecurityEvent).order_by(SecurityEvent.created_at.desc())
    count_query = select(func.count()).select_from(SecurityEvent)
    if direction:
        query = query.where(SecurityEvent.direction == direction)
        count_query = count_query.where(SecurityEvent.direction == direction)
    if decision:
        query = query.where(SecurityEvent.decision == decision)
        count_query = count_query.where(SecurityEvent.decision == decision)
    result = await db.execute(query.offset(offset).limit(min(limit, 200)))
    total = (await db.execute(count_query)).scalar() or 0
    return list(result.scalars().all()), int(total)


async def event_detections(db: AsyncSession, event_id: str) -> list[DetectionResult]:
    result = await db.execute(select(DetectionResult).where(DetectionResult.event_id == event_id))
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def _event_summary(e: SecurityEvent) -> dict:
    return {
        "id": e.id,
        "request_id": e.request_id,
        "direction": e.direction,
        "decision": e.decision,
        "risk_score": e.risk_score,
        "threat_types": e.threat_types,
        "application_name": e.application_name,
        "created_at": e.created_at.isoformat(),
        "total_latency_ms": e.total_latency_ms,
    }


async def dashboard_metrics(db: AsyncSession, window_hours: int = 24) -> dict:
    since = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    base = (
        select(
            func.count().label("requests"),
            func.sum(case((SecurityEvent.decision == "ALLOW", 1), else_=0)).label("allowed"),
            func.sum(case((SecurityEvent.decision == "BLOCK", 1), else_=0)).label("blocked"),
            func.sum(case((SecurityEvent.decision == "SANITIZE", 1), else_=0)).label("sanitized"),
            func.sum(case((SecurityEvent.decision == "REVIEW", 1), else_=0)).label("reviewed"),
            func.avg(SecurityEvent.risk_score).label("avg_risk"),
            func.avg(SecurityEvent.total_latency_ms).label("avg_latency"),
        )
        .where(SecurityEvent.created_at >= since)
    )
    row = (await db.execute(base)).one()

    threats = (
        await db.execute(
            select(DetectionResult.category, func.count())
            .join(SecurityEvent, DetectionResult.event_id == SecurityEvent.id)
            .where(DetectionResult.detected.is_(True), SecurityEvent.created_at >= since)
            .group_by(DetectionResult.category)
        )
    ).all()

    recent = (
        (await db.execute(select(SecurityEvent).order_by(SecurityEvent.created_at.desc()).limit(10)))
        .scalars()
        .all()
    )

    return {
        "window_hours": window_hours,
        "requests": int(row.requests or 0),
        "allowed": int(row.allowed or 0),
        "blocked": int(row.blocked or 0),
        "sanitized": int(row.sanitized or 0),
        "reviewed": int(row.reviewed or 0),
        "threats_detected": sum(int(c) for _cat, c in threats),
        "avg_risk": round(float(row.avg_risk or 0), 1),
        "avg_latency_ms": round(float(row.avg_latency or 0), 1),
        "threats_by_category": {cat: int(c) for cat, c in threats},
        "recent_events": [_event_summary(e) for e in recent],
    }


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


async def timeseries(db: AsyncSession, hours: int = 24) -> list[dict]:
    """Hourly allowed/blocked/sanitized counts for charts."""
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    events = (
        (await db.execute(select(SecurityEvent).where(SecurityEvent.created_at >= since)))
        .scalars()
        .all()
    )
    buckets: dict[str, dict] = {}
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    for i in range(hours, 0, -1):
        key = (now - timedelta(hours=i - 1)).isoformat(timespec="seconds")
        buckets[key] = {"hour": key, "allowed": 0, "blocked": 0, "sanitized": 0, "reviewed": 0}
    for e in events:
        key = _as_utc(e.created_at).replace(minute=0, second=0, microsecond=0).isoformat(timespec="seconds")
        bucket = buckets.get(key)
        if bucket is None:
            continue
        if e.decision == "ALLOW":
            bucket["allowed"] += 1
        elif e.decision == "BLOCK":
            bucket["blocked"] += 1
        elif e.decision == "SANITIZE":
            bucket["sanitized"] += 1
        elif e.decision == "REVIEW":
            bucket["reviewed"] += 1
    return list(buckets.values())


# ---------------------------------------------------------------------------
# Test runs
# ---------------------------------------------------------------------------

async def save_test_run(db: AsyncSession, run: TestRun) -> TestRun:
    db.add(run)
    await db.commit()
    await db.refresh(run)
    return run


async def latest_test_runs(db: AsyncSession, limit: int = 10) -> list[TestRun]:
    result = await db.execute(select(TestRun).order_by(TestRun.started_at.desc()).limit(limit))
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Settings + audit
# ---------------------------------------------------------------------------

async def get_settings_doc(db: AsyncSession) -> dict:
    row = await db.get(AppSetting, "global")
    return row.data if row else {}


async def put_settings_doc(db: AsyncSession, data: dict) -> dict:
    row = await db.get(AppSetting, "global")
    if row is None:
        row = AppSetting(id="global", data=data)
        db.add(row)
    else:
        row.data = data
    await db.commit()
    return data


async def add_audit(
    db: AsyncSession,
    action: str,
    entity: str,
    entity_id: str | None = None,
    actor: str = "dashboard",
    detail: dict | None = None,
) -> None:
    db.add(AuditLog(action=action, entity=entity, entity_id=entity_id, actor=actor, detail=detail or {}))
    await db.commit()


async def list_audit(db: AsyncSession, limit: int = 50) -> list[AuditLog]:
    result = await db.execute(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit))
    return list(result.scalars().all())


async def clear_events(db: AsyncSession) -> int:
    """Delete all security events (used by explicit reset endpoints)."""
    await db.execute(delete(DetectionResult))
    await db.execute(delete(SecurityEvent))
    await db.commit()
    return 0
