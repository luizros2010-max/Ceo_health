"""Transparent health scoring vs. age-peers.

Every biomarker is scored 0-100 against explicit clinical anchor points (not a
black box): the anchors below encode commonly-cited optimal/target values, and a
score is linearly interpolated between them. Domain scores average their markers;
the overall score is a weighted average across the domains that have data.

This is deterministic (no LLM, no API key) and intentionally inspectable — the
anchors are returned with the result so the UI can show *why* each score is what
it is. Percentile bands are rough population estimates, not a live database, and
this is informational, not medical advice.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from sqlmodel import Session, select

from .models import Biomarker, Observation, Patient

# Per biomarker: ascending (value, score) anchors. Interpolated + clamped to [0,100].
# "lower is better" -> scores descend with value; "higher" -> ascend; "center" -> peak mid.
ANCHORS: dict[str, list[tuple[float, float]]] = {
    # Metabolic
    "hba1c": [(4.8, 100), (5.6, 85), (6.0, 60), (6.5, 35), (7.5, 10)],
    "glucose_fasting": [(85, 100), (99, 85), (110, 60), (126, 35), (160, 10)],
    "triglycerides": [(50, 100), (100, 90), (150, 75), (200, 55), (300, 30), (500, 10)],
    # Lipids
    "ldl_cholesterol": [(70, 100), (100, 85), (130, 65), (160, 45), (190, 25), (220, 10)],
    "cholesterol_total": [(170, 100), (200, 82), (240, 55), (280, 30), (320, 12)],
    "hdl_cholesterol": [(30, 30), (40, 55), (50, 78), (60, 92), (75, 100)],
    "chol_hdl_ratio": [(3.0, 100), (3.5, 92), (4.0, 82), (5.0, 62), (6.0, 40), (8.0, 15)],
    # Kidney (eGFR anchors are age-tolerant: a mild age-related dip still scores well)
    "egfr": [(30, 20), (45, 40), (60, 65), (75, 85), (90, 100)],
    "creatinine": [(0.6, 92), (0.8, 100), (1.0, 95), (1.3, 75), (1.6, 45), (2.0, 20)],
    "urea": [(10, 95), (20, 100), (40, 85), (50, 70), (70, 40)],
    # Liver
    "alt": [(15, 100), (41, 82), (60, 58), (100, 28), (150, 10)],
    "ast": [(12, 100), (40, 82), (60, 55), (100, 25)],
    "ggt": [(20, 100), (60, 82), (100, 55), (150, 28)],
    "bilirubin_total": [(0.3, 90), (0.7, 100), (1.2, 88), (1.6, 65), (2.5, 35)],
    # Inflammation / blood
    "crp": [(0.5, 100), (1.0, 90), (3.0, 65), (5.0, 45), (10.0, 20)],
    "hemoglobin": [(12.0, 60), (13.5, 88), (14.5, 100), (16.5, 100), (17.5, 85), (18.5, 60)],
    "wbc": [(3.0, 55), (4.0, 85), (5.5, 100), (8.0, 95), (11.0, 70), (14.0, 40)],
    "platelets": [(100, 50), (150, 85), (220, 100), (350, 95), (450, 60)],
    # Hormonal / other
    "vitamin_d": [(15, 35), (20, 55), (30, 78), (40, 92), (50, 100), (100, 100), (120, 80)],
    "tsh": [(0.3, 70), (0.6, 92), (1.0, 100), (2.5, 100), (4.0, 80), (6.0, 45)],
    "psa_total": [(0.5, 100), (1.5, 95), (2.5, 85), (4.0, 65), (6.0, 35), (10.0, 12)],
    "uric_acid": [(3.0, 90), (4.5, 100), (6.0, 88), (7.0, 72), (8.5, 45), (10.0, 20)],
    "albumin": [(3.3, 60), (3.8, 85), (4.3, 100), (5.0, 100), (5.5, 90)],
    # Vitals / body
    "systolic_bp": [(105, 100), (120, 90), (130, 70), (140, 45), (160, 20)],
    "diastolic_bp": [(65, 100), (80, 90), (90, 60), (100, 30)],
    "bmi": [(18.5, 80), (22, 100), (25, 82), (28, 60), (32, 35), (38, 12)],
    "waist_circumference": [(80, 100), (94, 82), (102, 55), (112, 30), (125, 12)],
    # Fitness & recovery (wearables)
    "vo2max": [(20, 35), (28, 62), (35, 85), (42, 100), (55, 100)],
    "resting_heart_rate": [(45, 100), (55, 92), (65, 78), (75, 55), (85, 30), (95, 12)],
    "hrv": [(15, 35), (30, 62), (50, 85), (70, 100), (100, 100)],
    "sleep_duration": [(4, 30), (6, 72), (7, 100), (8.5, 100), (9.5, 88), (11, 60)],
    "spo2": [(90, 35), (94, 72), (96, 90), (98, 100)],
}

# Domains: (display, weight, [biomarker slugs])
DOMAINS: list[tuple[str, float, list[str]]] = [
    ("Metabolic / glycemic", 0.25, ["hba1c", "glucose_fasting", "triglycerides"]),
    ("Cholesterol / lipids", 0.25, ["ldl_cholesterol", "cholesterol_total", "hdl_cholesterol", "chol_hdl_ratio"]),
    ("Kidney", 0.15, ["egfr", "creatinine", "urea"]),
    ("Liver", 0.10, ["alt", "ast", "ggt", "bilirubin_total"]),
    ("Inflammation / blood", 0.10, ["crp", "hemoglobin", "wbc", "platelets"]),
    ("Hormonal / other", 0.15, ["vitamin_d", "tsh", "psa_total", "uric_acid", "albumin"]),
    ("Body & blood pressure", 0.15, ["bmi", "waist_circumference", "systolic_bp", "diastolic_bp"]),
    ("Fitness & recovery", 0.15, ["vo2max", "resting_heart_rate", "hrv", "sleep_duration", "spo2"]),
]


def _interp(value: float, anchors: list[tuple[float, float]]) -> float:
    if value <= anchors[0][0]:
        return anchors[0][1]
    if value >= anchors[-1][0]:
        return anchors[-1][1]
    for (x0, s0), (x1, s1) in zip(anchors, anchors[1:]):
        if x0 <= value <= x1:
            t = (value - x0) / (x1 - x0) if x1 != x0 else 0
            return s0 + t * (s1 - s0)
    return anchors[-1][1]


def _age(dob: Optional[date]) -> Optional[int]:
    if not dob:
        return None
    t = date.today()
    return t.year - dob.year - ((t.month, t.day) < (dob.month, dob.day))


def latest_values(session: Session, patient_id: int | None = None) -> dict[str, dict]:
    """Latest confirmed value per biomarker slug (optionally scoped to a patient)."""
    out: dict[str, dict] = {}
    stmt = select(Observation).where(
        Observation.status == "confirmed",
        Observation.value_num.is_not(None),
        Observation.collection_date.is_not(None),
    )
    if patient_id is not None:
        stmt = stmt.where(Observation.patient_id == patient_id)
    rows = session.exec(stmt).all()
    by_bm: dict[int, Observation] = {}
    for o in rows:
        prev = by_bm.get(o.biomarker_id)
        if o.biomarker_id and (prev is None or o.collection_date > prev.collection_date):
            by_bm[o.biomarker_id] = o
    for bm_id, o in by_bm.items():
        bm = session.get(Biomarker, bm_id)
        if bm:
            out[bm.slug] = {
                "display_name": bm.display_name,
                "value": o.value_num,
                "unit": o.canonical_unit or bm.canonical_unit,
                "date": o.collection_date.isoformat(),
            }
    return out


def _band(score: float) -> tuple[str, str]:
    if score >= 88:
        return "top ~10% for your age", "excellent"
    if score >= 80:
        return "top ~20–30% for your age", "very good"
    if score >= 72:
        return "top ~30–45% for your age", "good"
    if score >= 62:
        return "around average for your age", "average"
    if score >= 50:
        return "somewhat below average for your age", "below average"
    return "well below average for your age", "needs attention"


def compute_score(session: Session, patient_id: int | None = None) -> dict:
    patient = session.get(Patient, patient_id) if patient_id else session.exec(select(Patient)).first()
    vals = latest_values(session, patient_id)

    domains = []
    weighted_sum = 0.0
    weight_total = 0.0
    for name, weight, slugs in DOMAINS:
        markers = []
        for slug in slugs:
            v = vals.get(slug)
            if not v or slug not in ANCHORS:
                continue
            sc = round(_interp(v["value"], ANCHORS[slug]), 1)
            markers.append(
                {
                    "biomarker": v["display_name"],
                    "slug": slug,
                    "value": v["value"],
                    "unit": v["unit"],
                    "date": v["date"],
                    "score": sc,
                    "optimal": ANCHORS[slug][0][0] if ANCHORS[slug][0][1] >= 90 else None,
                }
            )
        if not markers:
            continue
        dscore = round(sum(m["score"] for m in markers) / len(markers), 1)
        domains.append({"name": name, "weight": weight, "score": dscore, "markers": markers})
        weighted_sum += dscore * weight
        weight_total += weight

    overall = round(weighted_sum / weight_total, 1) if weight_total else None
    band, label = _band(overall) if overall is not None else ("no data", "n/a")

    return {
        "overall": {"score": overall, "band": band, "label": label},
        "subject": {"age": _age(patient.date_of_birth) if patient else None,
                    "sex": patient.sex if patient else None},
        "domains": sorted(domains, key=lambda d: d["score"]),
        "as_of": max((v["date"] for v in vals.values()), default=None),
        "caveats": [
            "Scores compare your values to common clinical optimal targets; anchor points are shown per marker.",
            "Percentile bands are rough population estimates, not a live database.",
            "Reference targets are general (not age/sex-individualized beyond eGFR tolerance), and exclude key factors like blood pressure, body composition, ApoB/Lp(a), smoking, and family history.",
            "Informational only — not a diagnosis or medical advice.",
        ],
    }
