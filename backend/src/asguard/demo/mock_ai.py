"""Demo/mock AI upstream — an OpenAI-compatible endpoint for local demos.

This mock AI plays the role of the "existing AI" so the full pipeline
(client → ASGuard → AI → ASGuard → client) can be exercised without external
API keys. It never returns real secrets; the "leaky" demo responses contain
clearly fake example values.
"""

from __future__ import annotations

import time
import uuid

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/demo/upstream/v1")

_DEMO_MODEL = "asguard-demo-ai"

# Canned demo responses (all values are fake examples).
_RESPONSES = [
    # (keywords in prompt, response content)
    (["phone"], "Ahmed's phone number is +212 6 12 34 56 78. Please keep it private."),
    (["api key", "apikey", "credential"], "Here are the credentials you asked for: API key: sk-demo-not-a-real-key-000111222"),
    (["email", "contact"], "You can reach our support lead at jane.doe@example-corp.com or via the portal."),
    (["status"], "The project is 82% complete. All milestone deliverables are on track for next quarter."),
    (["salary"], "The senior engineer salary is 95,000 EUR per year according to the internal spreadsheet."),
    (["confidential", "internal"], "This section is confidential and intended for internal use only. The roadmap includes Q3 planning details."),
    (["password"], "The staging environment password is: hunter2-demo-password"),
    (["card", "credit"], "The test payment card on file is 4111 1111 1111 1111 (expired test card)."),
    (["hello", "hi ", "hey"], "Hello! I am the demo AI assistant protected by ASGuard. Ask me about project status, contacts, or credentials to see the security pipeline in action."),
]


@router.post("/chat/completions")
async def chat_completions(request: Request) -> JSONResponse:
    body = await request.json()
    if not isinstance(body, dict) or "messages" not in body:
        return JSONResponse(status_code=400, content={
            "error": {"message": "Invalid request: 'messages' is required.", "type": "invalid_request_error"}
        })

    content = ""
    for message in reversed(body.get("messages", [])):
        if isinstance(message, dict) and message.get("role") == "user":
            content = str(message.get("content", ""))
            break

    lowered = content.lower()
    reply = (
        "I am the demo AI assistant. I can talk about the project status, "
        "contacts, and (fake) credentials so you can observe ASGuard's "
        "bidirectional security pipeline."
    )
    for keywords, response in _RESPONSES:
        if any(k in lowered for k in keywords):
            reply = response
            break

    # Simulate small upstream latency so the inspector shows realistic timings.
    await _sleep(0.02)
    return JSONResponse({
        "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": body.get("model") or _DEMO_MODEL,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": reply},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": len(content.split()),
            "completion_tokens": len(reply.split()),
            "total_tokens": len(content.split()) + len(reply.split()),
        },
    })


async def _sleep(seconds: float) -> None:
    import asyncio

    await asyncio.sleep(seconds)
