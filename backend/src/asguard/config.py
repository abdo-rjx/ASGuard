"""Application configuration.

ASGuard only ever needs credentials for *itself* (its own metadata database and
its own dashboard). It never holds credentials for enterprise databases, RAG
stores, CRMs or other enterprise systems — the existing AI keeps those.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables / .env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Application -------------------------------------------------------
    app_name: str = "ASGuard"
    environment: str = "development"  # development | production
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"

    # --- ASGuard's own metadata database ------------------------------------
    # This is ASGuard's own metadata store (policies, events, applications).
    # It is NOT an enterprise database and contains no business data.
    database_url: str = "postgresql+asyncpg://asguard:asguard_dev@localhost:5432/asguard"

    # --- Demo / seed --------------------------------------------------------
    seed_demo_data: bool = True
    demo_upstream_url: str = "http://localhost:8000/demo/upstream/v1"

    # --- Security defaults ---------------------------------------------------
    # Behaviour when a detector itself fails: fail_closed = treat as unsafe.
    detector_failure_mode: str = "fail_closed"  # fail_closed | fail_open
    # Default maximum risk considered reviewable before blocking (used by UI).
    default_block_threshold: int = 70
    # Whether raw prompt/response content may ever be persisted.
    allow_content_logging: bool = False

    # --- Proxy ---------------------------------------------------------------
    upstream_timeout_seconds: float = 60.0
    max_request_body_bytes: int = 1_000_000


@lru_cache
def get_settings() -> Settings:
    return Settings()
