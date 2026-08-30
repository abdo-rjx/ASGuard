"""Prompt injection detector."""

from __future__ import annotations

from asguard.input_guard.detectors import PatternDetector
from asguard.security_models.enums import Severity, ThreatCategory

PROMPT_INJECTION_PATTERNS: list[tuple[str, str, float]] = [
    (
        r"\bignore\s+(all\s+|any\s+|the\s+)?(previous|prior|above|earlier|preceding)\s+(instructions?|prompts?|rules?|directions?)\b",
        "instruction_override",
        0.95,
    ),
    (
        r"\bdisregard\s+(all\s+|any\s+|the\s+)?(previous|prior|above|your)\s+(instructions?|rules?|prompts?|guidelines?|training)\b",
        "instruction_override",
        0.95,
    ),
    (
        r"\bforget\s+(all\s+|everything|the\s+)?(previous|prior|above|your)\s+(instructions?|rules?|prompts?|training)\b",
        "instruction_override",
        0.9,
    ),
    (
        r"\b(you\s+are\s+now|from\s+now\s+on\s+you\s+are|new\s+instructions?:)\b",
        "identity_reassignment",
        0.75,
    ),
    (
        r"\boverride\s+(your\s+)?(safety|rules|instructions|guidelines|programming)\b",
        "safety_override",
        0.9,
    ),
    (
        r"\b(your\s+)?(real|true|actual)\s+(instructions?|prompt|purpose)\s+(are|is)\b",
        "instruction_probing",
        0.7,
    ),
    (
        r"\bi\s+am\s+(your\s+)?(developer|administrator|creator|owner|system)\b",
        "authority_claim",
        0.7,
    ),
    (
        r"\b(admin|developer|debug|system|maintenance)\s+(mode|message)\b",
        "authority_claim",
        0.65,
    ),
    (
        r"\b(reveal|show|print|output|repeat)\s+(me\s+)?(the\s+)?(text|content|words?)\s+(above|before|prior|in\s+your\s+prompt)\b",
        "context_leak_attempt",
        0.8,
    ),
    (
        r"\b(add|append)\s+(this\s+)?(sentence|instruction|line)\s+(to|in)\s+(your|the)\s+(prompt|instructions|memory)\b",
        "instruction_injection",
        0.8,
    ),
]


class PromptInjectionDetector(PatternDetector):
    name = "prompt_injection"
    category = ThreatCategory.PROMPT_INJECTION
    severity = Severity.HIGH
    patterns = PROMPT_INJECTION_PATTERNS
    condensed_patterns = [
        (r"ignoreall(?:previous|prior|earlier)", "instruction_override_condensed", 0.9),
        (r"ignore(?:previous|prior)instructions", "instruction_override_condensed", 0.9),
        (r"disregard(?:all)?(?:previous|prior|your)", "instruction_override_condensed", 0.9),
        (r"forget(?:all|everything)?(?:previous|prior)", "instruction_override_condensed", 0.85),
        (r"reveal(?:your)?systemprompt", "extraction_condensed", 0.9),
        (r"whatisyoursystemprompt", "extraction_condensed", 0.85),
    ]
