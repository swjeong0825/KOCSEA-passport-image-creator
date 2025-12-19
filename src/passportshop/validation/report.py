from __future__ import annotations

from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class RuleResult:
    """
    Result of a single validation rule.
    """
    rule_id: str
    passed: bool
    message: str
    metrics: dict[str, Any] | None = None

@dataclass(frozen=True)
class ValidationReport:
    """
    Collection of validation rule results for a processed photo.
    """
    passed: bool
    results: list[RuleResult]
