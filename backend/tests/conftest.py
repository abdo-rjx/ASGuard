"""Shared pytest fixtures."""

from __future__ import annotations

import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fastapi import FastAPI

from asguard.app.state import AppState
from asguard.config import Settings
from asguard.demo.mock_ai import router as demo_router
from asguard.gateway.provider import OpenAICompatibleProvider
from asguard.api.main import create_app


@pytest.fixture()
def settings(tmp_path) -> Settings:
    return Settings(
        database_url=f"sqlite+aiosqlite:///{tmp_path}/asguard_test.db",
        seed_demo_data=True,
        demo_upstream_url="http://demo-upstream/demo/upstream/v1",
        environment="test",
    )


@pytest.fixture()
def demo_upstream_transport() -> httpx.ASGITransport:
    """An in-process ASGI transport for the demo/mock upstream AI."""
    mock_app = FastAPI()
    mock_app.include_router(demo_router)
    return httpx.ASGITransport(app=mock_app)


@pytest.fixture()
async def app(settings: Settings, demo_upstream_transport: httpx.ASGITransport) -> FastAPI:
    def factory(application_row):
        return OpenAICompatibleProvider(
            base_url=settings.demo_upstream_url,
            transport=demo_upstream_transport,
        )

    return create_app(settings, provider_factory=factory)


@pytest.fixture()
async def client(app: FastAPI) -> httpx.AsyncClient:
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
            yield c
