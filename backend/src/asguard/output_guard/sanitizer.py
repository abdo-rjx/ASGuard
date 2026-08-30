"""Deterministic sanitizer.

Removes detected sensitive spans from text without touching anything else.
Two replacement styles:
- REDACT → ``[REDACTED:<TYPE>]``
- SANITIZE → ``[<readable label> removed]``
"""

from __future__ import annotations

import time

from asguard.security_models.enums import PolicyAction
from asguard.security_models.models import (
    DetectionSpan,
    DetectorResult,
    SanitizationResult,
)
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

# Human-readable labels used by SANITIZE replacements.
_READABLE_LABELS = {
    "api_key": "API key",
    "password": "password",
    "token": "token",
    "phone": "phone number",
    "email": "email address",
    "financial": "financial data",
    "confidential": "confidential content",
}


class Sanitizer:
    """Removes sensitive spans deterministically and verifies the result."""

    def __init__(self) -> None:
        self._detectors: list[OutputDetector] = [
            ApiKeyDetector(),
            PasswordDetector(),
            TokenDetector(),
            PhoneDetector(),
            EmailDetector(),
            FinancialDetector(),
            ConfidentialDetector(),
        ]

    def sanitize(self, text: str, spans: list[DetectionSpan], action: PolicyAction) -> SanitizationResult:
        """Remove all spans from text using the requested replacement style."""
        start = time.perf_counter()
        if not spans:
            return SanitizationResult(sanitized_text=text, verified_clean=True)

        placeholder_for = {
            PolicyAction.REDACT: lambda span: f"[REDACTED:{span.label.upper()}]",
            PolicyAction.SANITIZE: lambda span: f"[{_READABLE_LABELS.get(span.label, span.label)} removed]",
        }
        if action not in placeholder_for:
            # Unknown action → safest deterministic replacement.
            action = PolicyAction.REDACT

        # Merge overlapping spans, replace from the end so offsets stay valid.
        merged = _merge_spans(spans)
        result_text = text
        changes = []
        for span in sorted(merged, key=lambda s: s.start, reverse=True):
            replacement = placeholder_for[action](span)
            result_text = result_text[: span.start] + replacement + result_text[span.end :]
            changes.append(
                {
                    "label": span.label,
                    "position": span.start,
                    "masked_preview": span.masked_preview,
                    "replacement": replacement,
                }
            )
        changes.reverse()

        # Final verification: re-run all detectors on the sanitized text.
        remaining: list[DetectorResult] = []
        for detector in self._detectors:
            res = detector.detect(result_text)
            if res.detected:
                remaining.append(res)
        verified_clean = not remaining

        return SanitizationResult(
            sanitized_text=result_text,
            changes=changes,
            remaining_detections=remaining,
            verified_clean=verified_clean,
        )

    def verify(self, text: str) -> SanitizationResult:
        """Final output verification: confirm no sensitive spans remain."""
        remaining = [d for d in (det.detect(text) for det in self._detectors) if d.detected]
        return SanitizationResult(
            sanitized_text=text,
            remaining_detections=remaining,
            verified_clean=not remaining,
        )


def _merge_spans(spans: list[DetectionSpan]) -> list[DetectionSpan]:
    ordered = sorted(spans, key=lambda s: (s.start, s.end))
    merged: list[DetectionSpan] = []
    for span in ordered:
        if merged and span.start <= merged[-1].end:
            prev = merged[-1]
            if span.end > prev.end:
                merged[-1] = DetectionSpan(
                    category=prev.category,
                    label=prev.label,
                    start=prev.start,
                    end=span.end,
                    masked_preview=prev.masked_preview,
                )
        else:
            merged.append(span)
    return merged
