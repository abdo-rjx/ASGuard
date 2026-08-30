"""Core security pipeline interfaces.

Detectors return structured data (``DetectorResult``), the risk engine returns
a ``RiskAssessment``, the policy engine returns the final ``PolicyDecision``.
Detectors provide *evidence only* — the policy engine always has final
authority (spec rule 4).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from asguard.security_models.enums import (
    Decision,
    Direction,
    PolicyAction,
    Severity,
    StageStatus,
    ThreatCategory,
)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DetectionSpan(BaseModel):
    """A concrete substring in the analyzed text that triggered a detector."""

    category: ThreatCategory
    label: str  # e.g. "api_key", "email"
    start: int
    end: int
    # Preview with middle characters masked — never the full sensitive value.
    masked_preview: str = ""


class DetectorResult(BaseModel):
    """Structured output of a single detector."""

    detector: str
    category: ThreatCategory
    detected: bool
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    severity: Severity = Severity.LOW
    signals: list[str] = Field(default_factory=list)
    spans: list[DetectionSpan] = Field(default_factory=list)
    latency_ms: float = 0.0
    error: str | None = None

    @property
    def weighted_score(self) -> float:
        """Confidence scaled by the severity weight, in 0..1."""
        if not self.detected:
            return 0.0
        return min(1.0, self.confidence * self.severity.weight)


class RiskAssessment(BaseModel):
    """Aggregate risk produced by the risk engine."""

    direction: Direction
    score: int = Field(ge=0, le=100)
    level: Severity = Severity.LOW
    contributors: list[str] = Field(default_factory=list)
    rationale: str = ""


class PolicyRule(BaseModel):
    """One deterministic policy rule."""

    direction: Direction
    category: ThreatCategory
    action: PolicyAction
    threshold: int = Field(ge=0, le=100, default=60)
    enabled: bool = True


class PolicyDecision(BaseModel):
    """Final, deterministic decision from the policy engine."""

    decision: Decision
    reason: str
    risk_score: int
    triggered_rules: list[str] = Field(default_factory=list)
    # Rules that requested sanitization-style actions (used by output guard).
    sanitize_categories: list[ThreatCategory] = Field(default_factory=list)
    # Which replacement style to use when sanitizing (SANITIZE vs REDACT).
    replacement_action: PolicyAction = PolicyAction.SANITIZE


class SanitizationResult(BaseModel):
    """Outcome of deterministic sanitization/redaction."""

    sanitized_text: str
    changes: list[dict[str, Any]] = Field(default_factory=list)
    remaining_detections: list[DetectorResult] = Field(default_factory=list)
    verified_clean: bool = True


class PipelineStageTrace(BaseModel):
    """One stage of the transaction lifecycle, for the request inspector."""

    name: str
    status: StageStatus = StageStatus.OK
    latency_ms: float = 0.0
    risk: int | None = None
    decision: Decision | None = None
    detail: str = ""


class SecurityEvent(BaseModel):
    """A completed, auditable security transaction."""

    event_id: str
    request_id: str
    application_id: str | None = None
    application_name: str | None = None
    direction: Direction = Direction.INPUT
    decision: Decision
    risk_score: int
    threat_types: list[ThreatCategory] = Field(default_factory=list)
    policy_triggered: list[str] = Field(default_factory=list)
    detections: list[DetectorResult] = Field(default_factory=list)
    stages: list[PipelineStageTrace] = Field(default_factory=list)
    input_latency_ms: float = 0.0
    output_latency_ms: float = 0.0
    upstream_latency_ms: float = 0.0
    total_latency_ms: float = 0.0
    upstream_status: str = "skipped"
    error_code: str | None = None
    content_preview: str | None = None  # only present when explicitly allowed
    created_at: datetime = Field(default_factory=utcnow)


class TransactionTrace(BaseModel):
    """Full lifecycle of one proxied transaction (request inspector data)."""

    request_id: str
    event_id: str | None = None
    stages: list[PipelineStageTrace] = Field(default_factory=list)
    final_decision: Decision = Decision.ALLOW
    input_risk: int = 0
    output_risk: int = 0
    total_latency_ms: float = 0.0
