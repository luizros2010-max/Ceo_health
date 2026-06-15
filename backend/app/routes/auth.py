"""Auth + profile management for multi-patient (family) use."""
from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlmodel import Session, select

from ..auth import COOKIE_NAME, current_patient, hash_password, make_token, verify_password
from ..db import get_session
from ..models import Patient

router = APIRouter(prefix="/api/auth", tags=["auth"])


class Credentials(BaseModel):
    username: str
    password: str
    name: Optional[str] = None
    date_of_birth: Optional[date] = None
    sex: Optional[str] = None


def _set_cookie(resp: Response, patient_id: int) -> None:
    resp.set_cookie(
        COOKIE_NAME, make_token(patient_id), httponly=True, samesite="lax", max_age=60 * 60 * 24 * 30
    )


@router.get("/me")
def me(session: Session = Depends(get_session)):
    # Reports whether any profile exists yet (so the UI can show register vs login).
    any_profile = session.exec(select(Patient).where(Patient.username.is_not(None))).first()
    return {"has_profiles": any_profile is not None}


@router.get("/session")
def whoami(patient: Patient = Depends(current_patient)):
    return {"id": patient.id, "name": patient.name, "username": patient.username,
            "date_of_birth": patient.date_of_birth, "sex": patient.sex}


@router.post("/register")
def register(body: Credentials, response: Response, session: Session = Depends(get_session)):
    if session.exec(select(Patient).where(Patient.username == body.username)).first():
        raise HTTPException(status_code=400, detail="Username already taken")

    # First registrant claims the pre-existing credential-less default profile so the
    # owner's existing data stays with their account; later registrants get new profiles.
    profiles = session.exec(select(Patient).where(Patient.username.is_not(None))).all()
    target = None
    if not profiles:
        target = session.exec(select(Patient).where(Patient.username.is_(None))).first()
    if target is None:
        target = Patient(name=body.name or body.username)
        session.add(target)

    target.username = body.username
    target.password_hash = hash_password(body.password)
    if body.name:
        target.name = body.name
    if body.date_of_birth:
        target.date_of_birth = body.date_of_birth
    if body.sex:
        target.sex = body.sex
    session.add(target)
    session.commit()
    session.refresh(target)
    _set_cookie(response, target.id)
    return {"id": target.id, "name": target.name, "username": target.username}


@router.post("/login")
def login(body: Credentials, response: Response, session: Session = Depends(get_session)):
    p = session.exec(select(Patient).where(Patient.username == body.username)).first()
    if not p or not verify_password(body.password, p.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    _set_cookie(response, p.id)
    return {"id": p.id, "name": p.name, "username": p.username}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME)
    return {"ok": True}
