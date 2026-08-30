"""Deterministic policy engine — the final enforcement layer.

Detectors and the risk engine provide evidence; this engine makes the
decision. Rules are simple, auditable and deterministic:

    direction + category + (risk >= threshold) + enabled → action

Decisions compose with strict precedence: BLOCK > SANITIZE > REVIEW > ALLOW.
"""

from __future__ import annotations

from asguard.security_models.enums import (
    Decision,
    Direction,
    PolicyAction,
    Severity,
    ThreatCategory,
)
from asguard.security_models.models import DetectorResult, PolicyDecision, PolicyRule, RiskAssessment


# ---------------------------------------------------------------------------
# Default policy set (safe defaults; overridable via DB/UI)
# ---------------------------------------------------------------------------

INPUT_POLICY_DEFAULTS: list[PolicyRule] = [
    PolicyRule(direction=Direction.INPUT, category=ThreatCategory.PROMPT_INJECTION,
               action=PolicyAction.BLOCK, threshold=60),
    PolicyRule(direction=Direction.INPUT, category=ThreatCategory.JAILBREAK,
               action=PolicyAction.BLOCK, threshold=70),
    PolicyRule(direction=Direction.INPUT, category=ThreatCategory.SYSTEM_PROMPT_EXTRACTION,
               action=PolicyAction.BLOCK, threshold=65),
    PolicyRule(direction=Direction.INPUT, category=ThreatCategory.SUSPICIOUS_INTENT,
               action=PolicyAction.BLOCK, threshold=60),
    PolicyRule(direction=Direction.INPUT, category=ThreatCategory.OBFUSCATION,
               action=PolicyAction.REVIEW, threshold=60),
]

OUTPUT_POLICY_DEFAULTS: list[PolicyRule] = [
    PolicyRule(direction=Direction.OUTPUT, category=ThreatCategory.SECRET,
               action=PolicyAction.BLOCK, threshold=50),
    PolicyRule(direction=Direction.OUTPUT, category=ThreatCategory.PII,
               action=PolicyAction.SANITIZE, threshold=40),
    PolicyRule(direction=Direction.OUTPUT, category=ThreatCategory.FINANCIAL,
               action=PolicyAction.REDACT, threshold=40),
    PolicyRule(direction=Direction.OUTPUT, category=ThreatCategory.CONFIDENTIAL,
               action=PolicyAction.BLOCK, threshold=50),
]

ALL_POLICY_DEFAULTS: list[PolicyRule] = INPUT_POLICY_DEFAULTS + OUTPUT_POLICY_DEFAULTS

ALLOWED_ACTIONS: dict[Direction, set[PolicyAction]] = {
    Direction.INPUT: {PolicyAction.ALLOW, PolicyAction.BLOCK, PolicyAction.REVIEW},
    Direction.OUTPUT: {PolicyAction.ALLOW, PolicyAction.REDACT, PolicyAction.SANITIZE, PolicyAction.BLOCK},
}


class PolicyEngine:
    """Evaluates a rule set against a risk assessment and detector evidence."""

    def __init__(self, rules: list[PolicyRule] | None = None) -> None:
        self.rules = list(rules) if rules is not None else list(ALL_POLICY_DEFAULTS)

    def set_rules(self, rules: list[PolicyRule]) -> None:
        self.rules = list(rules)

    def evaluate(
        self,
        direction: Direction,
        risk: RiskAssessment,
        results: list[DetectorResult],
    ) -> PolicyDecision:
        triggered: list[str] = []
        sanitize_categories: list[ThreatCategory] = []
        replacement_action = PolicyAction.SANITIZE
        final = Decision.ALLOW
        reason = "no policy triggered"

        for rule in self.rules:
            if rule.direction != direction or not rule.enabled:
                continue
            category_results = [r for r in results if r.category == rule.category and r.detected and not r.error]
            if not category_results:
                continue
            if risk.score < rule.threshold:
                continue

            triggered.append(f"{rule.category.value}:{rule.action.value}")
            if rule.action in (PolicyAction.SANITIZE, PolicyAction.REDACT):
                sanitize_categories.append(rule.category)
                replacement_action = rule.action

            rule_decision = _action_to_decision(rule.action)
            if _precedence(rule_decision) > _precedence(final):
                final = rule_decision
                reason = rule.category.value

        # Ensure sanitization only claims categories whose rule fired.
        if final == Decision.ALLOW and sanitize_categories:
            final = Decision.SANITIZE
            if reason == "no policy triggered":
                reason = "sanitization policy"

        return PolicyDecision(
            decision=final,
            reason=reason,
            risk_score=risk.score,
            triggered_rules=triggered,
            sanitize_categories=sanitize_categories,
            replacement_action=replacement_action,
        )

    def validate_rule(self, rule: PolicyRule) -> list[str]:
        """Return a list of validation errors (empty = valid)."""
        errors: list[str] = []
        if rule.action not in ALLOWED_ACTIONS[rule.direction]:
            errors.append(
                f"action {rule.action.value} is not valid for {rule.direction.value} policies"
            )
        if not (0 <= rule.threshold <= 100):
            errors.append("threshold must be between 0 and 100")
        return errors


def _action_to_decision(action: PolicyAction) -> Decision:
    return {
        PolicyAction.ALLOW: Decision.ALLOW,
        PolicyAction.BLOCK: Decision.BLOCK,
        PolicyAction.REVIEW: Decision.REVIEW,
        PolicyAction.SANITIZE: Decision.SANITIZE,
        PolicyAction.REDACT: Decision.SANITIZE,
    }[action]


def _precedence(decision: Decision) -> int:
    return {
        Decision.ALLOW: 0,
        Decision.REVIEW: 1,
        Decision.SANITIZE: 2,
        Decision.BLOCK: 3,
        Decision.ERROR: 4,
    }[decision]


# Re-exported for convenience in callers that map risk levels to UI colors.
SEVERITY_ORDER = [Severity.LOW, Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL]
