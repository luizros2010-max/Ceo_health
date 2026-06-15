"""Wearable connector routes: Oura sync + Apple Health export import."""
from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlmodel import Session

from ..auth import current_patient_id
from ..config import settings
from ..connectors.apple_health import import_apple_health
from ..connectors.oura import sync_oura
from ..db import get_session

router = APIRouter(prefix="/api/connectors", tags=["connectors"])


@router.get("/status")
def status():
    return {
        "oura": {"configured": settings.has_oura},
        "apple_health": {"available": True, "method": "file_import"},
    }


class OuraSync(BaseModel):
    token: str | None = None
    days: int = 90


@router.post("/oura/sync")
def oura_sync(body: OuraSync, session: Session = Depends(get_session), pid: int = Depends(current_patient_id)):
    token = (body.token or settings.oura_token).strip()
    if not token:
        raise HTTPException(status_code=400, detail="No Oura token (set OURA_TOKEN or pass one)")
    return sync_oura(session, token, days=body.days, patient_id=pid)


@router.post("/apple-health")
async def apple_health(file: UploadFile = File(...), session: Session = Depends(get_session),
                       pid: int = Depends(current_patient_id)):
    suffix = ".zip" if (file.filename or "").lower().endswith(".zip") else ".xml"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp_path = tmp.name
        while chunk := await file.read(1 << 20):  # stream in 1MB chunks
            tmp.write(chunk)
    try:
        return import_apple_health(session, tmp_path, patient_id=pid)
    finally:
        Path(tmp_path).unlink(missing_ok=True)
