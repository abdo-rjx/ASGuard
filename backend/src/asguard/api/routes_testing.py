"""Security testing APIs: run the shipped YAML corpus against the live engine."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from asguard.api.deps import get_app_state, get_db_session
from asguard.app.state import AppState
from asguard.persistence import repository as repo
from asguard.persistence.orm import TestRun
from asguard.testing.framework import default_cases, run_cases

router = APIRouter(prefix="/api/testing")


@router.get("/cases")
async def list_cases() -> dict:
    cases = default_cases()
    return {
        "total": len(cases),
        "cases": [
            {
                "id": c.id,
                "direction": c.direction,
                "category": c.category,
                "description": c.description,
                "expected_decision": c.expected_decision,
                "minimum_risk": c.minimum_risk,
            }
            for c in cases
        ],
    }


@router.post("/run")
async def run_tests(
    state: AppState = Depends(get_app_state),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    report = run_cases(default_cases(), state.input_guard, state.output_guard)
    run = TestRun(
        id=uuid.uuid4().hex,
        started_at=datetime.now(timezone.utc),
        finished_at=datetime.now(timezone.utc),
        total=report["total"],
        passed=report["passed"],
        failed=report["failed"],
        results=report["results"],
    )
    await repo.save_test_run(db, run)
    return {
        "run_id": run.id,
        "total": report["total"],
        "passed": report["passed"],
        "failed": report["failed"],
        "results": report["results"],
    }


@router.get("/results")
async def results(
    limit: int = 10,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    runs = await repo.latest_test_runs(db, limit=min(limit, 50))
    return {
        "runs": [
            {
                "id": r.id,
                "started_at": r.started_at.isoformat(),
                "total": r.total,
                "passed": r.passed,
                "failed": r.failed,
                "results": r.results,
            }
            for r in runs
        ]
    }
