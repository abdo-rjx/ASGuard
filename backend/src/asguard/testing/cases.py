"""Security test case model and YAML loading."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class SecurityTestCase:
    id: str
    direction: str  # input | output
    category: str
    input: str
    expected_decision: str  # ALLOW | BLOCK | SANITIZE
    minimum_risk: int = 0
    description: str = ""


def load_cases(directory: str | Path) -> list[SecurityTestCase]:
    """Load all YAML test case files from a directory."""
    cases: list[SecurityTestCase] = []
    base = Path(directory)
    if not base.exists():
        return cases
    for path in sorted(base.glob("*.yaml")):
        data = yaml.safe_load(path.read_text())
        entries = data if isinstance(data, list) else [data]
        for entry in entries:
            if not isinstance(entry, dict) or "id" not in entry:
                continue
            cases.append(
                SecurityTestCase(
                    id=str(entry["id"]),
                    direction=str(entry.get("direction", "input")),
                    category=str(entry.get("category", "unknown")),
                    input=str(entry.get("input", "")),
                    expected_decision=str(entry.get("expected_decision", "ALLOW")).upper(),
                    minimum_risk=int(entry.get("minimum_risk", 0)),
                    description=str(entry.get("description", "")),
                )
            )
    return cases
