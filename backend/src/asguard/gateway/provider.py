"""Upstream AI provider abstraction.

ASGuard is provider-independent: any OpenAI-compatible endpoint works by
configuring ``base_url``. The security core never sees provider specifics.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx


@dataclass
class UpstreamResult:
    status: int
    body: dict
    error: str | None = None  # error code when the upstream call failed


class AIProvider:
    """Minimal interface for an upstream AI provider."""

    async def chat_completions(self, payload: dict, timeout_s: float) -> UpstreamResult:  # pragma: no cover
        raise NotImplementedError

    async def aclose(self) -> None:  # pragma: no cover
        raise NotImplementedError


class OpenAICompatibleProvider(AIProvider):
    """Talks to any OpenAI-compatible /chat/completions endpoint."""

    def __init__(self, base_url: str, api_key: str | None = None, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        self._client = httpx.AsyncClient(headers=headers, timeout=None, transport=transport)

    async def chat_completions(self, payload: dict, timeout_s: float) -> UpstreamResult:
        url = f"{self.base_url}/chat/completions"
        try:
            response = await self._client.post(url, json=payload, timeout=timeout_s)
        except httpx.TimeoutException:
            return UpstreamResult(status=0, body={}, error="upstream_timeout")
        except httpx.HTTPError:
            return UpstreamResult(status=0, body={}, error="upstream_unavailable")

        if response.status_code >= 400:
            return UpstreamResult(
                status=response.status_code, body={}, error="upstream_error"
            )
        try:
            body = response.json()
        except ValueError:
            return UpstreamResult(status=response.status_code, body={}, error="upstream_invalid_response")
        return UpstreamResult(status=response.status_code, body=body)

    async def aclose(self) -> None:
        await self._client.aclose()
