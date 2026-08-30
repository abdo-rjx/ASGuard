"""Default settings document and validation.

Settings are stored in ASGuard's own metadata database and exposed via the
Settings page. All values have safe defaults.
"""

from __future__ import annotations

DEFAULT_SETTINGS: dict = {
    "security_thresholds": {
        "block_threshold": 70,
        "review_threshold": 40,
    },
    "logging": {
        "log_level": "INFO",
        "log_security_events": True,
    },
    "privacy": {
        "store_raw_content": False,  # never recommended; supported only for explicit opt-in per app
        "retention_days": 30,
    },
    "detection": {
        "detector_failure_mode": "fail_closed",  # fail_closed | fail_open
    },
    "upstream": {
        "timeout_seconds": 60,
    },
    "redaction": {
        "style": "placeholder",  # placeholder (fixed) — deterministic by design
    },
}

_VALID_ENUMS = {
    ("detection", "detector_failure_mode"): {"fail_closed", "fail_open"},
    ("logging", "log_level"): {"DEBUG", "INFO", "WARNING", "ERROR"},
    ("redaction", "style"): {"placeholder"},
}


def merge_defaults(stored: dict) -> dict:
    """Merge stored settings over defaults (deep, two levels)."""
    merged = {**{k: dict(v) if isinstance(v, dict) else v for k, v in DEFAULT_SETTINGS.items()}}
    for section, values in (stored or {}).items():
        if section not in merged:
            continue
        if isinstance(values, dict) and isinstance(merged[section], dict):
            merged[section].update(values)
        else:
            merged[section] = values
    return merged


def validate_settings(data: dict) -> list[str]:
    """Return a list of validation errors (empty = valid)."""
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["settings must be an object"]

    thresholds = data.get("security_thresholds")
    if isinstance(thresholds, dict):
        for key in ("block_threshold", "review_threshold"):
            value = thresholds.get(key)
            if value is not None and not (isinstance(value, int) and 0 <= value <= 100):
                errors.append(f"security_thresholds.{key} must be an integer between 0 and 100")
        block = thresholds.get("block_threshold")
        review = thresholds.get("review_threshold")
        if isinstance(block, int) and isinstance(review, int) and review > block:
            errors.append("review_threshold must be <= block_threshold")

    privacy = data.get("privacy")
    if isinstance(privacy, dict):
        retention = privacy.get("retention_days")
        if retention is not None and (not isinstance(retention, int) or not (1 <= retention <= 3650)):
            errors.append("privacy.retention_days must be between 1 and 3650")
        if privacy.get("store_raw_content") is True:
            errors.append(
                "privacy.store_raw_content must remain false — ASGuard does not store raw prompts/responses"
            )

    for (section, key), allowed in _VALID_ENUMS.items():
        value = (data.get(section) or {}).get(key)
        if value is not None and value not in allowed:
            errors.append(f"{section}.{key} must be one of: {', '.join(sorted(allowed))}")

    upstream = data.get("upstream")
    if isinstance(upstream, dict):
        timeout = upstream.get("timeout_seconds")
        if timeout is not None and (not isinstance(timeout, (int, float)) or not (1 <= timeout <= 600)):
            errors.append("upstream.timeout_seconds must be between 1 and 600")

    return errors
