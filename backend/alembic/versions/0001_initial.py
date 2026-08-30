"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-30
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "applications",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("name", sa.String(200), unique=True, nullable=False),
        sa.Column("upstream_url", sa.String(500), nullable=False),
        sa.Column("upstream_api_key", sa.String(500), nullable=True),
        sa.Column("auth_type", sa.String(30), nullable=False, server_default="bearer"),
        sa.Column("client_api_key", sa.String(128), unique=True, nullable=False),
        sa.Column("policy_profile", sa.String(100), nullable=False, server_default="default"),
        sa.Column("timeout_ms", sa.Integer(), nullable=False, server_default="60000"),
        sa.Column("rate_limit_rpm", sa.Integer(), nullable=False, server_default="120"),
        sa.Column("logging_mode", sa.String(30), nullable=False, server_default="metadata"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "policies",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("threshold", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("direction", "category", name="uq_policies_direction_category"),
    )
    op.create_table(
        "policy_versions",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("policy_id", sa.String(32), sa.ForeignKey("policies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("threshold", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("changed_by", sa.String(100), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
    )
    op.create_table(
        "security_events",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("request_id", sa.String(64), nullable=False, index=True),
        sa.Column("application_id", sa.String(32), nullable=True, index=True),
        sa.Column("application_name", sa.String(200), nullable=True),
        sa.Column("direction", sa.String(10), nullable=False, index=True),
        sa.Column("decision", sa.String(20), nullable=False, index=True),
        sa.Column("risk_score", sa.Integer(), nullable=False, index=True),
        sa.Column("threat_types", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("policy_triggered", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("stage_trace", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("input_latency_ms", sa.Float(), nullable=False, server_default="0"),
        sa.Column("output_latency_ms", sa.Float(), nullable=False, server_default="0"),
        sa.Column("upstream_latency_ms", sa.Float(), nullable=False, server_default="0"),
        sa.Column("detector_latency_ms", sa.Float(), nullable=False, server_default="0"),
        sa.Column("total_latency_ms", sa.Float(), nullable=False, server_default="0"),
        sa.Column("upstream_status", sa.String(30), nullable=False, server_default="skipped"),
        sa.Column("error_code", sa.String(100), nullable=True),
        sa.Column("content_preview", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, index=True),
    )
    op.create_table(
        "detection_results",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("event_id", sa.String(32), sa.ForeignKey("security_events.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("detector", sa.String(100), nullable=False),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("detected", sa.Boolean(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("signals", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("latency_ms", sa.Float(), nullable=False, server_default="0"),
    )
    op.create_table(
        "test_runs",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("passed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("results", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.create_table(
        "app_settings",
        sa.Column("id", sa.String(20), primary_key=True, server_default="global"),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "audit_log",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("actor", sa.String(100), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity", sa.String(100), nullable=False),
        sa.Column("entity_id", sa.String(64), nullable=True),
        sa.Column("detail", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    for table in (
        "audit_log",
        "app_settings",
        "test_runs",
        "detection_results",
        "security_events",
        "policy_versions",
        "policies",
        "applications",
    ):
        op.drop_table(table)