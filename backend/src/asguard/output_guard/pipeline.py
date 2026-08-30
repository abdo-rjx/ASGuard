"""Output security pipeline: parse → detect → score → policy → sanitize → verify."""

from __future__ import annotations

import time

from asguard.output_guard.detectors import (
    ApiKeyDetector,
    OutputDetector,
    PasswordDetector,
    TokenDetector,
)
from asguard.output_guard.pii_detectors import (
    ConfidentialDetector,
    EmailDetector,
    FinancialDetector,
    PhoneDetector,
)
from asguard.output_guard.sanitizer import Sanitizer
from asguard.policy.engine import PolicyEngine
from asguard.risk.engine import RiskEngine
from asguard.security_models.enums import Decision, Direction, StageStatus
from asguard.security_models.models import (
    DetectionSpan,
    DetectorResult,
    PipelineStageTrace,
    PolicyDecision,
    RiskAssessment,
    SanitizationResult,
)


def default_output_detectors() -> list[OutputDetector]:
    return [
        ApiKeyDetector(),
        PasswordDetector(),
        TokenDetector(),
        PhoneDetector(),
        EmailDetector(),
        FinancialDetector(),
        ConfidentialDetector(),
    ]


class OutputGuard:
    """Runs the full output security pipeline on AI-generated content."""

    def __init__(
        self,
        risk_engine: RiskEngine | None = None,
        policy_engine: PolicyEngine | None = None,
        sanitizer: Sanitizer | None = None,
        detectors: list[OutputDetector] | None = None,
        detector_failure_mode: str = "fail_closed",
    ) -> None:
        self.risk_engine = risk_engine or RiskEngine()
        self.policy_engine = policy_engine or PolicyEngine()
        self.sanitizer = sanitizer or Sanitizer()
        self.detectors = detectors if detectors is not None else default_output_detectors()
        self.detector_failure_mode = detector_failure_mode

    def check(
        self, content: str
    ) -> tuple[
        list[DetectorResult],
        RiskAssessment,
        PolicyDecision,
        list[PipelineStageTrace],
        SanitizationResult | None,
        float,
    ]:
        """Run parse → detect → score → policy → (sanitize) → verify.

        Returns (detections, risk, decision, stages, sanitization, total_ms).
        ``sanitization`` is not None only when content was modified.
        """
        stages: list[PipelineStageTrace] = []
        total_start = time.perf_counter()

        # 1. Parse (extract the text payload to inspect)
        t0 = time.perf_counter()
        stages.append(
            PipelineStageTrace(
                name="Response Parsing",
                status=StageStatus.OK,
                latency_ms=_ms(t0),
                detail=f"{len(content)} chars",
            )
        )

        # 2. Detection
        t0 = time.perf_counter()
        results: list[DetectorResult] = []
        detector_errors = 0
        for detector in self.detectors:
            try:
                results.append(detector.detect(content))
            except Exception as exc:
                detector_errors += 1
                results.append(
                    DetectorResult(
                        detector=detector.name, category=detector.category, detected=False, error=str(exc)
                    )
                )
        fired = sum(1 for r in results if r.detected)
        stages.append(
            PipelineStageTrace(
                name="Output Detection",
                status=StageStatus.FAILED if detector_errors else StageStatus.OK,
                latency_ms=_ms(t0),
                detail=f"{fired}/{len(results)} detectors fired",
            )
        )

        # 3. Risk scoring
        t0 = time.perf_counter()
        risk = self.risk_engine.assess(Direction.OUTPUT, results)
        stages.append(
            PipelineStageTrace(name="Output Risk Scoring", status=StageStatus.OK, latency_ms=_ms(t0), risk=risk.score)
        )

        # 4. Policy
        t0 = time.perf_counter()
        decision = self.policy_engine.evaluate(Direction.OUTPUT, risk, results)
        stages.append(
            PipelineStageTrace(name="Output Policy", latency_ms=_ms(t0), decision=decision.decision,
                               detail=decision.reason)
        )

        # 5. Sanitization (only if policy requires it)
        sanitization: SanitizationResult | None = None
        if decision.decision == Decision.SANITIZE:
            t0 = time.perf_counter()
            spans: list[DetectionSpan] = [s for r in results for s in r.spans]
            sanitization = self.sanitizer.sanitize(content, spans, decision.replacement_action)
            stages.append(
                PipelineStageTrace(
                    name="Sanitization",
                    status=StageStatus.SANITIZED,
                    latency_ms=_ms(t0),
                    detail=f"{len(sanitization.changes)} span(s) removed",
                )
            )

            # 6. Final verification — fail closed if sanitization is unsafe.
            if not sanitization.verified_clean:
                decision = PolicyDecision(
                    decision=Decision.BLOCK,
                    reason="sanitization_verification_failed",
                    risk_score=100,
                    triggered_rules=decision.triggered_rules + ["final_verification"],
                )
                stages.append(
                    PipelineStageTrace(
                        name="Final Verification",
                        status=StageStatus.BLOCKED,
                        detail="sensitive content survived sanitization → block",
                    )
                )
            else:
                stages.append(
                    PipelineStageTrace(name="Final Verification", status=StageStatus.OK, detail="verified clean")
                )
        else:
            stages.append(
                PipelineStageTrace(name="Final Verification", status=StageStatus.OK, detail="no modification required")
            )

        if detector_errors and self.detector_failure_mode == "fail_closed":
            decision = PolicyDecision(
                decision=Decision.BLOCK,
                reason="detector_failure_fail_closed",
                risk_score=100,
                triggered_rules=decision.triggered_rules + ["detector_failure"],
            )

        return results, risk, decision, stages, sanitization, _ms(total_start)


def _ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 3)
