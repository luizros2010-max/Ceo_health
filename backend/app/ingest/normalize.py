"""Normalization: map raw analyte names to canonical biomarkers + convert units.

Exact accent-folded alias match -> confidence 1.0. Miss -> rapidfuzz fuzzy match ->
lower confidence + needs_review. Unit conversion is per-biomarker (analyte-specific).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from rapidfuzz import fuzz, process
from sqlmodel import Session, select

from ..models import Biomarker, BiomarkerAlias, UnitConversion
from ..textnorm import normalize_alias

FUZZY_ACCEPT = 88  # >= this score -> accept as a (lower-confidence) match
FUZZY_FLOOR = 70   # below this -> leave unmapped


@dataclass
class MatchResult:
    biomarker: Optional[Biomarker]
    match_confidence: float  # 0..1 contribution from name match
    method: str  # 'exact_alias' | 'fuzzy_alias' | 'none'


def match_biomarker(session: Session, raw_name: str) -> MatchResult:
    norm = normalize_alias(raw_name)
    if not norm:
        return MatchResult(None, 0.0, "none")

    # 1) exact alias.
    alias = session.exec(
        select(BiomarkerAlias).where(BiomarkerAlias.alias_text == norm)
    ).first()
    if alias:
        biomarker = session.get(Biomarker, alias.biomarker_id)
        return MatchResult(biomarker, 1.0, "exact_alias")

    # 2) fuzzy alias.
    aliases = session.exec(select(BiomarkerAlias)).all()
    if not aliases:
        return MatchResult(None, 0.0, "none")
    choices = {a.alias_text: a.biomarker_id for a in aliases}
    best = process.extractOne(norm, list(choices.keys()), scorer=fuzz.WRatio)
    if best and best[1] >= FUZZY_FLOOR:
        score = best[1]
        biomarker = session.get(Biomarker, choices[best[0]])
        # Scale into a 0..1 confidence; >=FUZZY_ACCEPT gets a healthy score.
        conf = min(0.95, score / 100.0)
        method = "fuzzy_alias" if score >= FUZZY_ACCEPT else "fuzzy_weak"
        return MatchResult(biomarker, conf, method)

    return MatchResult(None, 0.0, "none")


@dataclass
class Converted:
    value_num: Optional[float]
    canonical_unit: Optional[str]
    converted: bool
    note: Optional[str] = None


def convert_value(
    session: Session,
    biomarker: Biomarker,
    value: Optional[float],
    unit_raw: Optional[str],
) -> Converted:
    """Convert value into the biomarker's canonical unit when possible."""
    if value is None:
        return Converted(None, biomarker.canonical_unit, False)

    canonical = biomarker.canonical_unit
    if not unit_raw or _same_unit(unit_raw, canonical):
        return Converted(value, canonical, True)

    conv = session.exec(
        select(UnitConversion).where(
            UnitConversion.biomarker_id == biomarker.id,
            UnitConversion.to_unit == canonical,
        )
    ).all()
    for c in conv:
        if _same_unit(c.from_unit, unit_raw):
            return Converted(value * c.factor + c.offset, canonical, True)

    # Unknown unit — keep the raw value but flag that no conversion was applied.
    return Converted(value, canonical, False, note=f"no conversion for unit '{unit_raw}'")


def _same_unit(a: str, b: str) -> bool:
    def k(u: str) -> str:
        return normalize_alias(u).replace(" ", "")
    return k(a) == k(b)


def parse_reference_range(ref_raw: Optional[str]) -> tuple[Optional[float], Optional[float]]:
    """Best-effort parse of a textual reference range like '70 - 99' or '< 200'."""
    if not ref_raw:
        return None, None
    import re

    s = ref_raw.replace(",", ".")
    m = re.search(r"(-?\d+\.?\d*)\s*[-–a]+\s*(-?\d+\.?\d*)", s)
    if m:
        return float(m.group(1)), float(m.group(2))
    m = re.search(r"[<≤]\s*(-?\d+\.?\d*)", s)
    if m:
        return None, float(m.group(1))
    m = re.search(r"[>≥]\s*(-?\d+\.?\d*)", s)
    if m:
        return float(m.group(1)), None
    return None, None
