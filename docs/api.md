# API Reference

Base URL: `http://<host>:8000`. Interactive docs: `/api/docs` (OpenAPI at `/api/openapi.json`).

## Proxy (OpenAI-compatible)

### `POST /v1/chat/completions`
Main gateway endpoint. The client only changes its `base_url`.

Request body: OpenAI chat-completion JSON (`messages` required).
- `"stream": true` → `400 streaming_not_supported` (non-streaming only in this version).
- Body > 1 MB → `413 payload_too_large`.

Resolution of the target application:
1. `Authorization: Bearer <client_api_key>` matching a configured application; else
2. the first active application (default).

Responses:
- `200` — ALLOW/REVIEW/SANITIZE. `SANITIZE` responses have sensitive spans replaced.
  Headers: `X-Request-Id`, `X-ASGuard-Decision`, `X-ASGuard-Risk`, `X-ASGuard-Event-Id`.
- `403` — BLOCK (input or output). Body:
  ```json
  {"error": {"type": "asguard_security_block", "code": "input_blocked",
             "message": "Request blocked by ASGuard security policy.",
             "details": {"direction": "input", "reason": "prompt_injection",
                          "risk_score": 99, "triggered_rules": ["prompt_injection:BLOCK"],
                          "request_id": "…"}}}
  ```
- `429` — rate limit exceeded (`rate_limited`).
- `502`/`504` — upstream errors (`upstream_unavailable`, `upstream_invalid_response`,
  `upstream_error`, `upstream_timeout`). Internal details are never exposed.

## Operational

- `GET /health` → `{"status": "ok"}`
- `GET /ready` → `200` with DB check, or `503` when the database is unavailable.

## Dashboard API

| Method | Path | Description |
|---|---|---|
| GET | `/api/dashboard/metrics?window_hours=24` | Real aggregates: requests, allowed, blocked, sanitized, reviewed, threats, avg risk/latency, threats by category, recent events |
| GET | `/api/dashboard/timeseries?hours=24` | Hourly allowed/blocked/sanitized/reviewed buckets |
| GET | `/api/events?limit&offset&direction&decision` | Paginated security events |
| GET | `/api/events/{id}` | Full event: stage trace, detections, latencies |
| GET | `/api/policies` | Policy rules + per-direction allowed actions |
| GET | `/api/policies/categories` | Valid categories/actions (UI metadata) |
| PUT | `/api/policies/{id}` | Validated update `{action, threshold, enabled, reason?}` → versions + audit |
| GET | `/api/applications` | Applications (never includes upstream API keys) |
| POST | `/api/applications` | Create (name, upstream_url, upstream_api_key?, auth_type, timeout_ms, rate_limit_rpm, logging_mode) |
| PUT | `/api/applications/{id}` | Partial update (unset fields untouched; keys write-only) |
| DELETE | `/api/applications/{id}` | Remove an application |
| GET | `/api/testing/cases` | The shipped YAML corpus metadata |
| POST | `/api/testing/run` | Execute the corpus against the live engine, persist a run |
| GET | `/api/testing/results?limit=10` | Recent runs with full per-case results |
| GET | `/api/settings` | Merged settings document |
| PUT | `/api/settings` | Validated settings update (422 on invalid values) |
| GET | `/api/audit` | Recent configuration-change audit entries |

## Error format

All errors are structured; stack traces are never returned:

```json
{"error": {"type": "asguard_error", "code": "invalid_request", "message": "…"}}
```