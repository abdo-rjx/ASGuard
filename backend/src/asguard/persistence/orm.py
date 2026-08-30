"""SQLAlchemy ORM models for ASGuard's own metadata."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _uuid() -> str:
    return uuid.uuid4().hex


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Application(Base):
    """A protected AI application (upstream configuration)."""

    __tablename__ = "applications"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    upstream_url: Mapped[str] = mapped_column(String(500))
    # Stored but NEVER returned by the API (only has_upstream_api_key flag).
    upstream_api_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    auth_type: Mapped[str] = mapped_column(String(30), default="bearer")
    client_api_key: Mapped[str] = mapped_column(String(128), unique=True, default=_uuid)
    policy_profile: Mapped[str] = mapped_column(String(100), default="default")
    timeout_ms: Mapped[int] = mapped_column(Integer, default=60000)
    rate_limit_rpm: Mapped[int] = mapped_column(Integer, default=120)
    # metadata (default) | content_preview — full content logging is not supported.
    logging_mode: Mapped[str] = mapped_column(String(30), default="metadata")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Policy(Base):
    """A single deterministic policy rule (with version history)."""

    __tablename__ = "policies"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    direction: Mapped[str] = mapped_column(String(10))  # input | output
    category: Mapped[str] = mapped_column(String(50))
    action: Mapped[str] = mapped_column(String(20))
    threshold: Mapped[int] = mapped_column(Integer, default=60)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    versions: Mapped[list[PolicyVersion]] = relationship(
        back_populates="policy", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("direction", "category", name="uq_policies_direction_category"),
    )


class PolicyVersion(Base):
    __tablename__ = "policy_versions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    policy_id: Mapped[str] = mapped_column(ForeignKey("policies.id", ondelete="CASCADE"))
    action: Mapped[str] = mapped_column(String(20))
    threshold: Mapped[int] = mapped_column(Integer)
    enabled: Mapped[bool] = mapped_column(Boolean)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    changed_by: Mapped[str] = mapped_column(String(100), default="system")
    reason: Mapped[str] = mapped_column(Text, default="")

    policy: Mapped[Policy] = relationship(back_populates="versions")


class SecurityEvent(Base):
    """One completed security transaction (input or full proxy transaction)."""

    __tablename__ = "security_events"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    request_id: Mapped[str] = mapped_column(String(64), index=True)
    application_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    application_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    direction: Mapped[str] = mapped_column(String(10), index=True)
    decision: Mapped[str] = mapped_column(String(20), index=True)
    risk_score: Mapped[int] = mapped_column(Integer, index=True)
    threat_types: Mapped[list] = mapped_column(JSON, default=list)
    policy_triggered: Mapped[list] = mapped_column(JSON, default=list)
    stage_trace: Mapped[list] = mapped_column(JSON, default=list)
    input_latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    output_latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    upstream_latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    detector_latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    total_latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    upstream_status: Mapped[str] = mapped_column(String(30), default="skipped")
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Only populated when the application's logging_mode explicitly allows it.
    content_preview: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)

    detections: Mapped[list[DetectionResult]] = relationship(
        back_populates="event", cascade="all, delete-orphan"
    )


class DetectionResult(Base):
    """Per-detector evidence attached to a security event."""

    __tablename__ = "detection_results"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    event_id: Mapped[str] = mapped_column(ForeignKey("security_events.id", ondelete="CASCADE"), index=True)
    detector: Mapped[str] = mapped_column(String(100))
    direction: Mapped[str] = mapped_column(String(10))
    category: Mapped[str] = mapped_column(String(50))
    detected: Mapped[bool] = mapped_column(Boolean)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    signals: Mapped[list] = mapped_column(JSON, default=list)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)

    event: Mapped[SecurityEvent] = relationship(back_populates="detections")


class TestRun(Base):
    """A run of the built-in security test suite."""

    __tablename__ = "test_runs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total: Mapped[int] = mapped_column(Integer, default=0)
    passed: Mapped[int] = mapped_column(Integer, default=0)
    failed: Mapped[int] = mapped_column(Integer, default=0)
    results: Mapped[list] = mapped_column(JSON, default=list)


class AppSetting(Base):
    """Global settings, stored as a single JSON document (id='global')."""

    __tablename__ = "app_settings"

    id: Mapped[str] = mapped_column(String(20), primary_key=True, default="global")
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class AuditLog(Base):
    """Audit trail for configuration changes (policies, applications, settings)."""

    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    actor: Mapped[str] = mapped_column(String(100), default="dashboard")
    action: Mapped[str] = mapped_column(String(100))
    entity: Mapped[str] = mapped_column(String(100))
    entity_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
