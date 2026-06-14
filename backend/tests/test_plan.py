from datetime import date

from sqlmodel import select

from app.models import Biomarker, Observation
from app.plan_service import compute_plan


def _add(session, slug, value):
    bm = session.exec(select(Biomarker).where(Biomarker.slug == slug)).first()
    session.add(
        Observation(
            source_document_id=1, raw_name=slug, value_num=value,
            canonical_unit=bm.canonical_unit, biomarker_id=bm.id,
            collection_date=date(2026, 1, 16), status="confirmed", mapping_confidence=1.0,
        )
    )
    session.commit()


def test_plan_targets_high_ldl(session):
    _add(session, "ldl_cholesterol", 155)
    plan = compute_plan(session)
    ldl = next(t for t in plan["targets"] if t["slug"] == "ldl_cholesterol")
    assert ldl["direction"] == "reduce to"
    assert ldl["target"] <= 100
    # lipids levers surfaced
    assert any(l["domain"].startswith("Cholesterol") for l in plan["levers"])


def test_plan_lists_missing_trackers(session):
    _add(session, "ldl_cholesterol", 155)
    plan = compute_plan(session)
    slugs = {m["slug"] for m in plan["missing_trackers"]}
    assert {"systolic_bp", "bmi", "waist_circumference"} <= slugs


def test_bp_scores_and_targets(session):
    _add(session, "systolic_bp", 145)
    plan = compute_plan(session)
    sbp = next(t for t in plan["targets"] if t["slug"] == "systolic_bp")
    assert sbp["direction"] == "reduce to"
    assert sbp["target"] <= 120
