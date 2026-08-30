"""Input threat detectors.

Detectors are deterministic, rule/pattern-based, and cheap. They provide
evidence (``DetectorResult``) — they never make the final decision.
"""

from __future__ import annotations

import re
import time
from abc import ABC, abstractmethod

from asguard.normalization import NormalizedInput
from asguard.security_models.enums import Severity, ThreatCategory
from asguard.security_models.models import DetectorResult


def _elapsed_ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 3)


class InputDetector(ABC):
    """Base class for input detectors."""

    name: str = "detector"
    category: ThreatCategory
    severity: Severity = Severity.MEDIUM

    @abstractmethod
    def detect(self, content: NormalizedInput) -> DetectorResult: ...

    def _result(
        self,
        detected: bool,
        confidence: float,
        signals: list[str],
        latency_ms: float = 0.0,
    ) -> DetectorResult:
        return DetectorResult(
            detector=self.name,
            category=self.category,
            detected=detected,
            confidence=round(min(max(confidence, 0.0), 1.0), 3),
            severity=self.severity,
            signals=signals,
            latency_ms=latency_ms,
        )


class PatternDetector(InputDetector):
    """A detector driven by a list of (regex, signal, confidence) patterns.

    Patterns are matched against the normalized text and, additionally, a set
    of ``condensed_patterns`` is matched against the fully-condensed text to
    catch letter-separated obfuscation (e.g. "i g n o r e ...").
    """

    patterns: list[tuple[str, str, float]] = []
    condensed_patterns: list[tuple[str, str, float]] = []

    def detect(self, content: NormalizedInput) -> DetectorResult:
        start = time.perf_counter()
        text = content.normalized
        signals: list[str] = []
        max_conf = 0.0
        for pattern_str, signal, conf in self.patterns:
            if re.search(pattern_str, text):
                signals.append(signal)
                max_conf = max(max_conf, conf)
        for pattern_str, signal, conf in self.condensed_patterns:
            if re.search(pattern_str, content.condensed):
                if signal not in signals:
                    signals.append(signal)
                max_conf = max(max_conf, conf)
        if len(signals) >= 2:
            max_conf = min(1.0, max_conf + 0.05)
        return self._result(
            detected=bool(signals), confidence=max_conf, signals=signals, latency_ms=_elapsed_ms(start)
        )
