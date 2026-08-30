"""Output PII / financial / confidential detectors."""

from __future__ import annotations

import re

from asguard.output_guard.detectors import OutputDetector
from asguard.security_models.enums import Severity, ThreatCategory
from asguard.security_models.models import DetectorResult


def _luhn(number: str) -> bool:
    digits = [int(d) for d in number]
    checksum = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    return checksum % 10 == 0


class PhoneDetector(OutputDetector):
    """Detects phone numbers (international and common national formats)."""

    name = "pii_phone"
    label = "phone"
    category = ThreatCategory.PII
    severity = Severity.MEDIUM
    patterns = [
        (r"\+\d{1,3}[\s\-]?\(?\d{1,4}\)?(?:[\s\-]?\d{1,4}){2,6}", 0.85),
        (r"\b\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{4}\b", 0.8),
    ]

    def detect(self, text: str) -> DetectorResult:
        result = super().detect(text)
        # Reduce false positives: require at least 7 digits in the span.
        good_spans = []
        for span in result.spans:
            raw = text[span.start : span.end]
            if sum(ch.isdigit() for ch in raw) >= 7:
                good_spans.append(span)
        result.spans = good_spans
        result.detected = bool(good_spans)
        result.signals = [f"phone x{len(good_spans)}"] if good_spans else []
        return result


class EmailDetector(OutputDetector):
    """Detects email addresses."""

    name = "pii_email"
    label = "email"
    category = ThreatCategory.PII
    severity = Severity.MEDIUM
    patterns = [
        (r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b", 0.95),
    ]


class FinancialDetector(OutputDetector):
    """Detects credit cards (Luhn-validated), IBANs and salary mentions."""

    name = "financial_data"
    label = "financial"
    category = ThreatCategory.FINANCIAL
    severity = Severity.HIGH
    patterns = [
        (r"\b(?:\d[ -]?){13,16}\b", 0.8),
        (r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b", 0.6),
        (r"(?i)\b(salary|wage)\b\s*(?:is|was|of|:|=)?\s*\d[\d,\.]*", 0.85),
    ]

    def detect(self, text: str) -> DetectorResult:
        result = super().detect(text)
        good_spans = []
        for span in result.spans:
            raw = text[span.start : span.end]
            if re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]{11,30}", raw):
                good_spans.append(span)  # IBAN-shaped
            elif "salary" in raw.lower() or "wage" in raw.lower():
                good_spans.append(span)
            else:
                digits = re.sub(r"\D", "", raw)
                if len(digits) in (13, 14, 15, 16) and _luhn(digits):
                    good_spans.append(span)  # Luhn-valid card
        result.spans = good_spans
        result.detected = bool(good_spans)
        result.signals = [f"financial x{len(good_spans)}"] if good_spans else []
        return result


class ConfidentialDetector(OutputDetector):
    """Detects confidentiality markers that indicate restricted content."""

    name = "confidential_data"
    label = "confidential"
    category = ThreatCategory.CONFIDENTIAL
    severity = Severity.HIGH
    patterns = [
        (r"(?i)\b(confidential|internal\s+use\s+only|trade\s+secret|do\s+not\s+distribute|restricted)\b", 0.75),
        (r"(?i)\bclassif(ied|ication)[:=]?\s*(secret|top\s+secret|confidential)\b", 0.9),
    ]
