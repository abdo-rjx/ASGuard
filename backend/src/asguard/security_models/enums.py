"""Core security enums shared by input and output pipelines."""

from __future__ import annotations

from enum import Enum


class Direction(str, Enum):
    INPUT = "input"
    OUTPUT = "output"


class Decision(str, Enum):
    """Final decision made by the deterministic policy engine."""

    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    SANITIZE = "SANITIZE"
    REVIEW = "REVIEW"
    ERROR = "ERROR"


class PolicyAction(str, Enum):
    """Actions a single policy rule may request."""

    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    REVIEW = "REVIEW"
    REDACT = "REDACT"
    SANITIZE = "SANITIZE"


class Severity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

    @property
    def weight(self) -> float:
        return {
            Severity.LOW: 0.45,
            Severity.MEDIUM: 0.70,
            Severity.HIGH: 0.90,
            Severity.CRITICAL: 1.0,
        }[self]


class ThreatCategory(str, Enum):
    """Categories of threats detectable in either direction."""

    # Input threats
    PROMPT_INJECTION = "prompt_injection"
    JAILBREAK = "jailbreak"
    SYSTEM_PROMPT_EXTRACTION = "system_prompt_extraction"
    OBFUSCATION = "obfuscation"
    SUSPICIOUS_INTENT = "suspicious_intent"
    # Output leaks
    SECRET = "secret"
    PII = "pii"
    FINANCIAL = "financial"
    CONFIDENTIAL = "confidential"


class StageStatus(str, Enum):
    PENDING = "PENDING"
    OK = "OK"
    SKIPPED = "SKIPPED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    SANITIZED = "SANITIZED"
    FLAGGED = "FLAGGED"
