# Policies

The policy engine is the **final, deterministic enforcement layer**. Detectors and the
risk engine only produce evidence; a simple, auditable rule set decides.

## Rule model

```text
direction (input|output) + category + threshold (0–100) + enabled → action
```

A rule triggers when its category was detected **and** the aggregate risk score is
≥ threshold. Triggered actions compose with strict precedence:

```text
ALLOW < REVIEW < SANITIZE < BLOCK
```

For sanitizing actions the rule also selects the replacement style:
`SANITIZE` → `[phone number removed]`, `REDACT` → `[REDACTED:FINANCIAL]`.

## Allowed actions per direction

| Direction | Allowed actions |
|---|---|
| input | ALLOW, BLOCK, REVIEW |
| output | ALLOW, REDACT, SANITIZE, BLOCK |

The API rejects invalid combinations (e.g. `REDACT` on an input rule) with HTTP 422 —
the UI cannot create invalid configurations.

## Default rules (safe defaults)

### Input

| Category | Action | Threshold |
|---|---|---|
| prompt_injection | BLOCK | 60 |
| jailbreak | BLOCK | 70 |
| system_prompt_extraction | BLOCK | 65 |
| suspicious_intent | BLOCK | 60 |
| obfuscation | REVIEW | 60 |

### Output

| Category | Action | Threshold |
|---|---|---|
| secret | BLOCK | 50 |
| pii | SANITIZE | 40 |
| financial | REDACT | 40 |
| confidential | BLOCK | 50 |

## Persistence & versioning

Policies live in ASGuard's own database (`policies` table, unique per
`direction+category`). Every change writes a row to `policy_versions`
(action/threshold/enabled/changed_by/reason/changed_at), giving a complete audit history.
The live policy engine is rebuilt from the persisted set immediately after each change —
no restart required.

## Managing policies

- Dashboard → **Policies** (edit action/threshold/enabled per rule)
- `GET /api/policies` — list with per-direction `allowed_actions`
- `PUT /api/policies/{id}` — validated update (writes a version + audit entry)
- `GET /api/policies/categories` — valid categories/actions per direction (UI metadata)

## Validation rules

- action must be valid for the rule's direction
- threshold must be an integer 0–100
- unknown categories/actions are rejected by the schema
- global settings additionally validate thresholds ordering
  (`review_threshold ≤ block_threshold`) — see Settings.