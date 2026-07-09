"""Iceland trip photo album: passphrase-gated upload + slideshow, stored server-side.

Deliberately separate from the patient auth system (auth.py) — this is a personal
photo page, not health data, so it gets its own single shared passphrase instead
of per-patient accounts.
"""
from __future__ import annotations

import hashlib
import hmac
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, File, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlmodel import Session, select

from ..config import settings
from ..db import get_session
from ..ingest.intake import guess_extension, sha256_bytes
from ..models import TripPhoto

router = APIRouter(prefix="/api/iceland", tags=["iceland"])

COOKIE_NAME = "iceland_session"
_SECRET = (settings.secret_key or "iceland-dev-secret").encode()


def _session_token() -> str:
    return hmac.new(_SECRET, b"unlocked", hashlib.sha256).hexdigest()


def require_unlocked(iceland_session: Optional[str] = Cookie(default=None)) -> None:
    if not iceland_session or not hmac.compare_digest(iceland_session, _session_token()):
        raise HTTPException(status_code=401, detail="Locked")


def _photo_out(p: TripPhoto) -> dict:
    return {"id": p.id, "original_name": p.original_name, "mime_type": p.mime_type,
            "created_at": p.created_at}


class LoginBody(BaseModel):
    password: str


@router.post("/login")
def login(body: LoginBody, response: Response):
    if not hmac.compare_digest(body.password, settings.iceland_trip_password):
        raise HTTPException(status_code=401, detail="Incorrect passphrase")
    response.set_cookie(
        COOKIE_NAME, _session_token(), httponly=True, samesite="lax", max_age=60 * 60 * 24 * 30
    )
    return {"ok": True}


@router.get("/session")
def session_status(_: None = Depends(require_unlocked)):
    return {"unlocked": True}


@router.post("/photos")
async def upload_photos(
    files: list[UploadFile] = File(...),
    session: Session = Depends(get_session),
    _: None = Depends(require_unlocked),
):
    created: list[TripPhoto] = []
    for file in files:
        data = await file.read()
        if not data:
            continue
        digest = sha256_bytes(data)
        ext = guess_extension(file.content_type or "", file.filename or "")
        dest = settings.iceland_photos_path / f"{digest}.{ext}"
        if not dest.exists():
            dest.write_bytes(data)
        photo = TripPhoto(
            file_path=str(dest),
            original_name=file.filename or "photo",
            mime_type=file.content_type or "application/octet-stream",
        )
        session.add(photo)
        created.append(photo)
    session.commit()
    for p in created:
        session.refresh(p)
    return [_photo_out(p) for p in created]


@router.get("/photos")
def list_photos(session: Session = Depends(get_session), _: None = Depends(require_unlocked)):
    photos = session.exec(select(TripPhoto).order_by(TripPhoto.created_at)).all()
    return [_photo_out(p) for p in photos]


@router.get("/photos/{photo_id}/file")
def get_photo_file(
    photo_id: int, session: Session = Depends(get_session), _: None = Depends(require_unlocked)
):
    photo = session.get(TripPhoto, photo_id)
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    path = Path(photo.file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File missing on disk")
    return FileResponse(path, media_type=photo.mime_type, filename=photo.original_name)


@router.delete("/photos/{photo_id}")
def delete_photo(
    photo_id: int, session: Session = Depends(get_session), _: None = Depends(require_unlocked)
):
    photo = session.get(TripPhoto, photo_id)
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    session.delete(photo)
    session.commit()
    return {"deleted": photo_id}


@router.delete("/photos")
def clear_photos(session: Session = Depends(get_session), _: None = Depends(require_unlocked)):
    photos = session.exec(select(TripPhoto)).all()
    for p in photos:
        session.delete(p)
    session.commit()
    return {"deleted": len(photos)}
