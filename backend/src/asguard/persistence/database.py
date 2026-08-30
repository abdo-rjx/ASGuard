"""ASGuard's own metadata database (async SQLAlchemy).

IMPORTANT: this database stores ASGuard's own metadata only — policies,
applications configuration, security events, test runs, settings. It never
stores enterprise business data and ASGuard holds no credentials for any
enterprise system.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from asguard.config import Settings


def create_engine(settings: Settings) -> AsyncEngine:
    url = settings.database_url
    if url.startswith("sqlite"):
        from sqlalchemy.pool import StaticPool

        kwargs: dict = {"connect_args": {"check_same_thread": False}}
        if ":memory:" in url:
            kwargs["poolclass"] = StaticPool
        return create_async_engine(url, **kwargs)
    return create_async_engine(url, pool_pre_ping=True)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def init_db(engine: AsyncEngine) -> None:
    """Create tables (dev/test convenience; production uses Alembic)."""
    from asguard.persistence.orm import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
