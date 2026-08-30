"""Proxy transaction orchestrator.

Runs the full bidirectional pipeline for one OpenAI-compatible request:

    Request → Input Guard → [BLOCK?]
            → Upstream AI → Output Guard → [BLOCK/SANITIZE?]
            → Deliver
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

from asguard.gateway.provider import AIProvider
from asguard.gateway.ratelimit import RateLimiter
from asguard.security_models.enums import Decision, Direction
from asguard.security_models.models import (
    PipelineStageTrace,
    PolicyDecision,
    RiskAssessment,
    SecurityEvent,
    StageStatus,
)


@dataclass
class ProxyOutcome:
    """Result of one proxy transaction (used by the API layer)."""

    request_id: str
    decision: Decision
    reason: str = ""
    risk_score: int = 0
    http_status: int = 200
    response_body: dict = field(default_factory=dict)
    security_event: SecurityEvent | None = None
    error_code: str | None = None


class ProxyService:
    """Orchestrates a full proxied chat completion transaction."""

    def __init__(
        self,
        input_guard,
        output_guard,
        provider_factory,
        rate_limiter: RateLimiter | None = None,
    ) -> None:
        self.input_guard = input_guard
        self.output_guard = output_guard
        self.provider_factory = provider_factory  # (app) -> AIProvider
        self.rate_limiter = rate_limiter or RateLimiter()

    async def handle_chat_completion(
        self,
        *,
        payload: dict,
        application,
        content_preview_allowed: bool,
    ) -> ProxyOutcome:
        """Process one request end-to-end. Never raises for expected failures."""
        request_id = uuid.uuid4().hex
        event_id = uuid.uuid4().hex
        total_start = time.perf_counter()
        stages: list[PipelineStageTrace] = []

        application_name = getattr(application, "name", None)
        application_id = getattr(application, "id", None)

        # --- 0. Rate limiting ------------------------------------------------
        if not self.rate_limiter.allow(
            application_id or "default", getattr(application, "rate_limit_rpm", 120)
        ):
            event = _make_event(
                event_id, request_id, application_id, application_name,
                decision=Decision.BLOCK, risk=0,
                stages=[PipelineStageTrace(name="Rate Limit", status=StageStatus.BLOCKED,
                                           decision=Decision.BLOCK, detail="rate limit exceeded")],
                upstream_status="skipped", error_code="rate_limited",
                total_ms=_ms(total_start),
                content_preview=_preview(payload, content_preview_allowed),
            )
            return ProxyOutcome(
                request_id=request_id, decision=Decision.BLOCK, reason="rate_limited",
                risk_score=0, http_status=429, security_event=event, error_code="rate_limited",
                response_body=_error_body("rate_limited", "Rate limit exceeded for this application.", 429),
            )

        # --- 1. Input security ------------------------------------------------
        user_content = extract_user_content(payload)
        in_detections, in_risk, in_decision, in_stages, input_ms = _run_input(
            self.input_guard, user_content
        )
        stages.extend(in_stages)

        if in_decision.decision == Decision.BLOCK:
            event = _make_event(
                event_id, request_id, application_id, application_name,
                decision=Decision.BLOCK, risk=in_risk.score,
                stages=stages, detections=in_detections,
                upstream_status="blocked", error_code="input_blocked",
                total_ms=_ms(total_start), input_ms=input_ms,
                content_preview=_preview(payload, content_preview_allowed),
            )
            return ProxyOutcome(
                request_id=request_id, decision=Decision.BLOCK, reason=in_decision.reason,
                risk_score=in_risk.score, http_status=403, security_event=event,
                error_code="input_blocked",
                response_body=_blocked_body("input", in_decision, in_risk, request_id),
            )

        # --- 2. Forward to upstream AI ----------------------------------------
        t0 = time.perf_counter()
        provider: AIProvider = self.provider_factory(application)
        upstream_result = await provider.chat_completions(
            payload, timeout_s=getattr(application, "timeout_ms", 60000) / 1000.0
        )
        await provider.aclose()
        upstream_ms = _ms(t0)
        upstream_status = "ok" if upstream_result.error is None and upstream_result.status < 400 else "error"
        stages.append(
            PipelineStageTrace(
                name="Upstream AI",
                status=StageStatus.FAILED if upstream_result.error else StageStatus.OK,
                latency_ms=upstream_ms,
                detail=upstream_result.error or f"HTTP {upstream_result.status}",
            )
        )

        if upstream_result.error:
            return _upstream_error_outcome(
                event_id=event_id, request_id=request_id,
                application_id=application_id, application_name=application_name,
                upstream_result=upstream_result, stages=stages, detections=in_detections,
                in_risk=in_risk, input_ms=input_ms, upstream_ms=upstream_ms,
                total_start=total_start, payload=payload,
                content_preview_allowed=content_preview_allowed,
            )

        # --- 3. Output security -------------------------------------------------
        response_content = extract_response_content(upstream_result.body)
        out_detections, out_risk, out_decision, out_stages, sanitization, output_ms = (
            self.output_guard.check(response_content)
        )
        stages.extend(out_stages)
        max_risk = max(in_risk.score, out_risk.score)

        if out_decision.decision == Decision.BLOCK:
            event = _make_event(
                event_id, request_id, application_id, application_name,
                decision=Decision.BLOCK, risk=max_risk,
                stages=stages, detections=in_detections + out_detections,
                upstream_status=upstream_status, error_code="output_blocked",
                total_ms=_ms(total_start), input_ms=input_ms, upstream_ms=upstream_ms,
                output_ms=output_ms,
                content_preview=_preview(payload, content_preview_allowed),
            )
            return ProxyOutcome(
                request_id=request_id, decision=Decision.BLOCK, reason=out_decision.reason,
                risk_score=max_risk, http_status=403, security_event=event,
                error_code="output_blocked",
                response_body=_blocked_body("output", out_decision, out_risk, request_id),
            )

        final_decision = out_decision.decision
        final_content = response_content
        if final_decision == Decision.SANITIZE and sanitization is not None:
            final_content = sanitization.sanitized_text
        if in_decision.decision == Decision.REVIEW:
            final_decision = Decision.REVIEW

        # --- 4. Deliver (rewrite response content) ------------------------------
        delivered = replace_response_content(upstream_result.body, final_content)
        total_ms = _ms(total_start)
        stages.append(
            PipelineStageTrace(
                name="Deliver",
                status=StageStatus.SANITIZED if sanitization is not None else StageStatus.OK,
                decision=final_decision,
                detail="delivered" + (" (sanitized)" if sanitization is not None else ""),
            )
        )

        combined_detections = in_detections + out_detections
        threat_types = sorted({d.category for d in combined_detections if d.detected})
        event = SecurityEvent(
            event_id=event_id,
            request_id=request_id,
            application_id=application_id,
            application_name=application_name,
            decision=final_decision,
            risk_score=max_risk,
            threat_types=threat_types,
            policy_triggered=in_decision.triggered_rules + out_decision.triggered_rules,
            detections=combined_detections,
            stages=stages,
            input_latency_ms=input_ms,
            output_latency_ms=output_ms,
            upstream_latency_ms=upstream_ms,
            total_latency_ms=total_ms,
            upstream_status=upstream_status,
            content_preview=_preview(payload, content_preview_allowed),
        )
        return ProxyOutcome(
            request_id=request_id,
            decision=final_decision,
            reason=out_decision.reason if final_decision == Decision.SANITIZE else "allowed",
            risk_score=max_risk,
            http_status=200,
            response_body=delivered,
            security_event=event,
        )


# ---------------------------------------------------------------------------
# OpenAI payload helpers
# ---------------------------------------------------------------------------

def extract_user_content(payload: dict) -> str:
    """Concatenate user messages (the content inspected by the input guard)."""
    parts: list[str] = []
    for message in payload.get("messages", []):
        if isinstance(message, dict) and message.get("role") == "user":
            content = message.get("content", "")
            if isinstance(content, str):
                parts.append(content)
            elif isinstance(content, list):
                for chunk in content:
                    if isinstance(chunk, dict) and isinstance(chunk.get("text"), str):
                        parts.append(chunk["text"])
    return "\n".join(parts)


def extract_response_content(body: dict) -> str:
    """Extract the assistant message content from an upstream response."""
    choices = body.get("choices") or []
    for choice in choices:
        message = choice.get("message") or {}
        if isinstance(message.get("content"), str):
            return message["content"]
        if isinstance(choice.get("text"), str):
            return choice["text"]
    return ""


def replace_response_content(body: dict, new_content: str) -> dict:
    """Return a copy of the body with the first choice's content replaced."""
    updated = dict(body)
    choices = [dict(c) for c in updated.get("choices", [])]
    for choice in choices:
        if "message" in choice and isinstance(choice.get("message"), dict):
            message = dict(choice["message"])
            if "content" in message:
                message["content"] = new_content
                choice["message"] = message
        elif "text" in choice:
            choice["text"] = new_content
        break
    updated["choices"] = choices
    return updated


def _blocked_body(direction: str, decision: PolicyDecision, risk: RiskAssessment, request_id: str) -> dict:
    return {
        "error": {
            "type": "asguard_security_block",
            "code": f"{direction}_blocked",
            "message": "Request blocked by ASGuard security policy.",
            "details": {
                "direction": direction,
                "reason": decision.reason,
                "risk_score": risk.score,
                "triggered_rules": decision.triggered_rules,
                "request_id": request_id,
            },
        }
    }


def _error_body(code: str, message: str, status: int) -> dict:
    return {
        "error": {
            "type": "asguard_error",
            "code": code,
            "message": message,
            "http_status": status,
        }
    }


def _preview(payload: dict, allowed: bool, max_len: int = 200) -> str | None:
    """Content preview — only when the application's logging mode allows it."""
    if not allowed:
        return None
    content = extract_user_content(payload).replace("\n", " ")
    return content[:max_len] if content else None


def _ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 3)


def _run_input(input_guard, content: str):
    """Run the input guard; returns (detections, risk, decision, stages, input_ms)."""
    _normalized, detections, risk, decision, stages, input_ms = input_guard.analyze(content)
    return detections, risk, decision, stages, input_ms


def _make_event(
    event_id, request_id, application_id, application_name, *,
    decision, risk, stages, detections=None, upstream_status="skipped",
    error_code=None, total_ms=0.0, input_ms=0.0, upstream_ms=0.0, output_ms=0.0,
    content_preview=None,
) -> SecurityEvent:
    return SecurityEvent(
        event_id=event_id,
        request_id=request_id,
        application_id=application_id,
        application_name=application_name,
        decision=decision,
        risk_score=risk,
        detections=detections or [],
        stages=stages,
        input_latency_ms=input_ms,
        upstream_latency_ms=upstream_ms,
        output_latency_ms=output_ms,
        total_latency_ms=total_ms,
        upstream_status=upstream_status,
        error_code=error_code,
        content_preview=content_preview,
    )


def _upstream_error_outcome(*, event_id, request_id, application_id, application_name,
                            upstream_result, stages, detections, in_risk, input_ms,
                            upstream_ms, total_start, payload, content_preview_allowed) -> ProxyOutcome:
    error_code = upstream_result.error or "upstream_error"
    http_status = 504 if error_code == "upstream_timeout" else 502
    event = _make_event(
        event_id, request_id, application_id, application_name,
        decision=Decision.ERROR, risk=in_risk.score,
        stages=stages, detections=detections,
        upstream_status="error", error_code=error_code,
        total_ms=_ms(total_start), input_ms=input_ms, upstream_ms=upstream_ms,
        content_preview=_preview(payload, content_preview_allowed),
    )
    message = {
        "upstream_timeout": "The upstream AI did not respond in time.",
        "upstream_unavailable": "The upstream AI is unreachable.",
        "upstream_invalid_response": "The upstream AI returned an invalid response.",
    }.get(error_code, "The upstream AI returned an error.")
    return ProxyOutcome(
        request_id=request_id, decision=Decision.ERROR, reason=error_code,
        risk_score=in_risk.score, http_status=http_status, security_event=event,
        error_code=error_code,
        response_body=_error_body(error_code, message, http_status),
    )
