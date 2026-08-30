"""Rate limiting integration test."""

import pytest


def _payload(content: str) -> dict:
    return {"model": "m", "messages": [{"role": "user", "content": content}]}


@pytest.mark.asyncio
async def test_rate_limit_blocks_after_limit(client, app):
    state = app.state.asguard
    # Find the demo application id from the applications API.
    apps = (await client.get("/api/applications")).json()["applications"]
    demo = next(a for a in apps if a["name"] == "Demo Assistant")
    state.rate_limiter.reset(demo["id"])

    # Fire more than the limit; final responses must start returning 429.
    statuses = []
    for _ in range(demo["rate_limit_rpm"] + 2):
        response = await client.post("/v1/chat/completions", json=_payload("hello"))
        statuses.append(response.status_code)
    assert 429 in statuses
    assert statuses[-1] == 429
