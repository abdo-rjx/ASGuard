"""Suspicious intent analyzer (rule-based)."""

from __future__ import annotations

from asguard.input_guard.detectors import PatternDetector
from asguard.security_models.enums import Severity, ThreatCategory

INTENT_PATTERNS: list[tuple[str, str, float]] = [
    (
        r"\b(exfiltrat|send|upload|post|forward|transmit)\b.*\b(data|records|customer|credential|password|token|key|file|database)\b",
        "data_exfiltration",
        0.85,
    ),
    (
        r"\b(https?://|webhook)\S*\b.*\b(send|post|upload|forward)\b|\b(send|post|upload|forward)\b.*\b(https?://|webhook)\S*\b",
        "external_transmission",
        0.8,
    ),
    (r"\b(drop\s+table|delete\s+from|truncate\s+table|rm\s+-rf|format\s+c:)\b", "destructive_command", 0.85),
    (
        r"\b(credential|password|secret|api\s*key|token)s?\b.*\b(steal|harvest|collect|grab|extract|list\s+all)\b|\b(steal|harvest|collect|grab|extract)\b.*\b(credential|password|secret|api\s*key|token)s?\b",
        "credential_harvesting",
        0.9,
    ),
    (r"\b(malware|ransomware|keylogger|backdoor|exploit|payload)\b", "malware_terms", 0.6),
    (
        r"\b(bypass|evade)\b.*\b(detection|authentication|authorization|security|firewall)\b",
        "security_evasion",
        0.8,
    ),
    (
        r"\b(personal\s+data|ssn|social\s+security|credit\s+card)\b.*\b(all|list|every|dump|extract|find)\b|\b(all|list|every|dump|extract|find)\b.*\b(personal\s+data|ssn|social\s+security|credit\s+card)",
        "pii_harvesting",
        0.8,
    ),
]


class SuspiciousIntentDetector(PatternDetector):
    name = "suspicious_intent"
    category = ThreatCategory.SUSPICIOUS_INTENT
    severity = Severity.MEDIUM
    patterns = INTENT_PATTERNS
