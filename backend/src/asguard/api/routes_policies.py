"""Policy management APIs."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from asguard.api.deps import get_app_state, get_db_session
from asguard.app.state import AppState
from asguard.audit import record_action
from asguard.persistence import repository as repo
from asguard.policy.engine import ALLOWED_ACTIONS
from asguard.security_models.enums import Direction, PolicyAction, ThreatCategory
from asguard.security_models.models import PolicyRule

router = APIRouter(prefix="/api/policies")


class PolicyUpdate(BaseModel):
    action: str = Field(..., description="ALLOW | BLOCK | REVIEW | REDACT | SANITIZE")
    threshold: int = Field(..., ge=0, le=100)
    enabled: bool = True
    reason: str = Field("", max_length=500)


def _policy_dict(p) -> dict:
    return {
        "id": p.id,
        "direction": p.direction,
        "category": p.category,
        "action": p.action,
        "threshold": p.threshold,
        "enabled": p.enabled,
        "updated_at": p.updated_at.isoformat(),
        "allowed_actions": sorted(
            a.value for a in ALLOWED_ACTIONS.get(Direction(p.direction), set())
        ),
    }


@router.get("")
async def list_policies(db: AsyncSession = Depends(get_db_session)) -> dict:
    policies = await repo.list_policies(db)
    return {"policies": [_policy_dict(p) for p in policies]}


@router.get("/categories")
async def categories() -> dict:
    """Valid categories/actions per direction (for UI validation)."""
    return {
        "input": {
            "categories": [
                c.value
                for c in ThreatCategory
                if c.value
                in ("prompt_injection", "jailbreak", "system_prompt_extraction", "obfuscation", "suspicious_intent")
            ],
            "actions": [a.value for a in ALLOWED_ACTIONS[Direction.INPUT]],
        },
        "output": {
            "categories": [
                c.value
                for c in ThreatCategory
                if c.value in ("secret", "pii", "financial", "confidential")
            ],
            "actions": [a.value for a in ALLOWED_ACTIONS[Direction.OUTPUT]],
        },
    }


@router.put("/{policy_id}")
async def update_policy(
    policy_id: str,
    update: PolicyUpdate,
    state: AppState = Depends(get_app_state),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    policy = await repo.get_policy(db, policy_id)
    if policy is None:
        raise HTTPException(status_code=404, detail="policy not found")

    direction = Direction(policy.direction)
    try:
        action = PolicyAction(update.action)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"invalid action '{update.action}'")

    rule = PolicyRule(
        direction=direction,
        category=ThreatCategory(policy.category),
        action=action,
        threshold=update.threshold,
        enabled=update.enabled,
    )
    errors = state.policy_engine.validate_rule(rule)
    if errors:
        raise HTTPException(status_code=422, detail="; ".join(errors))

    saved = await repo.upsert_policy(db, rule, changed_by="dashboard", reason=update.reason)
    # Rebuild the live engine rules from the persisted set.
    await state.reload_policies()
    await record_action(
        db,
        action="policy.update",
        entity="policy",
        entity_id=policy_id,
        detail={
            "direction": policy.direction,
            "category": policy.category,
            "action": update.action,
            "threshold": update.threshold,
            "enabled": update.enabled,
        },
    )
    return _policy_dict(saved)
