"""Structured logging with automatic secret/sensitive-content redaction.

ASGuard never logs raw prompts or responses. Any string that reaches a log
record passes through the redacting formatter, which masks anything that looks
like a credential, token, or key.
"""

from __future__ import annotations

import logging
import re
import sys
from typing import Any

# Patterns for values that must never reach logs.
_SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_\-]{8,}"),
    re.compile(r"AKIA[0-9A-Z]{12,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9\-]{10,}"),
    re.compile(r"Bearer\s+[A-Za-z0-9._\-]{10,}", re.IGNORECASE),
    re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*\S+"),
]


def redact_secrets(value: str) -> str:
    """Replace anything that looks like a credential with a placeholder."""
    redacted = value
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


class RedactingFormatter(logging.Formatter):
    """Formatter that masks secret-looking substrings in every log record."""

    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        return redact_secrets(message)


def setup_logging(level: str = "INFO") -> None:
    """Configure root logging with the redacting formatter."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        RedactingFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())


def log_event(logger: logging.Logger, level: int, event: str, **fields: Any) -> None:
    """Emit a structured key=value log line (secrets redacted)."""
    parts = [f"event={event}"]
    for key, value in fields.items():
        parts.append(f"{key}={value}")
    logger.log(level, " ".join(parts))
