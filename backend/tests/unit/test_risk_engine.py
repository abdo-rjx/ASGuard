"""Risk engine unit tests."""

from asguard.risk.engine import RiskEngine
from asguard.security_models.enums import Direction, Severity, ThreatCategory
from asguard.security_models.models import DetectorResult


def _result(detector: str, category: ThreatCategory, confidence: float,
            severity: Severity = Severity.HIGH, detected: bool = True) -> DetectorResult:
    return DetectorResult(
        detector=detector, category=category, detected=detected,
        confidence=confidence, severity=severity,
    )


def test_no_detections_zero_risk():
    risk = RiskEngine().assess(Direction.INPUT, [_result("x", ThreatCategory.PII, 0.9, detected=False)])
    assert risk.score == 0
    assert risk.level == Severity.LOW


def test_single_detector_score():
    risk = RiskEngine().assess(Direction.INPUT, [_result("d", ThreatCategory.PROMPT_INJECTION, 0.95, Severity.HIGH)])
    expected = round(0.95 * 0.90 * 100)
    assert risk.score == expected
    assert risk.level == Severity.HIGH


def test_multiple_detectors_aggregate_higher_than_any_single():
    a = _result("a", ThreatCategory.PROMPT_INJECTION, 0.6, Severity.HIGH)
    b = _result("b", ThreatCategory.JAILBREAK, 0.6, Severity.MEDIUM)
    single = RiskEngine().assess(Direction.INPUT, [a])
    both = RiskEngine().assess(Direction.INPUT, [a, b])
    assert both.score > single.score
    assert both.score <= 100


def test_score_deterministic():
    results = [_result("a", ThreatCategory.PROMPT_INJECTION, 0.8, Severity.HIGH)]
    assert RiskEngine().assess(Direction.INPUT, results).score == RiskEngine().assess(Direction.INPUT, results).score


def test_critical_severity_weight():
    risk = RiskEngine().assess(Direction.OUTPUT, [_result("s", ThreatCategory.SECRET, 0.98, Severity.CRITICAL)])
    assert risk.score >= 90
