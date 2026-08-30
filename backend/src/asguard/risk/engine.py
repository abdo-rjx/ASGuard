"""Risk engine: converts detector evidence into a single 0..100 risk score.

The aggregation is deterministic (noisy-OR over severity-weighted detector
scores) so identical evidence always produces an identical score.
"""

from __future__ import annotations

import math

from asguard.security_models.enums import Direction, Severity
from asguard.security_models.models import DetectorResult, RiskAssessment


class RiskEngine:
    """Aggregates detector results into a deterministic risk score."""

    def assess(self, direction: Direction, results: list[DetectorResult]) -> RiskAssessment:
        fired = [r for r in results if r.detected and not r.error]
        if not fired:
            return RiskAssessment(
                direction=direction,
                score=0,
                level=Severity.LOW,
                rationale="no threats detected",
            )

        # Noisy-OR: 1 - Π(1 - s_i) over weighted detector scores.
        combined = 1.0 - math.prod(1.0 - r.weighted_score for r in fired)
        score = int(round(min(1.0, combined) * 100))
        contributors = [r.detector for r in fired]
        max_severity = max((r.severity for r in fired), key=lambda s: s.weight)

        level = (
            Severity.CRITICAL
            if score >= 90
            else Severity.HIGH
            if score >= 70
            else Severity.MEDIUM
            if score >= 40
            else Severity.LOW
        )

        rationale = (
            f"{len(fired)} detector(s) fired: {', '.join(contributors)}; "
            f"noisy-OR aggregation → {score}/100 ({level.value})"
        )
        return RiskAssessment(
            direction=direction,
            score=score,
            level=level,
            contributors=contributors,
            rationale=rationale,
        )
