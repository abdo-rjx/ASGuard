"""Input security pipeline: normalize → detect → analyze → score → policy."""

from __future__ import annotations

import time

from asguard.input_guard.detectors import InputDetector
from asguard.input_guard.intent import SuspiciousIntentDetector
from asguard.input_guard.jailbreak import JailbreakDetector
from asguard.input_guard.obfuscation import ObfuscationDetector
from asguard.input_guard.prompt_injection import PromptInjectionDetector
from asguard.input_guard.extraction import SystemPromptExtractionDetector
from asguard.logging_setup import log_event
from asguard.normalization import NormalizedInput, normalize
from asguard.policy.engine import PolicyEngine
from asguard.risk.engine import RiskEngine
from asguard.security_models.enums import Decision, Direction, StageStatus
from asguard.security_models.models import (
    DetectorResult,
    PipelineStageTrace,
    PolicyDecision,
    RiskAssessment,
)


def default_input_detectors() -> list[InputDetector]:
    return [
        PromptInjectionDetector(),
        JailbreakDetector(),
        SystemPromptExtractionDetector(),
        ObfuscationDetector(),
        SuspiciousIntentDetector(),
    ]


class InputGuard:
    """Runs the full input security pipeline and returns evidence + decision."""

    def __init__(
        self,
        risk_engine: RiskEngine | None = None,
        policy_engine: PolicyEngine | None = None,
        detectors: list[InputDetector] | None = None,
        detector_failure_mode: str = "fail_closed",
    ) -> None:
        self.risk_engine = risk_engine or RiskEngine()
        self.policy_engine = policy_engine or PolicyEngine()
        self.detectors = detectors if detectors is not None else default_input_detectors()
        self.detector_failure_mode = detector_failure_mode

    def analyze(self, content: str) -> tuple[
        NormalizedInput,
        list[DetectorResult],
        RiskAssessment,
        PolicyDecision,
        list[PipelineStageTrace],
        float,
    ]:
        """Run normalization → detection → risk → policy. Returns full evidence."""
        stages: list[PipelineStageTrace] = []
        total_start = time.perf_counter()

        # 1. Normalization
        t0 = time.perf_counter()
        normalized = normalize(content)
        stages.append(
            PipelineStageTrace(
                name="Normalization",
                status=StageStatus.OK,
                latency_ms=_ms(t0),
                detail=", ".join(normalized.flags) if normalized.flags else "clean",
            )
        )

        # 2. Threat detection
        t0 = time.perf_counter()
        results: list[DetectorResult] = []
        detector_errors = 0
        for detector in self.detectors:
            try:
                results.append(detector.detect(normalized))
            except Exception as exc:  # detector failure must be contained
                detector_errors += 1
                results.append(
                    DetectorResult(
                        detector=detector.name,
                        category=detector.category,
                        detected=False,
                        error=str(exc),
                    )
                )
        detected_any = any(r.detected for r in results)
        stages.append(
            PipelineStageTrace(
                name="Threat Detection",
                status=StageStatus.FAILED if detector_errors else StageStatus.OK,
                latency_ms=_ms(t0),
                detail=f"{sum(1 for r in results if r.detected)}/{len(results)} detectors fired",
            )
        )

        # 3. Intent analysis (evidence summary of the suspicious-intent detector)
        t0 = time.perf_counter()
        intent_signals = [s for r in results if r.category.value == "suspicious_intent" for s in r.signals]
        stages.append(
            PipelineStageTrace(
                name="Intent Analysis",
                status=StageStatus.FLAGGED if intent_signals else StageStatus.OK,
                latency_ms=_ms(t0),
                detail=", ".join(intent_signals) if intent_signals else "no suspicious intent",
            )
        )

        # 4. Risk scoring
        t0 = time.perf_counter()
        risk = self.risk_engine.assess(Direction.INPUT, results)
        stages.append(
            PipelineStageTrace(name="Risk Scoring", status=StageStatus.OK, latency_ms=_ms(t0), risk=risk.score)
        )

        # 5. Policy
        t0 = time.perf_counter()
        decision = self.policy_engine.evaluate(Direction.INPUT, risk, results)
        policy_status = (
            StageStatus.BLOCKED
            if decision.decision == Decision.BLOCK
            else StageStatus.FLAGGED
            if decision.decision == Decision.REVIEW
            else StageStatus.OK
        )
        stages.append(
            PipelineStageTrace(
                name="Policy",
                status=policy_status,
                latency_ms=_ms(t0),
                decision=decision.decision,
                detail=decision.reason,
            )
        )

        if detector_errors and self.detector_failure_mode == "fail_closed":
            decision = PolicyDecision(
                decision=Decision.BLOCK,
                reason="detector_failure_fail_closed",
                risk_score=100,
                triggered_rules=decision.triggered_rules + ["detector_failure"],
            )
            stages[-1].status = StageStatus.BLOCKED
            stages[-1].detail = "detector failure → fail closed"

        total_ms = _ms(total_start)
        return normalized, results, risk, decision, stages, total_ms

    def check(self, content: str) -> tuple[PolicyDecision, list[DetectorResult], RiskAssessment]:
        """Convenience API: run the pipeline and return decision + evidence."""
        _, results, risk, decision, _, _ = self.analyze(content)
        return decision, results, risk


def _ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 3)
