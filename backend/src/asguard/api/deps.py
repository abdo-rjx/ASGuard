"""Shared API dependencies and helpers."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from asguard.app.state import AppState


def get_app_state(request: Request) -> AppState:
    return request.app.state.asguard


async def get_db(state: AppState = Depends(get_app_state)):
    """Yield a database session from the shared session factory."""
    session = state.session_factory()
    try:
        yield session
    finally:
        await session.close()


async def get_db_session(session: AsyncSession = Depends(get_db)) -> AsyncSession:
    return session
