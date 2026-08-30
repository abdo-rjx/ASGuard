"""Policy engine unit tests."""

from asguard.policy.engine import ALLOWED_ACTIONS, PolicyEngine
from asguard.risk.engine import RiskEngine
from asguard.security_models.enums import Direction, PolicyAction, Severity, ThreatCategory
from asguard.security_models.models import DetectorResult, PolicyRule


def _fired(category: ThreatCategory, confidence: float = 0.95) -> DetectorResult:
    return DetectorResult(
        detector="t", category=category, detected=True,
        confidence=confidence, severity=Severity.HIGH,
    )


def _risk(results):
    return RiskEngine().assess(Direction.INPUT, results)


class TestInputPolicy:
    def test_prompt_injection_blocked(self):
        results = [_fired(ThreatCategory.PROMPT_INJECTION)]
        decision = PolicyEngine().evaluate(Direction.INPUT, _risk(results), results)
        assert decision.decision.value == "BLOCK"
        assert decision.reason == "prompt_injection"

    def test_below_threshold_not_triggered(self):
        # confidence low enough that risk < 60 threshold
        results = [_fired(ThreatCategory.OBFUSCATION, confidence=0.5)]
        decision = PolicyEngine().evaluate(Direction.INPUT, _risk(results), results)
        assert decision.decision.value == "ALLOW"

    def test_disabled_rule_ignored(self):
        rules = [PolicyRule(direction=Direction.INPUT, category=ThreatCategory.PROMPT_INJECTION,
                            action=PolicyAction.BLOCK, threshold=0, enabled=False)]
        results = [_fired(ThreatCategory.PROMPT_INJECTION)]
        decision = PolicyEngine(rules=rules).evaluate(Direction.INPUT, _risk(results), results)
        assert decision.decision.value == "ALLOW"


class TestOutputPolicy:
    def test_secret_blocked(self):
        results = [_fired(ThreatCategory.SECRET, confidence=0.98)]
        risk = RiskEngine().assess(Direction.OUTPUT, results)
        decision = PolicyEngine().evaluate(Direction.OUTPUT, risk, results)
        assert decision.decision.value == "BLOCK"

    def test_pii_sanitized(self):
        results = [_fired(ThreatCategory.PII, confidence=0.85)]
        risk = RiskEngine().assess(Direction.OUTPUT, results)
        decision = PolicyEngine().evaluate(Direction.OUTPUT, risk, results)
        assert decision.decision.value == "SANITIZE"
        assert decision.replacement_action == PolicyAction.SANITIZE

    def test_financial_redacted(self):
        results = [_fired(ThreatCategory.FINANCIAL, confidence=0.85)]
        risk = RiskEngine().assess(Direction.OUTPUT, results)
        decision = PolicyEngine().evaluate(Direction.OUTPUT, risk, results)
        assert decision.decision.value == "SANITIZE"
        assert decision.replacement_action == PolicyAction.REDACT


class TestPrecedenceAndValidation:
    def test_block_wins_over_sanitize(self):
        results = [
            _fired(ThreatCategory.SECRET, confidence=0.98),
            _fired(ThreatCategory.PII, confidence=0.85),
        ]
        risk = RiskEngine().assess(Direction.OUTPUT, results)
        decision = PolicyEngine().evaluate(Direction.OUTPUT, risk, results)
        assert decision.decision.value == "BLOCK"
        assert decision.triggered_rules  # both recorded

    def test_action_validation_per_direction(self):
        assert PolicyAction.REDACT in ALLOWED_ACTIONS[Direction.OUTPUT]
        assert PolicyAction.REDACT not in ALLOWED_ACTIONS[Direction.INPUT]
        assert PolicyAction.BLOCK in ALLOWED_ACTIONS[Direction.INPUT]

    def test_validate_rule_rejects_bad_action(self):
        engine = PolicyEngine()
        rule = PolicyRule(direction=Direction.INPUT, category=ThreatCategory.PII,
                          action=PolicyAction.REDACT)
        errors = engine.validate_rule(rule)
        assert errors
