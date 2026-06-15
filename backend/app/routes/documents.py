"""Document routes: upload, list, detail, file stream, edit, delete."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlmodel import Session, select

from ..auth import current_patient_id
from ..db import get_session
from ..ingest.pipeline import ingest_document
from ..models import Observation, SourceDocument
from ..schemas import DocumentPatch

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("")
async def upload_document(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    pid: int = Depends(current_patient_id),
):
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    summary = ingest_document(
        session,
        data=data,
        mime_type=file.content_type or "application/octet-stream",
        original_name=file.filename or "upload",
        patient_id=pid,
    )
    session.commit()
    return summary


@router.get("")
def list_documents(session: Session = Depends(get_session), pid: int = Depends(current_patient_id)):
    docs = session.exec(
        select(SourceDocument).where(SourceDocument.patient_id == pid).order_by(SourceDocument.created_at.desc())
    ).all()
    out = []
    for d in docs:
        obs = session.exec(
            select(Observation).where(Observation.source_document_id == d.id)
        ).all()
        out.append(
            {
                "id": d.id,
                "original_name": d.original_name,
                "lab_name": d.lab_name,
                "source_type": d.source_type,
                "collection_date": d.collection_date,
                "report_date": d.report_date,
                "ingest_status": d.ingest_status,
                "notes": d.notes,
                "created_at": d.created_at,
                "observations_total": len(obs),
                "confirmed": sum(1 for o in obs if o.status == "confirmed"),
                "needs_review": sum(1 for o in obs if o.status == "needs_review"),
            }
        )
    return out


@router.get("/{doc_id}")
def get_document(doc_id: int, session: Session = Depends(get_session), pid: int = Depends(current_patient_id)):
    doc = session.get(SourceDocument, doc_id)
    if not doc or doc.patient_id != pid:
        raise HTTPException(status_code=404, detail="Document not found")
    obs = session.exec(
        select(Observation).where(Observation.source_document_id == doc_id)
    ).all()
    return {"document": doc, "observations": obs}


@router.get("/{doc_id}/file")
def get_document_file(doc_id: int, session: Session = Depends(get_session), pid: int = Depends(current_patient_id)):
    doc = session.get(SourceDocument, doc_id)
    if not doc or doc.patient_id != pid:
        raise HTTPException(status_code=404, detail="Document not found")
    path = Path(doc.file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File missing on disk")
    return FileResponse(path, media_type=doc.mime_type, filename=doc.original_name)


@router.patch("/{doc_id}")
def patch_document(
    doc_id: int, patch: DocumentPatch, session: Session = Depends(get_session),
    pid: int = Depends(current_patient_id),
):
    doc = session.get(SourceDocument, doc_id)
    if not doc or doc.patient_id != pid:
        raise HTTPException(status_code=404, detail="Document not found")
    if patch.lab_name is not None:
        doc.lab_name = patch.lab_name
    if patch.notes is not None:
        doc.notes = patch.notes
    if patch.collection_date is not None:
        doc.collection_date = patch.collection_date
        # Keep observations' denormalized date in sync.
        for o in session.exec(
            select(Observation).where(Observation.source_document_id == doc_id)
        ).all():
            o.collection_date = patch.collection_date
            session.add(o)
    session.add(doc)
    session.commit()
    return doc


@router.delete("/{doc_id}")
def delete_document(doc_id: int, session: Session = Depends(get_session), pid: int = Depends(current_patient_id)):
    doc = session.get(SourceDocument, doc_id)
    if not doc or doc.patient_id != pid:
        raise HTTPException(status_code=404, detail="Document not found")
    for o in session.exec(
        select(Observation).where(Observation.source_document_id == doc_id)
    ).all():
        session.delete(o)
    session.delete(doc)
    session.commit()
    return {"deleted": doc_id}
