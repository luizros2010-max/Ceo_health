"""Biomarker routes: catalog + timeline + overview."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..auth import current_patient_id
from ..db import get_session
from ..models import Biomarker, Observation, SourceDocument

router = APIRouter(prefix="/api", tags=["biomarkers"])


@router.get("/biomarkers")
def list_biomarkers(session: Session = Depends(get_session), pid: int = Depends(current_patient_id)):
    biomarkers = session.exec(select(Biomarker).order_by(Biomarker.category, Biomarker.display_name)).all()
    confirmed = session.exec(
        select(Observation).where(Observation.status == "confirmed", Observation.patient_id == pid)
    ).all()
    have_data = {o.biomarker_id for o in confirmed if o.biomarker_id}
    return [
        {
            "slug": b.slug,
            "display_name": b.display_name,
            "category": b.category,
            "canonical_unit": b.canonical_unit,
            "default_ref_low": b.default_ref_low,
            "default_ref_high": b.default_ref_high,
            "higher_is_better": b.higher_is_better,
            "has_data": b.id in have_data,
        }
        for b in biomarkers
    ]


@router.get("/biomarkers/{slug}/timeline")
def biomarker_timeline(slug: str, session: Session = Depends(get_session), pid: int = Depends(current_patient_id)):
    bm = session.exec(select(Biomarker).where(Biomarker.slug == slug)).first()
    if not bm:
        raise HTTPException(status_code=404, detail="Unknown biomarker")
    obs = session.exec(
        select(Observation)
        .where(Observation.biomarker_id == bm.id, Observation.status == "confirmed",
               Observation.patient_id == pid)
        .order_by(Observation.collection_date)
    ).all()
    doc_names: dict[int, str] = {}
    points = []
    for o in obs:
        if o.value_num is None or o.collection_date is None:
            continue
        if o.source_document_id not in doc_names:
            d = session.get(SourceDocument, o.source_document_id)
            doc_names[o.source_document_id] = d.original_name if d else "Unknown"
        points.append(
            {
                "date": o.collection_date,
                "value": o.value_num,
                "operator": o.operator,
                "refLow": o.ref_low,
                "refHigh": o.ref_high,
                "sourceDocId": o.source_document_id,
                "source": doc_names[o.source_document_id],
                "status": o.status,
            }
        )
    return {
        "biomarker": {"slug": bm.slug, "display_name": bm.display_name, "category": bm.category},
        "unit": bm.canonical_unit,
        "refLow": bm.default_ref_low,
        "refHigh": bm.default_ref_high,
        "higherIsBetter": bm.higher_is_better,
        "points": points,
    }


@router.get("/overview")
def overview(session: Session = Depends(get_session), pid: int = Depends(current_patient_id)):
    docs = session.exec(select(SourceDocument).where(SourceDocument.patient_id == pid)).all()
    confirmed = session.exec(
        select(Observation).where(Observation.status == "confirmed", Observation.patient_id == pid)
    ).all()
    needs_review = session.exec(
        select(Observation).where(Observation.status == "needs_review", Observation.patient_id == pid)
    ).all()

    # Latest confirmed value per biomarker.
    latest: dict[int, Observation] = {}
    for o in confirmed:
        if o.biomarker_id is None or o.collection_date is None:
            continue
        prev = latest.get(o.biomarker_id)
        if prev is None or (o.collection_date > prev.collection_date):
            latest[o.biomarker_id] = o

    cards = []
    for bm_id, o in latest.items():
        bm = session.get(Biomarker, bm_id)
        if not bm:
            continue
        in_range = _in_range(o.value_num, o.ref_low, o.ref_high)
        # Sparkline series.
        series = sorted(
            [
                (s.collection_date, s.value_num)
                for s in confirmed
                if s.biomarker_id == bm_id and s.value_num is not None and s.collection_date
            ]
        )
        cards.append(
            {
                "slug": bm.slug,
                "display_name": bm.display_name,
                "category": bm.category,
                "value": o.value_num,
                "unit": o.canonical_unit or bm.canonical_unit,
                "ref_low": o.ref_low,
                "ref_high": o.ref_high,
                "in_range": in_range,
                "last_measured": o.collection_date,
                "sparkline": [{"date": d, "value": v} for d, v in series],
            }
        )
    cards.sort(key=lambda c: (c["in_range"] is True, c["category"] or "", c["display_name"]))

    dates = [o.collection_date for o in confirmed if o.collection_date]
    return {
        "stats": {
            "documents": len([d for d in docs if d.source_type != "manual"]),
            "observations": len(confirmed),
            "needs_review": len(needs_review),
            "date_span": {
                "from": min(dates) if dates else None,
                "to": max(dates) if dates else None,
            },
        },
        "cards": cards,
    }


def _in_range(value, low, high):
    if value is None:
        return None
    if low is not None and value < low:
        return False
    if high is not None and value > high:
        return False
    return True
