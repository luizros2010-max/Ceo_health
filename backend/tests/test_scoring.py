from datetime import date

from sqlmodel import select

from app.models import Biomarker, Observation
from app.scoring import ANCHORS, _interp, compute_score


def _add(session, slug, value, d="2026-01-16"):
    bm = session.exec(select(Biomarker).where(Biomarker.slug == slug)).first()
    session.add(
        Observation(
            source_document_id=1, raw_name=slug, value_num=value,
            canonical_unit=bm.canonical_unit, biomarker_id=bm.id,
            collection_date=date.fromisoformat(d), status="confirmed", mapping_confidence=1.0,
        )
    )
    session.commit()


def test_interp_clamps_and_interpolates():
    a = ANCHORS["ldl_cholesterol"]
    assert _interp(50, a) == 100          # below first anchor -> clamped high
    assert _interp(300, a) == 10          # above last -> clamped low
    # 154 between (130,65) and (160,45): 65 - (24/30)*20 = 49.0
    assert abs(_interp(154, a) - 49.0) < 0.6


def test_excellent_metabolic_scores_high(session):
    _add(session, "hba1c", 4.9)
    _add(session, "triglycerides", 52)
    _add(session, "glucose_fasting", 90)
    res = compute_score(session)
    metab = next(d for d in res["domains"] if d["name"].startswith("Metabolic"))
    assert metab["score"] >= 90


def test_high_ldl_drags_lipids(session):
    _add(session, "ldl_cholesterol", 155)
    _add(session, "hdl_cholesterol", 52)
    res = compute_score(session)
    lipids = next(d for d in res["domains"] if d["name"].startswith("Cholesterol"))
    # LDL ~48, HDL ~80 -> domain in the 60s
    assert 55 <= lipids["score"] <= 72


def test_overall_band_present(session):
    _add(session, "hba1c", 4.9)
    _add(session, "ldl_cholesterol", 155)
    res = compute_score(session)
    assert res["overall"]["score"] is not None
    assert res["overall"]["band"]
    assert res["domains"][0]["score"] <= res["domains"][-1]["score"]  # sorted ascending
