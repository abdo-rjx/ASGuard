"""Output secret detectors (API keys, passwords, tokens).

Detectors scan AI-generated content for secrets. Each detector returns spans
(start/end offsets into the *original* text) so the sanitizer can redact
precisely without rewriting the rest of the response.
"""

from __future__ import annotations

import re
import time
from abc import ABC, abstractmethod

from asguard.security_models.enums import Severity, ThreatCategory
from asguard.security_models.models import DetectionSpan, DetectorResult


def mask_preview(value: str, keep: int = 2) -> str:
    """Middle-mask a value so logs/UI never show full sensitive content."""
    if len(value) <= keep * 2:
        return "*" * len(value)
    return value[:keep] + "*" * (len(value) - keep * 2) + value[-keep:]


class OutputDetector(ABC):
    """Base class for output leak detectors."""

    name: str = "detector"
    label: str = "sensitive"  # span label, e.g. "api_key"
    category: ThreatCategory
    severity: Severity = Severity.HIGH

    #: list of (regex, confidence)
    patterns: list[tuple[str, float]] = []

    def detect(self, text: str) -> DetectorResult:
        start = time.perf_counter()
        spans: list[DetectionSpan] = []
        max_conf = 0.0
        for pattern_str, conf in self.patterns:
            for match in re.finditer(pattern_str, text):
                spans.append(
                    DetectionSpan(
                        category=self.category,
                        label=self.label,
                        start=match.start(),
                        end=match.end(),
                        masked_preview=mask_preview(match.group(0)),
                    )
                )
                max_conf = max(max_conf, conf)
        confidence = min(1.0, max_conf + 0.05 * (len(spans) - 1)) if spans else 0.0
        return DetectorResult(
            detector=self.name,
            category=self.category,
            detected=bool(spans),
            confidence=round(confidence, 3),
            severity=self.severity,
            signals=[f"{self.label} x{len(spans)}"] if spans else [],
            spans=spans,
            latency_ms=round((time.perf_counter() - start) * 1000, 3),
        )


class ApiKeyDetector(OutputDetector):
    """Detects API keys and cloud credentials (sk-…, AKIA…, ghp_…, xox…, etc.)."""

    name = "secret_api_key"
    label = "api_key"
    category = ThreatCategory.SECRET
    severity = Severity.CRITICAL
    patterns = [
        (r"\bsk-[A-Za-z0-9_\-]{16,}\b", 0.98),
        (r"\bAKIA[0-9A-Z]{12,}\b", 0.98),
        (r"\bgh[pousr]_[A-Za-z0-9]{20,}\b", 0.98),
        (r"\bxox[baprs]-[A-Za-z0-9\-]{10,}\b", 0.95),
        (r"\bAIza[0-9A-Za-z_\-]{30,}\b", 0.95),
        (r"(?i)\bapi[_-]?key\s*[:=]\s*['\"]?[A-Za-z0-9_\-\.]{12,}['\"]?", 0.9),
    ]


class PasswordDetector(OutputDetector):
    """Detects plaintext passwords and private key blocks."""

    name = "secret_password"
    label = "password"
    category = ThreatCategory.SECRET
    severity = Severity.CRITICAL
    patterns = [
        (r"(?i)\b(pass(word)?|pwd|passwd)\s*[:=]\s*['\"]?\S{6,}['\"]?", 0.9),
        (r"-----BEGIN (RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----", 0.99),
    ]


class TokenDetector(OutputDetector):
    """Detects bearer tokens, JWTs and session tokens."""

    name = "secret_token"
    label = "token"
    category = ThreatCategory.SECRET
    severity = Severity.HIGH
    patterns = [
        (r"\bBearer\s+[A-Za-z0-9._\-]{16,}\b", 0.95),
        (r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{5,}\b", 0.95),
        (
            r"(?i)\b(access[_-]?token|session[_-]?token|auth[_-]?token|refresh[_-]?token)\s*[:=]\s*['\"]?[A-Za-z0-9._\-]{12,}['\"]?",
            0.9,
        ),
    ]
