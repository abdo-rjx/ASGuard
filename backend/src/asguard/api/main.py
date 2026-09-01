"""FastAPI application factory."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from asguard.api import (
    routes_applications,
    routes_dashboard,
    routes_health,
    routes_policies,
    routes_proxy,
    routes_settings,
    routes_testing,
)
from asguard.app.seed import seed_database
from asguard.app.state import AppState
from asguard.config import Settings, get_settings
from asguard.demo.mock_ai import router as demo_router
from asguard.gateway.provider import OpenAICompatibleProvider
from asguard.gateway.ratelimit import RateLimiter
from asguard.gateway.service import ProxyService
from asguard.input_guard.pipeline import InputGuard
from asguard.logging_setup import setup_logging
from asguard.output_guard.pipeline import OutputGuard
from asguard.persistence.database import create_engine, create_session_factory, init_db
from asguard.policy.engine import PolicyEngine
from asguard.app.state import AppState

logger = logging.getLogger("asguard")


def _find_frontend_dist() -> Path | None:
    """Locate the built React dashboard (dev tree or installed-package layout)."""
    override = os.environ.get("ASGUARD_FRONTEND_DIR")
    if override:
        candidate = Path(override)
        if candidate.exists():
            return candidate
    candidates = [
        Path.cwd() / "frontend" / "dist",
        Path("/app/frontend/dist"),
        Path(__file__).resolve().parents[4] / "frontend" / "dist",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def create_app(settings: Settings | None = None, provider_factory=None) -> FastAPI:
    settings = settings or get_settings()
    setup_logging(settings.log_level)

    def _default_provider_factory(application):
        return OpenAICompatibleProvider(
            base_url=application.upstream_url,
            api_key=getattr(application, "upstream_api_key", None),
        )

    _provider_factory = provider_factory or _default_provider_factory

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        engine = create_engine(settings)
        session_factory = create_session_factory(engine)
        await init_db(engine)  # dev/test convenience; prod uses Alembic (see docs/deployment.md)
        await seed_database(session_factory, settings)

        policy_engine = PolicyEngine()
        state = AppState(
            engine=engine,
            session_factory=session_factory,
            policy_engine=policy_engine,
            input_guard=InputGuard(
                policy_engine=policy_engine,
                detector_failure_mode=settings.detector_failure_mode,
            ),
            output_guard=OutputGuard(
                policy_engine=policy_engine,
                detector_failure_mode=settings.detector_failure_mode,
            ),
            proxy_service=None,  # type: ignore[arg-type]
            rate_limiter=RateLimiter(),
        )
        state.proxy_service = ProxyService(
            input_guard=state.input_guard,
            output_guard=state.output_guard,
            provider_factory=_provider_factory,
            rate_limiter=state.rate_limiter,
        )
        await state.reload_policies()
        stored = {}
        async with session_factory() as db:
            from asguard.persistence import repository as repo

            stored = await repo.get_settings_doc(db)
        state.apply_settings(stored)
        app.state.asguard = state
        logger.info("asguard started environment=%s", settings.environment)
        yield
        await engine.dispose()

    app = FastAPI(
        title="ASGuard",
        description="Bidirectional AI Security Firewall Middleware",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )

    # Desktop app (Tauri webview) and the local vite dev server call the API
    # from other origins; the dashboard itself stays same-origin.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "tauri://localhost",
            "http://tauri.localhost",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(routes_health.router)
    app.include_router(routes_proxy.router)
    app.include_router(routes_dashboard.router)
    app.include_router(routes_policies.router)
    app.include_router(routes_applications.router)
    app.include_router(routes_testing.router)
    app.include_router(routes_settings.router)

    # Demo/mock upstream AI (local demo mode — no external API keys needed).
    app.include_router(demo_router)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        """Fail safe: never leak stack traces or internals to clients."""
        logger.exception("unhandled error on %s", request.url.path)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "type": "asguard_error",
                    "code": "internal_error",
                    "message": "An internal error occurred.",
                }
            },
        )

    _mount_frontend(app)
    return app


def _mount_frontend(app: FastAPI) -> None:
    """Serve the built dashboard (SPA) when the frontend dist exists."""
    frontend_dist = _find_frontend_dist()
    if frontend_dist is None:
        logger.warning("frontend dist not found — dashboard will not be served")
        return
    assets = frontend_dist / "assets"
    if assets.exists():
        app.mount("/assets", StaticFiles(directory=str(assets)), name="assets")

    index_file = frontend_dist / "index.html"

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str):
        candidate = frontend_dist / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(index_file)


# Module-level app instance for `uvicorn asguard.api.main:app`.
app = create_app()
