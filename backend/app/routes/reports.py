"""Narrative / imaging report routes (MRI, echo, endoscopy, specialist notes)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..db import get_session
from ..models import NarrativeReport, Patient
from ..schemas import NarrativeReportIn

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("")
def list_reports(session: Session = Depends(get_session)):
    reports = session.exec(
        select(NarrativeReport).order_by(NarrativeReport.report_date.desc())
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
def get_report(report_id: int, session: Session = Depends(get_session)):
    r = session.get(NarrativeReport, report_id)
    if not r:
        raise HTTPException(status_code=404, detail="Report not found")
    return r


@router.post("")
def create_report(body: NarrativeReportIn, session: Session = Depends(get_session)):
    patient = session.exec(select(Patient)).first()
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
def delete_report(report_id: int, session: Session = Depends(get_session)):
    r = session.get(NarrativeReport, report_id)
    if not r:
        raise HTTPException(status_code=404, detail="Report not found")
    session.delete(r)
    session.commit()
    return {"deleted": report_id}
