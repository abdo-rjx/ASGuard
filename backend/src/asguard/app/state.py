"""Application state shared across API routes."""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from asguard.app.settings_service import merge_defaults
from asguard.gateway.ratelimit import RateLimiter
from asguard.gateway.service import ProxyService
from asguard.input_guard.pipeline import InputGuard
from asguard.output_guard.pipeline import OutputGuard
from asguard.policy.engine import PolicyEngine
from asguard.security_models.enums import Direction, PolicyAction, ThreatCategory
from asguard.security_models.models import PolicyRule


@dataclass
class AppState:
    """Container for long-lived services wired once at startup."""

    engine: AsyncEngine
    session_factory: async_sessionmaker
    policy_engine: PolicyEngine
    input_guard: InputGuard
    output_guard: OutputGuard
    proxy_service: ProxyService
    rate_limiter: RateLimiter
    demo_mode: bool = False
    # runtime knobs mirrored from the settings document
    runtime: dict = field(default_factory=dict)

    async def reload_policies(self) -> None:
        """Rebuild the live policy engine from the persisted policy set."""
        from asguard.persistence import repository as repo
        from asguard.security_models.models import PolicyRule

        async with self.session_factory() as db:
            rows = await repo.list_policies(db)
        rules = [
            PolicyRule(
                direction=Direction(row.direction),
                category=ThreatCategory(row.category),
                action=PolicyAction(row.action),
                threshold=row.threshold,
                enabled=row.enabled,
            )
            for row in rows
        ]
        if rules:
            self.policy_engine.set_rules(rules)
            self.input_guard.policy_engine = self.policy_engine
            self.output_guard.policy_engine = self.policy_engine

    def apply_settings(self, stored: dict) -> None:
        """Apply the merged settings document to runtime behaviour."""
        merged = merge_defaults(stored)
        self.runtime = {
            "log_security_events": merged.get("logging", {}).get("log_security_events", True),
            "detector_failure_mode": merged.get("detection", {}).get("detector_failure_mode", "fail_closed"),
            "upstream_timeout_seconds": merged.get("upstream", {}).get("timeout_seconds", 60),
            "block_threshold": merged.get("security_thresholds", {}).get("block_threshold", 70),
            "review_threshold": merged.get("security_thresholds", {}).get("review_threshold", 40),
        }
        mode = self.runtime["detector_failure_mode"]
        self.input_guard.detector_failure_mode = mode
        self.output_guard.detector_failure_mode = mode

