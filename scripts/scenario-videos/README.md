# ASGuard scenario videos

Generates one narrated explainer video per security-test category from
`backend/security_test_cases/`, recorded with Playwright at human speed.

Every verdict shown in the videos (decision, risk score, fired detectors,
stage timings, sanitized output) is produced by the **real** ASGuard
`InputGuard` / `OutputGuard` engines — nothing is mocked.

## Categories (11 videos)

| # | Category | Direction | Cases |
|---|----------|-----------|-------|
| 01 | Prompt Injection | input | 4 |
| 02 | Jailbreak | input | 3 |
| 03 | System Prompt Extraction | input | 2 |
| 04 | Obfuscation Attacks | input | 2 |
| 05 | Suspicious Intent | input | 2 |
| 06 | Benign Input (false-positive guard) | input | 4 |
| 07 | Secret Leakage | output | 4 |
| 08 | PII Leakage | output | 2 |
| 09 | Financial Data Leakage | output | 2 |
| 10 | Confidential Content | output | 1 |
| 11 | Benign Output (false-positive guard) | output | 3 |

## Regenerate

```bash
cd scripts/scenario-videos
npm install                       # playwright
npx playwright install chromium   # once
python3 capture_verdicts.py       # 1. run the corpus through the real engine
node generate.mjs                 # 2. record videos -> videos/scenarios/*.webm
```

`node generate.mjs <filter>` records only matching categories
(e.g. `node generate.mjs pii`).

## Output

`videos/scenarios/NN-<category>.webm` — 1280×720, ~60–110 s each.

Convert with ffmpeg if you need MP4:
`ffmpeg -i 01-prompt-injection.webm -c:v libx264 -crf 20 -pix_fmt yuv420p 01-prompt-injection.mp4`

## Files

- `capture_verdicts.py` — runs the YAML corpus through the live engine, writes `verdicts.json`
- `explainer.html` — self-contained ASGuard-branded explainer page driven via `window.__driver`
- `generate.mjs` — Playwright recorder (human-speed typewriter, pipeline and verdict animation)
