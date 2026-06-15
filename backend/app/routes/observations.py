"""Observation routes: list, manual entry, review queue, confirm/fix/reject (+ learn alias)."""
from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlmodel import Session, select

from ..auth import current_patient_id
from ..db import get_session
from ..ingest.imports import import_csv_text
from ..ingest.normalize import convert_value
from ..models import Biomarker, BiomarkerAlias, Observation, Patient, SourceDocument
from ..schemas import ManualObservation, ObservationPatch
from ..textnorm import normalize_alias

router = APIRouter(prefix="/api/observations", tags=["observations"])


@router.get("")
def list_observations(
    biomarker: Optional[str] = Query(default=None, description="biomarker slug"),
    status: Optional[str] = None,
    date_from: Optional[date] = Query(default=None, alias="from"),
    date_to: Optional[date] = Query(default=None, alias="to"),
    session: Session = Depends(get_session),
    pid: int = Depends(current_patient_id),
):
    stmt = select(Observation).where(Observation.patient_id == pid)
    if biomarker:
        bm = session.exec(select(Biomarker).where(Biomarker.slug == biomarker)).first()
        if not bm:
            raise HTTPException(status_code=404, detail="Unknown biomarker")
        stmt = stmt.where(Observation.biomarker_id == bm.id)
    if status:
        stmt = stmt.where(Observation.status == status)
    if date_from:
        stmt = stmt.where(Observation.collection_date >= date_from)
    if date_to:
        stmt = stmt.where(Observation.collection_date <= date_to)
    return session.exec(stmt.order_by(Observation.collection_date)).all()


@router.get("/review")
def review_queue(session: Session = Depends(get_session), pid: int = Depends(current_patient_id)):
    rows = session.exec(
        select(Observation).where(Observation.status == "needs_review", Observation.patient_id == pid)
    ).all()
    out = []
    for o in rows:
        bm = session.get(Biomarker, o.biomarker_id) if o.biomarker_id else None
        doc = session.get(SourceDocument, o.source_document_id)
        out.append(
            {
                "observation": o,
                "suggested_biomarker": (
                    {"slug": bm.slug, "display_name": bm.display_name} if bm else None
                ),
                "document": {
                    "id": doc.id if doc else None,
                    "original_name": doc.original_name if doc else None,
                    "lab_name": doc.lab_name if doc else None,
                },
            }
        )
    return out


@router.post("")
def create_manual_observation(
    body: ManualObservation, session: Session = Depends(get_session), pid: int = Depends(current_patient_id)
):
    bm = session.exec(select(Biomarker).where(Biomarker.slug == body.biomarker_slug)).first()
    if not bm:
        raise HTTPException(status_code=404, detail="Unknown biomarker slug")
    patient = session.get(Patient, pid)

    # Manual entries are confirmed immediately (the human is the source).
    conv = convert_value(session, bm, body.value_num, body.unit)
    obs = Observation(
        source_document_id=_manual_document_id(session, patient),
        patient_id=patient.id if patient else None,
        raw_name=bm.display_name,
        raw_value=str(body.value_num),
        raw_unit=body.unit or bm.canonical_unit,
        biomarker_id=bm.id,
        value_num=conv.value_num,
        canonical_unit=conv.canonical_unit,
        ref_low=body.ref_low if body.ref_low is not None else bm.default_ref_low,
        ref_high=body.ref_high if body.ref_high is not None else bm.default_ref_high,
        ref_source="report" if body.ref_low is not None or body.ref_high is not None else "catalog_default",
        collection_date=body.collection_date,
        extraction_method="manual",
        mapping_confidence=1.0,
        status="confirmed",
        source_text_snippet=body.notes,
    )
    session.add(obs)
    session.commit()
    session.refresh(obs)
    return obs


@router.post("/import-csv")
async def import_csv_upload(
    file: UploadFile = File(...), session: Session = Depends(get_session),
    pid: int = Depends(current_patient_id),
):
    """Import a long-format CSV (biomarker,date,value,unit) into your record."""
    data = await file.read()
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 text/CSV")
    name = file.filename or "CSV import"
    return import_csv_text(session, text, name, pid)


@router.patch("/{obs_id}")
def patch_observation(
    obs_id: int, patch: ObservationPatch, session: Session = Depends(get_session),
    pid: int = Depends(current_patient_id),
):
    obs = session.get(Observation, obs_id)
    if not obs or obs.patient_id != pid:
        raise HTTPException(status_code=404, detail="Observation not found")

    # Re-map to a different biomarker, optionally teaching the catalog a new alias.
    if patch.biomarker_slug is not None:
        bm = session.exec(
            select(Biomarker).where(Biomarker.slug == patch.biomarker_slug)
        ).first()
        if not bm:
            raise HTTPException(status_code=404, detail="Unknown biomarker slug")
        obs.biomarker_id = bm.id
        obs.canonical_unit = bm.canonical_unit
        conv = convert_value(session, bm, obs.value_num, obs.raw_unit)
        obs.value_num = conv.value_num
        if obs.ref_source == "catalog_default" or (obs.ref_low is None and obs.ref_high is None):
            obs.ref_low, obs.ref_high = bm.default_ref_low, bm.default_ref_high
            obs.ref_source = "catalog_default"
        if patch.learn_alias and obs.raw_name:
            _learn_alias(session, bm.id, obs.raw_name)

    if patch.value_num is not None:
        obs.value_num = patch.value_num
    if patch.collection_date is not None:
        obs.collection_date = patch.collection_date
    if patch.ref_low is not None:
        obs.ref_low = patch.ref_low
        obs.ref_source = "report"
    if patch.ref_high is not None:
        obs.ref_high = patch.ref_high
        obs.ref_source = "report"
    if patch.status is not None:
        if patch.status not in {"confirmed", "rejected", "needs_review"}:
            raise HTTPException(status_code=400, detail="Invalid status")
        obs.status = patch.status
        if patch.status == "confirmed":
            obs.mapping_confidence = max(obs.mapping_confidence, 1.0)

    session.add(obs)
    session.commit()
    session.refresh(obs)
    return obs


def _learn_alias(session: Session, biomarker_id: int, raw_name: str) -> None:
    norm = normalize_alias(raw_name)
    if not norm:
        return
    exists = session.exec(
        select(BiomarkerAlias).where(BiomarkerAlias.alias_text == norm)
    ).first()
    if not exists:
        session.add(BiomarkerAlias(biomarker_id=biomarker_id, alias_text=norm))


def _manual_document_id(session: Session, patient: Optional[Patient]) -> int:
    """A per-patient synthetic 'Manual entry' source document groups hand-entered values."""
    pid = patient.id if patient else None
    doc = session.exec(
        select(SourceDocument).where(
            SourceDocument.source_type == "manual", SourceDocument.patient_id == pid
        )
    ).first()
    if doc:
        return doc.id
    doc = SourceDocument(
        patient_id=pid,
        file_sha256=f"manual-entry:{pid}",
        file_path="",
        original_name="Manual entry",
        mime_type="text/plain",
        source_type="manual",
        ingest_status="reviewed",
    )
    session.add(doc)
    session.flush()
    return doc.id
