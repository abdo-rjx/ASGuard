# Output Security

The output guard inspects AI-generated content **before** it is delivered to the user.

## Pipeline

```text
Parse → Detect → Risk → Policy → [Sanitize] → Final Verification
```

### 1. Parsing

The assistant `message.content` (or completion `text`) is extracted from the upstream's
OpenAI-shaped response. Only this text is inspected; the rest of the envelope is passed
through untouched.

### 2. Detectors (`output_guard/`)

All detectors return **spans** (`start`, `end`, masked preview) into the original text so
the sanitizer can redact precisely without touching anything else.

| Detector | Category | Severity | Catches |
|---|---|---|---|
| `secret_api_key` | secret | CRITICAL | `sk-…`, `AKIA…`, `ghp_…`, `xox…`, `AIza…`, labeled keys |
| `secret_password` | secret | CRITICAL | `password: …`, `-----BEGIN PRIVATE KEY-----` |
| `secret_token` | secret | HIGH | bearer tokens, JWTs, session/access/refresh tokens |
| `pii_phone` | pii | MEDIUM | international and national phone formats (≥7 digits) |
| `pii_email` | pii | MEDIUM | email addresses |
| `financial_data` | financial | HIGH | Luhn-validated cards, IBAN-shaped tokens, salary figures |
| `confidential_data` | confidential | HIGH | confidentiality markers ("confidential", "internal use only", …) |

False-positive controls: card numbers must pass a **Luhn check**, phone spans must carry
≥7 digits, and salary/wage detection requires a money-like figure.

### 3. Risk + Policy

Same deterministic engines as the input side. Default output actions:

- `secret` → **BLOCK** (default 50) — preferred when safe transformation is uncertain
- `pii` → **SANITIZE** (40)
- `financial` → **REDACT** (40)
- `confidential` → **BLOCK** (50)

### 4. Deterministic sanitization (`sanitizer.py`)

Sensitive spans are removed with typed placeholders:

- `REDACT` → `[REDACTED:API_KEY]`
- `SANITIZE` → `[phone number removed]`, `[email address removed]`, …

Overlapping spans are merged; replacement happens back-to-front so offsets stay valid.
Nothing else in the response is modified — safe content remains byte-for-byte identical
(spec rule 5).

### 5. Final verification (fail closed)

After sanitization the result is **re-scanned with all detectors**. If any sensitive span
survives (e.g. a pattern that a placeholder could not safely neutralize), the pipeline
escalates to `BLOCK` with reason `sanitization_verification_failed` instead of delivering
a partially-cleaned response.

### 6. Delivery

`ALLOW`/`REVIEW`/`SANITIZE` responses are delivered (sanitized content spliced back into
the original response envelope) with `X-ASGuard-Decision`, `X-ASGuard-Risk` and
`X-ASGuard-Event-Id` headers.

## Response rewriting (optional, not enabled)

The spec allows an optional rewriter for cases where sanitization damages readability.
By design ASGuard ships **without** an LLM rewriter: redaction placeholders keep responses
readable and avoid all rewriter risks (inventing facts, reintroducing redacted data,
extra LLM latency). `output_guard/` is structured so a rewriter can be inserted between
"Sanitize" and "Final Verification" as a clean extension point.