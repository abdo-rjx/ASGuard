"""Jailbreak detector."""

from __future__ import annotations

from asguard.input_guard.detectors import PatternDetector
from asguard.security_models.enums import Severity, ThreatCategory

JAILBREAK_PATTERNS: list[tuple[str, str, float]] = [
    (r"\bdo\s+anything\s+now\b", "dan", 0.95),
    (r"\b(jailbreak|jail\s+break)\b", "jailbreak_term", 0.9),
    (r"\byou\s+have\s+no\s+(restrictions|limits|filters|rules|guardrails)\b", "restriction_denial", 0.9),
    (r"\b(no|without)\s+(restrictions|limits|filters|censorship|guardrails)\b", "restriction_denial", 0.8),
    (r"\bignore\s+(your\s+)?(safety|ethical|moral)\s+(guidelines?|rules?|guardrails?|training)\b", "safety_bypass", 0.92),
    (r"\b(unfiltered|uncensored|unrestricted)\s+(mode|model|ai|response|version)\b", "unfiltered_mode", 0.85),
    (r"\bpretend\s+(you\s+are|to\s+be)\s+.*(no\s+rules|unrestricted|unfiltered|evil|amoral)", "roleplay_bypass", 0.8),
    (r"\bin\s+(this|the)\s+(hypothetical|fictional)\s+(scenario|story|roleplay).*(anything|no\s+rules|illegal|without\s+limits)", "fictional_framing", 0.7),
    (r"\b(act|behave)\s+as\s+(if\s+)?(you\s+)?(have|had)\s+no\s+(rules|limits|restrictions)\b", "roleplay_bypass", 0.85),
    (r"\benable\s+(developer|god|dan)\s+mode\b", "mode_switch", 0.9),
]


class JailbreakDetector(PatternDetector):
    name = "jailbreak"
    category = ThreatCategory.JAILBREAK
    severity = Severity.HIGH
    patterns = JAILBREAK_PATTERNS
