"""Action plan generator — turns score gaps into concrete targets + levers.

Deterministic (no LLM): for each below-optimal marker it derives the value that
would earn full marks, and surfaces the workout / nutrition / lifestyle / medical
levers relevant to whichever domains are weak. The AI layer can additionally draft
a narrative plan from the same minimal slice.
"""
from __future__ import annotations

from sqlmodel import Session

from .scoring import ANCHORS, compute_score, latest_values

# Levers per domain — shown when that domain scores below target.
LEVERS: dict[str, dict[str, list[str]]] = {
    "Cholesterol / lipids": {
        "nutrition": [
            "Soluble fiber 10–25 g/day (oats, barley, beans/lentils, psyllium, apples)",
            "Plant sterols ~2 g/day (fortified spread or supplement)",
            "Saturated fat <7% of calories; eliminate trans fats",
            "Swap to extra-virgin olive oil; daily handful of nuts; fatty fish 2–3×/week",
            "Mediterranean / Portfolio dietary pattern; more legumes & soy protein",
        ],
        "workout": ["Zone-2 aerobic 150–200 min/week", "1–2 VO₂/interval sessions/week to raise HDL"],
        "medical": ["Discuss LDL-lowering therapy (e.g. statin) with your physician given the rising trend"],
    },
    "Metabolic / glycemic": {
        "nutrition": [
            "Cut refined sugar and white starch; prioritize whole-food carbs",
            "Protein + fiber with each meal to blunt glucose spikes",
        ],
        "workout": ["10–15 min walk after meals", "Resistance training 2–3×/week for glucose disposal"],
        "lifestyle": ["Weight/waist reduction if elevated; 7–8 h sleep (sleep debt raises glucose)"],
    },
    "Kidney": {
        "nutrition": ["Hydrate ~2.5–3 L/day", "Avoid excessive protein loads / NSAID overuse"],
    },
    "Liver": {
        "nutrition": ["Limit alcohol and added sugar (fatty-liver/pancreas risk)"],
        "lifestyle": ["Weight management"],
    },
    "Hormonal / other": {
        "nutrition": ["Vitamin D 1000–2000 IU/day if below ~40 ng/mL (confirm with labs)"],
    },
    "Body & blood pressure": {
        "nutrition": ["DASH pattern; sodium <2.3 g/day; more potassium-rich produce"],
        "workout": ["Aerobic 150+ min/week; resistance 2–3×/week"],
        "lifestyle": ["Weight/waist reduction; limit alcohol; manage stress; confirm BP with home cuff"],
        "medical": ["If BP stays ≥130/80, discuss management with your physician"],
    },
    "Inflammation / blood": {
        "lifestyle": ["Maintain — anti-inflammatory diet, exercise, sleep"],
    },
}

TARGET_GAP = 90.0  # markers scoring below this get an explicit target


def _max_score_target(slug: str, current: float):
    anchors = ANCHORS[slug]
    top = max(s for _, s in anchors)
    candidates = [x for x, s in anchors if s >= top - 0.01]
    target = min(candidates, key=lambda x: abs(x - current))
    if target < current:
        direction = "reduce to"
    elif target > current:
        direction = "raise to"
    else:
        direction = "maintain near"
    return target, direction


def compute_plan(session: Session) -> dict:
    score = compute_score(session)
    vals = latest_values(session)

    # Targets for below-optimal markers.
    targets = []
    for dom in score["domains"]:
        for m in dom["markers"]:
            if m["score"] >= TARGET_GAP:
                continue
            tgt, direction = _max_score_target(m["slug"], m["value"])
            targets.append(
                {
                    "biomarker": m["biomarker"],
                    "slug": m["slug"],
                    "domain": dom["name"],
                    "current": m["value"],
                    "unit": m["unit"],
                    "current_score": m["score"],
                    "target": tgt,
                    "direction": direction,
                }
            )
    targets.sort(key=lambda t: t["current_score"])

    # Levers for weak domains.
    weak = [d["name"] for d in score["domains"] if d["score"] < TARGET_GAP]
    levers = []
    for name in weak:
        if name in LEVERS:
            levers.append({"domain": name, "score": next(d["score"] for d in score["domains"] if d["name"] == name), **LEVERS[name]})

    # Which scoreable trackers the user hasn't entered yet (missing risk factors).
    missing = [
        {"slug": s, "label": s.replace("_", " ")}
        for s in ["systolic_bp", "diastolic_bp", "bmi", "waist_circumference"]
        if s not in vals
    ]

    return {
        "overall": score["overall"],
        "subject": score["subject"],
        "targets": targets,
        "levers": levers,
        "missing_trackers": missing,
        "note": "Targets are the values that would earn full marks for each metric. "
        "Informational only — clear exercise intensity and any medication with your physician.",
    }
