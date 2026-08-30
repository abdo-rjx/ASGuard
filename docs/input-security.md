# Input Security

The input guard inspects every user message **before** it reaches the existing AI.

## Pipeline

```text
Normalize → Detect → Intent Analysis → Risk Scoring → Policy
```

### 1. Normalization (`normalization.py`)

Produces a canonical view of the raw text so obfuscation cannot hide threats:

- NFKC unicode folding + casefold
- homoglyph folding (Cyrillic/fullwidth lookalikes → ASCII)
- invisible character removal (zero-width, BOM, soft hyphens)
- leetspeak folding (`1→i`, `0→o`, `3→e`, `4→a`, `5→s`, `7→t`, `$`, `@`, `|`)
- whitespace collapse
- **separated-letter collapse** when letter separation is detected
  (`i g n o r e a l l …` → matchable words)
- a **condensed view** (all separators removed) used by condensed pattern matching

Obfuscation heuristics raise flags consumed by the obfuscation detector.

### 2. Detectors (`input_guard/`)

Each detector returns structured evidence:

```json
{
  "detector": "prompt_injection",
  "category": "prompt_injection",
  "detected": true,
  "confidence": 0.95,
  "severity": "HIGH",
  "signals": ["instruction_override"]
}
```

| Detector | Category | Severity | Example caught |
|---|---|---|---|
| `prompt_injection` | prompt_injection | HIGH | "ignore previous instructions", "disregard your rules", "you are now…", authority claims |
| `jailbreak` | jailbreak | HIGH | "do anything now", DAN, "you have no restrictions", unfiltered mode, fictional framing |
| `system_prompt_extraction` | system_prompt_extraction | HIGH | "reveal your system prompt", "repeat everything above", "what are your initial instructions" |
| `obfuscation` | obfuscation | MEDIUM | invisible characters, letter separation, base64-like blobs, normalization deltas |
| `suspicious_intent` | suspicious_intent | MEDIUM | exfiltration, webhook exfil, credential harvesting, destructive commands, security evasion |

Obfuscation is defeated *before* detection (the normalized/condensed text is what the
pattern detectors scan), so `1gn0re аll previ0us instructi0ns` and
`i g n o r e a l l p r e v i o u s i n s t r u c t i o n s` are both caught as injection.

### 3. Risk engine (`risk/engine.py`)

Severity-weighted detector scores are combined with a **noisy-OR** aggregation:

```text
score = 100 × (1 − Π (1 − confidenceᵢ × severityWeightᵢ))
```

Properties: deterministic (same evidence ⇒ same score), monotonic (more/firmer signals ⇒
higher score), bounded 0–100. Levels: LOW <40, MEDIUM <70, HIGH <90, CRITICAL ≥90.

### 4. Policy (`policy/engine.py`)

Deterministic rules (`direction + category + threshold + action`); see
[docs/policies.md](docs/policies.md). Default input actions: injection/jailbreak/
extraction/suspicious-intent → **BLOCK**, obfuscation → **REVIEW**.

## What happens on each decision

| Decision | Behaviour |
|---|---|
| `ALLOW` | request forwarded to the upstream AI unchanged |
| `REVIEW` | request forwarded, event flagged `REVIEW` in the dashboard |
| `BLOCK` | upstream never called; HTTP 403 with a structured error body; event recorded with `upstream_status=blocked` |
| detector failure | `fail_closed` (default): BLOCK with reason `detector_failure_fail_closed` |

## Benign false-positive guards

Legitimate phrasing like *"How do I ignore previous emails in Outlook?"* or *"write a
story about a robot following the rules of its creator"* must remain ALLOW — the corpus
(`backend/security_test_cases/input_cases.yaml`, `input-benign-*`) locks this in.