"""Key-free lab extraction: pull biomarker values straight from PDF text.

Used when no ANTHROPIC_API_KEY is configured. It scans the extracted text for the
catalog's biomarker aliases (accent/case-insensitive) and grabs the value + unit +
reference range that follow. Strong (multi-word / longer) alias hits are confident
enough to auto-confirm; short/ambiguous ones go to the review queue.

This is a deterministic best-effort parser — the LLM path (extract_llm) is more
robust for messy formats — but it means uploads work out of the box, no key needed.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

from sqlmodel import Session, select

from ..models import Biomarker, BiomarkerAlias
from .extract_llm import ExtractedRow


def _fold(text: str) -> str:
    """Lowercase + strip accents, but keep digits/punctuation (needed for values)."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower()


# value like 1.00, 217, <5, 0,82 ; followed by an optional unit token
_NUM = r"[<>]?\s*-?\d+(?:[.,]\d+)?"
_UNIT = r"[a-zµμ%/0-9^.\-]{1,12}"
_REF = r"(?:[<>]\s*-?\d+(?:[.,]\d+)?|-?\d+(?:[.,]\d+)?\s*[-a]\s*-?\d+(?:[.,]\d+)?)"


@dataclass
class RulesResult:
    rows: list[ExtractedRow]
    collection_date: Optional[date]
    lab_name: Optional[str]


def _parse_dates(folded: str) -> Optional[date]:
    """Best-effort sample/collection date: prefer one near a 'muestra/collected' keyword."""
    candidates: list[date] = []
    for m in re.finditer(r"(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})", folded):
        d, mo, y = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
        if y < 100:
            y += 2000 if y <= (date.today().year % 100) else 1900
        try:
            dt = date(y, mo, d)
        except ValueError:
            continue
        if 1990 <= dt.year <= date.today().year and dt <= date.today():
            # weight dates near collection keywords
            ctx = folded[max(0, m.start() - 40): m.start()]
            score = 2 if re.search(r"muestra|extrac|collect|draw|sample", ctx) else 1
            candidates.append((score, dt))
    for m in re.finditer(r"(\d{4})-(\d{2})-(\d{2})", folded):
        try:
            dt = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            if 1990 <= dt.year <= date.today().year and dt <= date.today():
                candidates.append((1, dt))
        except ValueError:
            continue
    if not candidates:
        return None
    # highest keyword score, then most recent
    candidates.sort(key=lambda t: (t[0], t[1]))
    return candidates[-1][1]


def extract_from_text(session: Session, full_text: str) -> RulesResult:
    folded = _fold(full_text)

    # alias -> biomarker, longest aliases first so specific names win.
    aliases = session.exec(select(BiomarkerAlias)).all()
    by_alias = sorted(aliases, key=lambda a: len(a.alias_text), reverse=True)

    rows: list[ExtractedRow] = []
    seen: set[int] = set()  # one value per biomarker (first/best hit)
    consumed: list[tuple[int, int]] = []  # spans already claimed (longest aliases win)

    def overlaps(a: int, b: int) -> bool:
        return any(a < ce and cs < b for cs, ce in consumed)

    for alias in by_alias:
        if alias.biomarker_id in seen:
            continue
        norm = alias.alias_text.strip()
        if len(norm) < 3:
            continue
        # alias words separated by any non-alphanumeric run
        pattern = r"\b" + r"\W+".join(re.escape(w) for w in norm.split()) + r"\b"
        m = re.search(pattern, folded)
        if not m or overlaps(m.start(), m.end()):
            continue
        window = folded[m.end(): m.end() + 60]
        vm = re.search(rf"({_NUM})\s*({_UNIT})?", window)
        if not vm:
            continue
        consumed.append((m.start(), m.end() + vm.end()))
        value_raw = vm.group(1).replace(" ", "")
        try:
            value_num = float(value_raw.lstrip("<>").replace(",", "."))
        except ValueError:
            continue
        unit = (vm.group(2) or "").strip(" .-") or None
        rm = re.search(_REF, window[vm.end():])
        ref_raw = rm.group(0) if rm else None

        bm = session.get(Biomarker, alias.biomarker_id)
        if not bm:
            continue
        operator = "<" if value_raw.startswith("<") else ">" if value_raw.startswith(">") else "="
        strong = (" " in norm) or len(norm) >= 5
        snippet = full_text[max(0, 0):][:0] or ""
        # grab a readable snippet from the original text around the match
        raw_idx = m.start()
        snippet = full_text[raw_idx: raw_idx + 80].replace("\n", " ").strip()

        rows.append(
            ExtractedRow(
                raw_analyte_name=bm.display_name,
                value_raw=value_raw,
                value_numeric=value_num,
                operator=operator,
                unit_raw=unit,
                reference_raw=ref_raw,
                source_text_snippet=snippet,
                confidence=0.95 if strong else 0.7,
            )
        )
        seen.add(alias.biomarker_id)

    return RulesResult(rows=rows, collection_date=_parse_dates(folded), lab_name=None)
