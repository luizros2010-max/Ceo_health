"""Deterministic validators + confidence composition.

These are the safety net behind the LLM proposer: catch hallucinated values
(value-in-source check), implausible numbers, broken ranges, and impossible dates.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from ..textnorm import normalize_alias


@dataclass
class ValidationResult:
    ok: bool
    penalties: float  # subtracted from confidence (0..1)
    issues: list[str] = field(default_factory=list)


def value_in_source(value_raw: str | None, source_text: str | None) -> bool:
    """Does the raw value literally appear in the page text? Catches hallucination."""
    if not value_raw or not source_text:
        return False
    needle = value_raw.strip().replace(" ", "")
    hay = source_text.replace(" ", "")
    if needle in hay:
        return True
    # Tolerate decimal comma/point differences.
    return needle.replace(",", ".") in hay.replace(",", ".")


def validate_row(
    *,
    value_raw: str | None,
    value_num: float | None,
    source_text_snippet: str | None,
    full_text: str | None,
    ref_low: float | None,
    ref_high: float | None,
    collection_date: date | None,
    birth_date: date | None,
    today: date | None = None,
) -> ValidationResult:
    today = today or date.today()
    issues: list[str] = []
    penalty = 0.0

    # 1) value-in-source (check snippet first, then whole document).
    haystack = source_text_snippet or full_text
    if value_raw and not value_in_source(value_raw, haystack):
        issues.append("value_not_in_source")
        penalty += 0.5

    # 2) reference range sanity.
    if ref_low is not None and ref_high is not None and ref_low >= ref_high:
        issues.append("ref_low_ge_ref_high")
        penalty += 0.2

    # 3) plausibility: non-negative numeric values for typical labs.
    if value_num is not None and value_num < 0:
        issues.append("negative_value")
        penalty += 0.3

    # 4) date sanity.
    if collection_date is not None:
        if collection_date > today:
            issues.append("collection_date_in_future")
            penalty += 0.4
        if birth_date is not None and collection_date < birth_date:
            issues.append("collection_date_before_birth")
            penalty += 0.4

    ok = "value_not_in_source" not in issues
    return ValidationResult(ok=ok, penalties=min(penalty, 1.0), issues=issues)


def compose_confidence(model_conf: float, match_conf: float, penalties: float) -> float:
    """Blend model confidence + name-match confidence, then apply validation penalties."""
    base = 0.5 * float(model_conf or 0.0) + 0.5 * float(match_conf or 0.0)
    return max(0.0, min(1.0, base - penalties))
