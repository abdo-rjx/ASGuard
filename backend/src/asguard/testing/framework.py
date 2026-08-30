"""Security testing framework.

Runs the structured YAML test cases against the live security engine
(input/output pipelines and the deterministic policy engine) and reports
expected vs actual decisions. The same framework backs the Security Testing
page and the pytest regression suite.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

from asguard.input_guard.pipeline import InputGuard
from asguard.output_guard.pipeline import OutputGuard
from asguard.testing.cases import SecurityTestCase, load_cases


def _default_cases_dir() -> Path:
    """Locate the security test corpus robustly (dev tree or installed package)."""
    override = os.environ.get("ASGUARD_TEST_CASES_DIR")
    if override:
        return Path(override)
    # Walk up from this module looking for a `security_test_cases` directory
    # (works in editable/dev installs and in a source checkout).
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "security_test_cases"
        if candidate.exists():
            return candidate
    # Installed-as-package layout: cwd-based fallback (e.g. /app in Docker).
    cwd_candidate = Path.cwd() / "security_test_cases"
    if cwd_candidate.exists():
        return cwd_candidate
    return here.parents[3] / "security_test_cases"  # best-effort fallback


CASES_DIR = _default_cases_dir()


def run_case(case: SecurityTestCase, input_guard: InputGuard, output_guard: OutputGuard) -> dict:
    """Execute one case and return a structured result."""
    start = time.perf_counter()
    if case.direction == "output":
        _detections, risk, decision, _stages, _san, _ms = output_guard.check(case.input)
    else:
        _norm, _detections, risk, decision, _stages, _ms = input_guard.analyze(case.input)
    latency_ms = round((time.perf_counter() - start) * 1000, 2)

    actual = decision.decision.value
    passed = actual == case.expected_decision and risk.score >= case.minimum_risk
    return {
        "id": case.id,
        "direction": case.direction,
        "category": case.category,
        "description": case.description,
        "expected_decision": case.expected_decision,
        "actual_decision": actual,
        "reason": decision.reason,
        "risk_score": risk.score,
        "minimum_risk": case.minimum_risk,
        "passed": passed,
        "latency_ms": latency_ms,
    }


def run_cases(
    cases: list[SecurityTestCase], input_guard: InputGuard, output_guard: OutputGuard
) -> dict:
    """Run all cases and return an aggregated result document."""
    results = [run_case(case, input_guard, output_guard) for case in cases]
    passed = sum(1 for r in results if r["passed"])
    return {
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "results": results,
    }


def default_cases() -> list[SecurityTestCase]:
    return load_cases(CASES_DIR)
