"""Phase 4 — AI longevity / insights layer.

Privacy-first: analysis only ever sees a *minimal slice* — selected biomarker
timelines (values, units, reference ranges, in/out-of-range flags) plus age/sex.
Never the whole DB, raw text, names, IDs, or original documents. The exact slice
is exposed via the preview endpoint so the user sees what would be shared before
any Claude call.

Trend flags are computed deterministically (no LLM), so they work without a key
and reduce reliance on the model for the factual part.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from sqlmodel import Session, select

from .config import settings
from .models import Biomarker, NarrativeReport, Observation, Patient

# Relative change (fraction) above which a trend is called rising/falling rather than stable.
TREND_EPS = 0.05


def _age(dob: Optional[date]) -> Optional[int]:
    if not dob:
        return None
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def _in_range(value, low, high) -> Optional[bool]:
    if value is None:
        return None
    if low is not None and value < low:
        return False
    if high is not None and value > high:
        return False
    return True


def build_slice(
    session: Session,
    *,
    biomarker_slugs: Optional[list[str]] = None,
    include_reports: bool = False,
) -> dict:
    """Assemble the minimal payload that would be shared with Claude."""
    patient = session.exec(select(Patient)).first()
    subject = {
        "age": _age(patient.date_of_birth) if patient else None,
        "sex": patient.sex if patient else None,
    }

    # Which biomarkers: explicit selection, else all that have confirmed data.
    q = select(Biomarker)
    if biomarker_slugs:
        q = q.where(Biomarker.slug.in_(biomarker_slugs))
    biomarkers = session.exec(q).all()

    series = []
    for bm in biomarkers:
        obs = session.exec(
            select(Observation)
            .where(
                Observation.biomarker_id == bm.id,
                Observation.status == "confirmed",
                Observation.value_num.is_not(None),
                Observation.collection_date.is_not(None),
            )
            .order_by(Observation.collection_date)
        ).all()
        if not obs:
            continue
        points = [
            {
                "date": o.collection_date.isoformat(),
                "value": o.value_num,
                "in_range": _in_range(o.value_num, o.ref_low, o.ref_high),
            }
            for o in obs
        ]
        series.append(
            {
                "biomarker": bm.display_name,
                "category": bm.category,
                "unit": bm.canonical_unit,
                "ref_low": bm.default_ref_low,
                "ref_high": bm.default_ref_high,
                "higher_is_better": bm.higher_is_better,
                "points": points,
            }
        )

    payload = {"subject": subject, "biomarkers": series}

    if include_reports:
        reports = session.exec(select(NarrativeReport)).all()
        payload["reports"] = [
            {
                "title": r.title,
                "category": r.category,
                "date": r.report_date.isoformat() if r.report_date else None,
                "impression": r.impression,
            }
            for r in reports
        ]
    return payload


def compute_flags(slice_payload: dict) -> list[dict]:
    """Deterministic trend flags from the slice — no LLM involved."""
    flags = []
    for s in slice_payload.get("biomarkers", []):
        pts = s["points"]
        if not pts:
            continue
        latest = pts[-1]
        first = pts[0]
        lv, fv = latest["value"], first["value"]

        # Direction over the whole series.
        if fv == 0 or lv is None or fv is None:
            direction = "n/a"
        else:
            change = (lv - fv) / abs(fv)
            direction = "rising" if change > TREND_EPS else "falling" if change < -TREND_EPS else "stable"

        in_range = latest["in_range"]
        hib = s.get("higher_is_better")

        # Is the movement favorable?
        good_dir = None
        if direction in ("rising", "falling") and hib is not None:
            good_dir = (direction == "rising") == bool(hib)

        if in_range is False and good_dir is False:
            severity = "high"
        elif in_range is False:
            severity = "medium"
        elif good_dir is False:
            severity = "watch"
        else:
            severity = "ok"

        flags.append(
            {
                "biomarker": s["biomarker"],
                "unit": s["unit"],
                "latest": lv,
                "latest_date": latest["date"],
                "in_range": in_range,
                "direction": direction,
                "n_points": len(pts),
                "severity": severity,
            }
        )
    order = {"high": 0, "medium": 1, "watch": 2, "ok": 3}
    flags.sort(key=lambda f: order.get(f["severity"], 9))
    return flags


SYSTEM_PROMPT = (
    "You are a longevity-focused health-data analyst. You are given a person's "
    "longitudinal biomarker history (values over time, units, reference ranges, "
    "in/out-of-range flags) plus age/sex, and a set of deterministic trend flags. "
    "Write a clear, structured summary:\n"
    "1. Overall trajectory (what's improving, what's worsening, what's stable).\n"
    "2. The most important things to pay attention to, grounded ONLY in the data shown.\n"
    "3. Concrete, evidence-based lifestyle levers relevant to the flagged markers.\n"
    "4. Specific questions to raise with a physician.\n"
    "Be precise with numbers and dates from the data. Do NOT invent values. "
    "You are not a doctor; include a brief note that this is informational and not "
    "a diagnosis or medical advice. Use Markdown."
)


def run_analysis(slice_payload: dict, flags: list[dict], question: Optional[str] = None) -> dict:
    """Call Claude on the minimal slice. Requires ANTHROPIC_API_KEY."""
    if not settings.has_api_key:
        return {"ok": False, "error": "no_api_key"}
    try:
        import anthropic
    except ImportError:
        return {"ok": False, "error": "anthropic_sdk_missing"}

    import json

    user = (
        "Here is the data slice (the only data shared):\n```json\n"
        + json.dumps({"slice": slice_payload, "trend_flags": flags}, ensure_ascii=False)
        + "\n```\n"
    )
    if question:
        user += f"\nUser question to focus on: {question}\n"

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    try:
        msg = client.messages.create(
            model=settings.extract_model,
            max_tokens=2000,
            temperature=0.3,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user}],
        )
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

    text = "".join(b.text for b in msg.content if getattr(b, "type", None) == "text")
    usage = getattr(msg, "usage", None)
    return {
        "ok": True,
        "insights": text,
        "model": settings.extract_model,
        "tokens_in": getattr(usage, "input_tokens", None) if usage else None,
        "tokens_out": getattr(usage, "output_tokens", None) if usage else None,
    }
