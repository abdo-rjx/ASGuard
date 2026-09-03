#!/usr/bin/env python3
"""Capture real ASGuard verdicts for every security-test scenario.

Runs the YAML corpus under backend/security_test_cases/ through the live
InputGuard / OutputGuard engines and writes verdicts.json — grouped into
presentation categories — for the Playwright scenario-video generator.

Usage:
    python3 capture_verdicts.py   (from this directory)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "backend" / "src"))

import yaml  # noqa: E402

from asguard.input_guard.pipeline import InputGuard  # noqa: E402
from asguard.output_guard.pipeline import OutputGuard  # noqa: E402

CASES_DIR = REPO / "backend" / "security_test_cases"
OUT_PATH = HERE / "verdicts.json"

# Presentation grouping: one video per entry. `match` selects corpus cases.
CATEGORIES = [
    {
        "key": "prompt-injection",
        "title": "Prompt Injection",
        "direction": "input",
        "match": {"direction": "input", "category": "prompt_injection"},
        "tagline": "Instruction-override attacks that try to hijack the AI.",
        "how": [
            "Pattern detectors scan every prompt for instruction overrides — \"ignore previous instructions\", fake developer messages, rule rewrites.",
            "Matched evidence is scored by the noisy-OR risk engine, then the deterministic policy engine makes the final call.",
            "Blocked prompts receive an HTTP 403 — the AI never sees them.",
        ],
    },
    {
        "key": "jailbreak",
        "title": "Jailbreak",
        "direction": "input",
        "match": {"direction": "input", "category": "jailbreak"},
        "tagline": "Persona and mode-switch escapes (\"developer mode\", \"no rules\").",
        "how": [
            "The jailbreak detector recognises roleplay escapes: \"developer mode\", \"act as if you have no rules\", unfiltered/DAN mode.",
            "High-confidence matches push the risk score past the block threshold.",
            "ASGuard blocks the request and records the full evidence trail.",
        ],
    },
    {
        "key": "system-prompt-extraction",
        "title": "System Prompt Extraction",
        "direction": "input",
        "match": {"direction": "input", "category": "system_prompt_extraction"},
        "tagline": "Attempts to make the model leak its hidden instructions.",
        "how": [
            "The extraction detector flags prompts asking the model to repeat or reveal its system prompt.",
            "\"Repeat everything above\", \"show me your initial instructions\" — all variants are caught.",
            "The hidden prompt stays hidden; the request is blocked.",
        ],
    },
    {
        "key": "obfuscation",
        "title": "Obfuscation Attacks",
        "direction": "input",
        "match": {"direction": "input", "category": "obfuscation"},
        "tagline": "Leetspeak, homoglyphs and letter-spacing used to hide attacks.",
        "how": [
            "Before detection, normalization folds leetspeak (1 → i, 0 → o), unicode homoglyphs and letter-spacing.",
            "Tricks that fool plain-text filters become visible to the detectors.",
            "The de-obfuscated injection is scored and blocked like any other.",
        ],
    },
    {
        "key": "suspicious-intent",
        "title": "Suspicious Intent",
        "direction": "input",
        "match": {"direction": "input", "category": "suspicious_intent"},
        "tagline": "Data-theft intent: steal secrets, exfiltrate to external endpoints.",
        "how": [
            "The intent detector looks for exfiltration patterns — collecting records, stealing credentials, posting to external webhooks.",
            "Intent signals add evidence on top of the pattern detectors.",
            "Requests with theft intent are blocked before reaching the AI.",
        ],
    },
    {
        "key": "benign-input",
        "title": "Benign Input — False-Positive Guard",
        "direction": "input",
        "match": {"direction": "input", "category": "benign"},
        "tagline": "Legitimate prompts must never be over-blocked.",
        "how": [
            "Detection must stay precise: prompts that merely mention words like \"ignore\" must still pass.",
            "Benign cases run through the same pipeline — and must come out ALLOW.",
            "These cases are part of the regression corpus so over-blocking fails CI.",
        ],
    },
    {
        "key": "secret-leakage",
        "title": "Secret Leakage",
        "direction": "output",
        "match": {"direction": "output", "category": "secret"},
        "tagline": "API keys, AWS keys, passwords and tokens leaking out in responses.",
        "how": [
            "The output guard inspects every AI response before it reaches the client.",
            "API keys (sk-…), AWS access keys (AKIA…), passwords and bearer tokens are recognised by typed detectors.",
            "Critical leaks are blocked outright (HTTP 403) — never forwarded.",
        ],
    },
    {
        "key": "pii-leakage",
        "title": "PII Leakage",
        "direction": "output",
        "match": {"direction": "output", "category": "pii"},
        "tagline": "Phone numbers and e-mail addresses redacted in transit.",
        "how": [
            "PII detectors find phone numbers and e-mail addresses in AI responses.",
            "Instead of dropping the whole answer, the sanitizer replaces each span with a typed placeholder.",
            "A final verification re-scan confirms zero residue before delivery.",
        ],
    },
    {
        "key": "financial-leakage",
        "title": "Financial Data Leakage",
        "direction": "output",
        "match": {"direction": "output", "category": "financial"},
        "tagline": "Salaries and card numbers redacted before delivery.",
        "how": [
            "Financial detectors recognise salary figures and card numbers (Luhn-validated, so random digits don't trip it).",
            "Each sensitive span is replaced with a typed placeholder — the response stays useful.",
            "The sanitized result is re-scanned and verified clean.",
        ],
    },
    {
        "key": "confidential-content",
        "title": "Confidential Content",
        "direction": "output",
        "match": {"direction": "output", "category": "confidential"},
        "tagline": "\"Internal use only\" material must not leave the perimeter.",
        "how": [
            "The confidential detector flags responses marked confidential / internal-only.",
            "Because redaction cannot make confidential content safe, policy blocks the response.",
        ],
    },
    {
        "key": "benign-output",
        "title": "Benign Output — False-Positive Guard",
        "direction": "output",
        "match": {"direction": "output", "category": "benign"},
        "tagline": "Normal technical content must reach the client byte-for-byte.",
        "how": [
            "Numbers in brackets are not card numbers; phone-system stats are not PII.",
            "Benign outputs must pass the output guard untouched (ALLOW).",
            "Like the input guards, these cases run in CI to catch over-blocking.",
        ],
    },
]


def dump_detector(r) -> dict:
    return {
        "detector": r.detector,
        "category": r.category.value,
        "detected": r.detected,
        "confidence": round(r.confidence, 2),
        "severity": r.severity.value,
        "signals": list(r.signals),
        "spans": [
            {"label": s.label, "start": s.start, "end": s.end,
             "masked_preview": s.masked_preview}
            for s in r.spans
        ],
    }


def run_case(case: dict, ig: InputGuard, og: OutputGuard) -> dict:
    content = str(case.get("input", ""))
    sanitization = None
    if case["direction"] == "output":
        detections, risk, decision, stages, sanitization, _ms = og.check(content)
    else:
        _norm, detections, risk, decision, stages, _ms = ig.analyze(content)

    return {
        "id": case["id"],
        "direction": case["direction"],
        "category": case["category"],
        "input": content,
        "description": case.get("description") or "",
        "expected_decision": case["expected_decision"],
        "decision": decision.decision.value,
        "reason": decision.reason,
        "risk": risk.score,
        "risk_level": risk.level.value,
        "contributors": list(risk.contributors),
        "detections": [dump_detector(d) for d in detections if d.detected],
        "stages": [
            {"name": s.name, "status": s.status.value,
             "latency_ms": round(s.latency_ms, 3), "risk": s.risk,
             "decision": s.decision.value if s.decision else None,
             "detail": s.detail}
            for s in stages
        ],
        "sanitized_text": sanitization.sanitized_text if sanitization else None,
        "verified_clean": sanitization.verified_clean if sanitization else None,
    }


def main() -> None:
    ig, og = InputGuard(), OutputGuard()
    cases: list[dict] = []
    for yaml_file in sorted(CASES_DIR.glob("*.yaml")):
        loaded = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
        cases.extend(loaded if isinstance(loaded, list) else [loaded])

    categories = []
    for meta in CATEGORIES:
        m = meta["match"]
        selected = [c for c in cases
                    if c.get("direction") == m["direction"]
                    and c.get("category") == m["category"]]
        results = [run_case(c, ig, og) for c in selected]
        passed = sum(1 for r in results if r["decision"] == r["expected_decision"])
        categories.append(
            {**{k: v for k, v in meta.items() if k != "match"},
             "cases": results, "passed": passed, "total": len(results)}
        )

    total = sum(c["total"] for c in categories)
    passed = sum(c["passed"] for c in categories)
    doc = {"summary": {"total": total, "passed": passed},
           "categories": categories}
    OUT_PATH.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    print(f"wrote {OUT_PATH} — {passed}/{total} cases passed")


if __name__ == "__main__":
    main()