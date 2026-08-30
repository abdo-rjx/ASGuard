"""OpenAI-compatible proxy endpoint: POST /v1/chat/completions."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from asguard.api.deps import get_app_state, get_db_session
from asguard.app.state import AppState
from asguard.gateway.provider import OpenAICompatibleProvider
from asguard.gateway.service import extract_user_content
from asguard.logging_setup import log_event
from asguard.persistence import repository as repo

logger = logging.getLogger(__name__)
router = APIRouter()

_MAX_BODY_BYTES = 1_000_000


@router.post("/v1/chat/completions")
async def chat_completions(
    request: Request,
    state: AppState = Depends(get_app_state),
    db: AsyncSession = Depends(get_db_session),
) -> JSONResponse:
    body = await _parse_body(request)
    if isinstance(body, JSONResponse):
        return body

    if body.get("stream"):
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "type": "asguard_error",
                    "code": "streaming_not_supported",
                    "message": (
                        "ASGuard inspects complete responses; streaming is not "
                        "supported in this version. Send \"stream\": false."
                    ),
                }
            },
        )

    application = await _resolve_application(body, request, state, db)
    if application is None:
        return JSONResponse(
            status_code=503,
            content={
                "error": {
                    "type": "asguard_error",
                    "code": "no_application",
                    "message": "No protected application is configured.",
                }
            },
        )

    preview_allowed = getattr(application, "logging_mode", "metadata") == "content_preview"

    outcome = await state.proxy_service.handle_chat_completion(
        payload=body,
        application=application,
        content_preview_allowed=preview_allowed,
    )

    # Persist the audit event + touch the application.
    if outcome.security_event is not None and state.runtime.get("log_security_events", True):
        try:
            await repo.record_event(db, outcome.security_event)
        except Exception:
            log_event(logger, logging.ERROR, "event_persist_failed",
                      request_id=outcome.request_id)
    if application is not None and application.id:
        try:
            await repo.touch_application(db, application.id)
        except Exception:
            pass

    headers = {
        "X-Request-Id": outcome.request_id,
        "X-ASGuard-Decision": outcome.decision.value,
        "X-ASGuard-Risk": str(outcome.risk_score),
    }
    if outcome.security_event is not None:
        headers["X-ASGuard-Event-Id"] = outcome.security_event.event_id

    log_event(
        logger,
        logging.INFO if outcome.decision.value == "ALLOW" else logging.WARNING,
        "proxy_transaction",
        request_id=outcome.request_id,
        decision=outcome.decision.value,
        reason=outcome.reason,
        risk=outcome.risk_score,
        error=outcome.error_code or "-",
    )
    return JSONResponse(status_code=outcome.http_status, content=outcome.response_body, headers=headers)


async def _parse_body(request: Request):
    raw = await request.body()
    if len(raw) > _MAX_BODY_BYTES:
        return JSONResponse(
            status_code=413,
            content={"error": {"type": "asguard_error", "code": "payload_too_large",
                               "message": "Request body exceeds the allowed size."}},
        )
    import json

    try:
        body = json.loads(raw or b"{}")
    except ValueError:
        return JSONResponse(
            status_code=400,
            content={"error": {"type": "asguard_error", "code": "invalid_json",
                               "message": "Request body is not valid JSON."}},
        )
    if not isinstance(body.get("messages"), list) or not body.get("messages"):
        return JSONResponse(
            status_code=400,
            content={"error": {"type": "asguard_error", "code": "invalid_request",
                               "message": "'messages' must be a non-empty array."}},
        )
    return body


async def _resolve_application(body: dict, request: Request, state: AppState, db: AsyncSession):
    """Resolve the target application from the bearer key (fallback: default app).

    This lets an existing OpenAI client switch to ASGuard by only changing its
    base_url: the client's existing Authorization header is accepted and mapped
    to the configured application, or the default application is used.
    """
    auth = request.headers.get("authorization", "")
    api_key = auth.removeprefix("Bearer ").strip() if auth else ""
    if api_key:
        app_row = await repo.get_application_by_api_key(db, api_key)
        if app_row is not None and app_row.is_active:
            return app_row
    # Fallback: first active application (the "default" protected app).
    apps = await repo.list_applications(db)
    for app_row in apps:
        if app_row.is_active:
            return app_row
    return None
