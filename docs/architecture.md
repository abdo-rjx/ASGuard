# Architecture
# Architecture

## Interactive diagrams

Open these self-contained HTML files in any browser (no server needed) — pan/zoom, dark/light theme (T), guided views, PNG/SVG export:

| # | Diagram | What it shows |
|---|---|---|
| 1 | [`assets/diagrams/01-system-architecture.html`](../assets/diagrams/01-system-architecture.html) | Where ASGuard sits: User → App → ASGuard → Cloud AI / Company AI, plus the management plane |
| 2 | [`assets/diagrams/02-security-pipeline.html`](../assets/diagrams/02-security-pipeline.html) | How ASGuard decides: normalize → detect → risk → policy → deliver/block — detectors give evidence, policy decides |
| 3 | [`assets/diagrams/03-attack-detection-enforcement.html`](../assets/diagrams/03-attack-detection-enforcement.html) | What ASGuard protects against, both directions — inbound threats before the model, outbound leaks before the user |

Sources (`*.json`, same directory) are Archify IR — edit and re-render to update a diagram.


## Positioning

ASGuard is a **bidirectional security firewall** that sits between a client/application
and an existing AI backend. It is deliberately *not* an AI: it does not generate content,
execute tools, query databases, or retrieve documents. It only inspects, scores, decides,
sanitizes and audits.

```text
Client
  ↓
POST /v1/chat/completions          (OpenAI-compatible)
  ↓
ASGuard Gateway ── rate limit, request id
  ↓
Input Guard ── normalize → detect → intent → risk → policy
  ↓  (BLOCK ⇒ 403, nothing reaches the AI)
Upstream AI (OpenAICompatibleProvider)
  ↓
Output Guard ── parse → detect → risk → policy → sanitize → verify
  ↓  (BLOCK ⇒ 403 · SANITIZE ⇒ content replaced)
Client
```

## Module map (`backend/src/asguard/`)

| Module | Responsibility |
|---|---|
| `security_models/` | Core interfaces: `DetectorResult`, `RiskAssessment`, `PolicyDecision`, `SanitizationResult`, `SecurityEvent`, `PipelineStageTrace`, enums |
| `normalization.py` | Unicode/homoglyph/leet folding, invisible-char removal, separated-letter collapse, condensed view |
| `input_guard/` | `InputDetector` base + prompt injection, jailbreak, system-prompt extraction, obfuscation, suspicious-intent detectors; `InputGuard` pipeline |
| `output_guard/` | Output leak detectors (secrets, passwords, tokens, phone, email, financial, confidential); `Sanitizer`; `OutputGuard` pipeline |
| `risk/` | Deterministic noisy-OR risk engine (0–100) |
| `policy/` | Deterministic policy engine — **final enforcement authority**; default rule sets; rule validation |
| `gateway/` | `OpenAICompatibleProvider` (provider-independent upstream client), in-memory `RateLimiter`, `ProxyService` transaction orchestrator |
| `persistence/` | Async SQLAlchemy ORM (PostgreSQL/SQLite), repositories, metrics aggregation |
| `audit/` | Configuration-change audit helpers |
| `api/` | FastAPI app factory, routes (proxy, dashboard, policies, applications, testing, settings, health) |
| `app/` | `AppState` wiring, settings service (defaults + validation), idempotent seeding |
| `demo/` | Mock OpenAI-compatible upstream for local demo mode |
| `testing/` | YAML security-test corpus loader + runner (backs the dashboard Testing page) |

## Transaction lifecycle (request inspector)

Every proxied transaction records a stage trace with status, latency, risk and decision:

```text
Request → Rate Limit → Normalization → Threat Detection → Intent Analysis
        → Risk Scoring → Policy → [Upstream AI]
        → Response Parsing → Output Detection → Output Risk Scoring
        → Output Policy → [Sanitization] → Final Verification → Deliver
```

Stages are persisted with the `SecurityEvent` and rendered by the dashboard's
Request Inspector.

## Design principles

1. **Detectors provide evidence; the policy engine decides.** No ML model, heuristic or
   LLM ever blocks on its own.
2. **Deterministic by default.** Rules + patterns are cheap, explainable and testable.
   The architecture leaves clean extension points (custom detectors, semantic engines)
   but ships zero-LLM security so added latency stays in single-digit milliseconds.
3. **Fail closed for critical failures.** Detector crashes ⇒ BLOCK (configurable via
   `detector_failure_mode`), sanitization that cannot be verified ⇒ BLOCK.
4. **Privacy by default.** Raw content is never persisted. The only way content reaches
   the event store is an explicit per-application `content_preview` logging mode.
5. **Safe content stays untouched.** Responses with no triggered policy are delivered
   byte-for-byte; no rewriting, no LLM rewriter in the loop (the optional rewriter is a
   documented extension point, not wired by default).
6. **Provider independence.** Anything that speaks OpenAI-compatible
   `/chat/completions` works by configuration. No provider logic exists in the
   security core.

## Data ownership

ASGuard's PostgreSQL instance holds only ASGuard's own metadata:
`applications`, `policies`, `policy_versions`, `security_events`, `detection_results`,
`test_runs`, `app_settings`, `audit_log`. There are no enterprise/business tables and no
enterprise credentials anywhere in the codebase.