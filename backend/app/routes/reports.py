"""Narrative / imaging report routes (MRI, echo, endoscopy, specialist notes)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlmodel import Session, select

from ..auth import current_patient_id
from ..db import get_session
from ..ingest.imports import import_reports_json
from ..models import NarrativeReport, Patient
from ..schemas import NarrativeReportIn

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.post("/import-json")
async def import_reports_upload(
    file: UploadFile = File(...), session: Session = Depends(get_session),
    pid: int = Depends(current_patient_id),
):
    """Import narrative/imaging reports from a JSON file into your record."""
    data = await file.read()
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 JSON")
    return import_reports_json(session, text, pid)


@router.get("")
def list_reports(session: Session = Depends(get_session), pid: int = Depends(current_patient_id)):
    reports = session.exec(
        select(NarrativeReport).where(NarrativeReport.patient_id == pid).order_by(NarrativeReport.report_date.desc())
    ).all()
    return [
        {
            "id": r.id,
            "title": r.title,
            "category": r.category,
            "report_date": r.report_date,
            "facility": r.facility,
            "impression": r.impression,
            "snippet": (r.body[:200] + "…") if r.body and len(r.body) > 200 else r.body,
        }
        for r in reports
    ]


@router.get("/{report_id}")
def get_report(report_id: int, session: Session = Depends(get_session), pid: int = Depends(current_patient_id)):
    r = session.get(NarrativeReport, report_id)
    if not r or r.patient_id != pid:
        raise HTTPException(status_code=404, detail="Report not found")
    return r


@router.post("")
def create_report(body: NarrativeReportIn, session: Session = Depends(get_session), pid: int = Depends(current_patient_id)):
    patient = session.get(Patient, pid)
    report = NarrativeReport(
        patient_id=patient.id if patient else None,
        title=body.title,
        category=body.category,
        report_date=body.report_date,
        facility=body.facility,
        body=body.body,
        impression=body.impression,
    )
    session.add(report)
    session.commit()
    session.refresh(report)
    return report


@router.delete("/{report_id}")
def delete_report(report_id: int, session: Session = Depends(get_session), pid: int = Depends(current_patient_id)):
    r = session.get(NarrativeReport, report_id)
    if not r or r.patient_id != pid:
        raise HTTPException(status_code=404, detail="Report not found")
    session.delete(r)
    session.commit()
    return {"deleted": report_id}
