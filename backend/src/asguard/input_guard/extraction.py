"""System prompt extraction detector."""

from __future__ import annotations

from asguard.input_guard.detectors import PatternDetector
from asguard.security_models.enums import Severity, ThreatCategory

EXTRACTION_PATTERNS: list[tuple[str, str, float]] = [
    (
        r"\b(system|initial|original|hidden|secret|first)\s+(prompt|instructions?|message)\b",
        "system_prompt_reference",
        0.75,
    ),
    (
        r"\b(reveal|show|print|display|repeat|output|give|share|leak|expose)\s+(me\s+)?(your\s+|the\s+)?(system\s+prompt|initial\s+instructions?|hidden\s+instructions?|full\s+prompt)",
        "extraction_request",
        0.95,
    ),
    (
        r"\bwhat\s+(are|is)\s+(your\s+)?(system\s+prompt|initial\s+instructions?|instructions\s+you\s+were\s+given)",
        "extraction_question",
        0.9,
    ),
    (
        r"\brepeat\s+(everything|all|the\s+text|the\s+words)\s+(above|before|so\s+far|in\s+your\s+prompt)",
        "echo_request",
        0.85,
    ),
    (
        r"\bverbatim\b.*\b(instructions|prompt)\b|\b(instructions|prompt)\b.*\bverbatim\b",
        "verbatim_request",
        0.7,
    ),
    (
        r"\byour\s+(config|configuration|directives?)\b.*\b(show|list|print|reveal|tell)\b|\b(show|list|print|reveal|tell)\b.*\byour\s+(config|configuration|directives?)\b",
        "config_probe",
        0.65,
    ),
]


class SystemPromptExtractionDetector(PatternDetector):
    name = "system_prompt_extraction"
    category = ThreatCategory.SYSTEM_PROMPT_EXTRACTION
    severity = Severity.HIGH
    patterns = EXTRACTION_PATTERNS
