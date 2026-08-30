# Threat Model

## Assets

| Asset | Where it lives | Protection |
|---|---|---|
| User prompts | transient in memory | never persisted; content preview only via explicit per-app opt-in |
| AI responses | transient in memory | same as prompts; only sanitized content is delivered |
| ASGuard config (policies, apps, settings) | ASGuard's own PostgreSQL | change audit trail, validated writes |
| Upstream AI credentials | ASGuard DB (`applications.upstream_api_key`) | write-only via API — never returned by any endpoint |
| ASGuard DB credentials | environment (`DATABASE_URL`) | never logged; logs are auto-redacted |
| Enterprise data (DBs, RAG, tools, CRM/ERP) | **outside ASGuard** | ASGuard holds no credentials and no connectors |

## Trust boundaries

```text
[Client] ──▶ [ASGuard] ──▶ [Existing AI] ──▶ [Enterprise data]
   untrusted      trusted        trusted        (untouched by ASGuard)
```

ASGuard is deployed inside the operator's network, in front of the AI endpoint. The
client's existing authorization against the AI is preserved: ASGuard does not expand or
replace the AI's permissions (it cannot — it has none).

## Attack surface & mitigations

### 1. Prompt injection / instruction override
- **Vector:** user text tries to override system instructions.
- **Mitigation:** pattern + condensed-pattern detectors after aggressive normalization;
  noisy-OR risk; deterministic BLOCK at threshold 60. Regression corpus: `input-pi-*`.

### 2. Jailbreak / persona attacks (DAN etc.)
- **Mitigation:** jailbreak detector (roleplay bypass, unfiltered mode, safety-bypass
  phrasing); BLOCK at 70. Corpus: `input-jb-*`.

### 3. System prompt extraction
- **Mitigation:** extraction detector (reveal/echo/verbatim/config probes); BLOCK at 65.
  Corpus: `input-sx-*`.

### 4. Obfuscation (leet, homoglyphs, letter separation, invisible chars, base64 blobs)
- **Mitigation:** normalization strips the disguise *before* detection; the obfuscation
  detector additionally flags the attempt itself. Corpus: `input-of-*`.

### 5. Malicious intent (exfiltration, harvesting, destructive commands)
- **Mitigation:** suspicious-intent detector (external transmission + sensitive target
  co-occurrence); BLOCK at 60. Corpus: `input-in-*`.

### 6. Sensitive-data leakage in AI output (secrets, PII, financial, confidential)
- **Mitigation:** span-level detectors (Luhn for cards, digit-count for phones);
  policy-driven REDACT/SANITIZE/BLOCK; **re-scan after sanitization**, fail closed on
  residue. Corpus: `output-secret-*`, `output-pii-*`, `output-fin-*`, `output-conf-*`.

### 7. Denial of service
- **Mitigation:** per-application sliding-window rate limit (429), request body cap
  (1 MB), upstream timeout (configurable), bounded list endpoints.

### 8. Upstream compromise / unavailability
- **Mitigation:** structured error mapping (`upstream_timeout` → 504,
  `upstream_unavailable`/`upstream_invalid_response`/`upstream_error` → 502); internal
  stack traces never reach clients (global exception handler returns opaque 500).

### 9. Log/audit leakage
- **Mitigation:** `RedactingFormatter` masks secret-shaped substrings in every log line;
  raw content is never written to the event store unless a specific application enables
  `content_preview` logging.

### 10. Security control bypass via detector failure
- **Mitigation:** detector exceptions are contained and, under `fail_closed` (default),
  convert to BLOCK. A regression test proves a crashing detector blocks.

## Residual risks / accepted limitations

- Detection is rule/pattern-based; novel paraphrased attacks may score below thresholds.
  The architecture reserves extension points for semantic/ML detectors, but ships none.
- Rate limiting is per-process (in-memory); multi-instance deployments need a shared store.
- The dashboard has no built-in authentication; front it with SSO or a reverse proxy.
- Streaming responses are rejected (output inspection requires buffering).