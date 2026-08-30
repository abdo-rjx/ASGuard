"""Database seeding: default policies, default settings, demo application."""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from asguard.app.settings_service import DEFAULT_SETTINGS, merge_defaults
from asguard.config import Settings
from asguard.persistence import repository as repo
from asguard.policy.engine import ALL_POLICY_DEFAULTS

logger = logging.getLogger(__name__)


async def seed_database(session_factory: async_sessionmaker[AsyncSession], settings: Settings) -> None:
    """Idempotent seeding of default policies, settings and demo app."""
    async with session_factory() as db:
        # 1. Default policy set (only insert missing rules)
        existing = await repo.list_policies(db)
        existing_pairs = {(p.direction, p.category) for p in existing}
        for rule in ALL_POLICY_DEFAULTS:
            if (rule.direction.value, rule.category.value) not in existing_pairs:
                await repo.upsert_policy(
                    db, rule, changed_by="seed", reason="default policy set"
                )
                logger.info("seeded default policy %s/%s", rule.direction.value, rule.category.value)

        # 2. Default settings document
        stored = await repo.get_settings_doc(db)
        if not stored:
            await repo.put_settings_doc(db, dict(DEFAULT_SETTINGS))

        # 3. Demo application pointing at the built-in mock upstream
        if settings.seed_demo_data:
            apps = await repo.list_applications(db)
            names = {a.name for a in apps}
            if "Demo Assistant" not in names:
                await repo.create_application(
                    db,
                    name="Demo Assistant",
                    upstream_url=settings.demo_upstream_url,
                    auth_type="none",
                    policy_profile="default",
                    timeout_ms=30000,
                    rate_limit_rpm=120,
                    logging_mode="metadata",
                )
                logger.info("seeded demo application 'Demo Assistant' -> %s", settings.demo_upstream_url)

        merged = merge_defaults(await repo.get_settings_doc(db))
    return None
