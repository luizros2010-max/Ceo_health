from datetime import date

from sqlmodel import select

from app.analysis_service import build_slice, compute_flags
from app.models import Biomarker, Observation, Patient


def _add(session, slug, pairs):
    bm = session.exec(select(Biomarker).where(Biomarker.slug == slug)).first()
    for d, v in pairs:
        session.add(
            Observation(
                source_document_id=1,
                raw_name=slug,
                value_num=v,
                canonical_unit=bm.canonical_unit,
                biomarker_id=bm.id,
                ref_low=bm.default_ref_low,
                ref_high=bm.default_ref_high,
                collection_date=date.fromisoformat(d),
                status="confirmed",
                mapping_confidence=1.0,
            )
        )
    session.commit()


def test_slice_excludes_identifiers_and_includes_age(session):
    p = session.exec(select(Patient)).first()
    p.date_of_birth = date(1964, 7, 22)
    p.sex = "male"
    session.add(p)
    _add(session, "ldl_cholesterol", [("2018-05-01", 132), ("2026-01-16", 155)])
    session.commit()

    sl = build_slice(session, biomarker_slugs=["ldl_cholesterol"])
    assert sl["subject"]["sex"] == "male"
    assert sl["subject"]["age"] and sl["subject"]["age"] >= 60
    bm = sl["biomarkers"][0]
    # Minimal slice: no raw names, ids, document references.
    assert set(bm.keys()) == {
        "biomarker", "category", "unit", "ref_low", "ref_high", "higher_is_better", "points"
    }
    assert bm["points"][0] == {"date": "2018-05-01", "value": 132.0, "in_range": False}


def test_flags_rising_out_of_range_is_high(session):
    # LDL ref high 100; rising 132 -> 155 and out of range -> high severity.
    _add(session, "ldl_cholesterol", [("2018-05-01", 132), ("2026-01-16", 155)])
    sl = build_slice(session, biomarker_slugs=["ldl_cholesterol"])
    flag = compute_flags(sl)[0]
    assert flag["direction"] == "rising"
    assert flag["in_range"] is False
    assert flag["severity"] == "high"


def test_flags_in_range_stable_is_ok(session):
    _add(session, "glucose_fasting", [("2019-01-01", 88), ("2020-01-01", 90)])
    sl = build_slice(session, biomarker_slugs=["glucose_fasting"])
    flag = compute_flags(sl)[0]
    assert flag["in_range"] is True
    assert flag["severity"] == "ok"
