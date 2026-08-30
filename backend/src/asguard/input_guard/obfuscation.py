"""Obfuscation detector."""

from __future__ import annotations

import time

from asguard.input_guard.detectors import InputDetector, _elapsed_ms
from asguard.normalization import NormalizedInput
from asguard.security_models.enums import Severity, ThreatCategory
from asguard.security_models.models import DetectorResult


class ObfuscationDetector(InputDetector):
    name = "obfuscation"
    category = ThreatCategory.OBFUSCATION
    severity = Severity.MEDIUM

    def detect(self, content: NormalizedInput) -> DetectorResult:
        start = time.perf_counter()
        signals: list[str] = []
        score = 0.0
        if "invisible_characters_removed" in content.flags:
            signals.append("invisible_characters")
            score += 0.6
        if "separated_letters" in content.flags:
            signals.append("separated_letters")
            score += 0.6
        if "base64_like_blob" in content.flags:
            signals.append("base64_like_blob")
            score += 0.5
        if content.visible_char_ratio < 0.95:
            score += (0.95 - content.visible_char_ratio) * 4
        if content.normalized != content.original.strip().lower():
            signals.append("normalization_changed_content")
            score += 0.2
        detected = score >= 0.4
        return self._result(
            detected=detected,
            confidence=min(score, 1.0),
            signals=signals,
            latency_ms=_elapsed_ms(start),
        )
