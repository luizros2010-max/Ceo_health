"""Auth + profile management for multi-patient (family) use."""
from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlmodel import Session, select

from ..auth import (
    COOKIE_NAME,
    current_admin,
    current_patient,
    hash_password,
    make_token,
    verify_password,
)
from ..db import get_session
from ..models import NarrativeReport, Observation, Patient, SourceDocument

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
            "is_admin": patient.is_admin,
            "date_of_birth": patient.date_of_birth, "sex": patient.sex}


@router.post("/register")
def register(body: Credentials, response: Response, session: Session = Depends(get_session)):
    if session.exec(select(Patient).where(Patient.username == body.username)).first():
        raise HTTPException(status_code=400, detail="Username already taken")

    # First registrant claims the pre-existing credential-less default profile so the
    # owner's existing data stays with their account; later registrants get new profiles.
    profiles = session.exec(select(Patient).where(Patient.username.is_not(None))).all()
    is_first = not profiles
    target = None
    if is_first:
        target = session.exec(select(Patient).where(Patient.username.is_(None))).first()
    if target is None:
        target = Patient(name=body.name or body.username)
        session.add(target)

    target.username = body.username
    target.password_hash = hash_password(body.password)
    target.is_admin = is_first  # first profile is the family admin
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


# ---- admin: manage family profiles ----
class ResetPassword(BaseModel):
    password: str


@router.get("/profiles")
def list_profiles(admin: Patient = Depends(current_admin), session: Session = Depends(get_session)):
    profiles = session.exec(select(Patient).where(Patient.username.is_not(None))).all()
    out = []
    for p in profiles:
        n_obs = len(session.exec(
            select(Observation).where(Observation.patient_id == p.id, Observation.status == "confirmed")
        ).all())
        out.append({"id": p.id, "name": p.name, "username": p.username, "is_admin": p.is_admin,
                    "is_you": p.id == admin.id, "observations": n_obs})
    return out


@router.post("/profiles")
def create_profile(body: Credentials, admin: Patient = Depends(current_admin),
                   session: Session = Depends(get_session)):
    if session.exec(select(Patient).where(Patient.username == body.username)).first():
        raise HTTPException(status_code=400, detail="Username already taken")
    p = Patient(
        name=body.name or body.username, username=body.username,
        password_hash=hash_password(body.password),
        date_of_birth=body.date_of_birth, sex=body.sex,
    )
    session.add(p)
    session.commit()
    session.refresh(p)
    return {"id": p.id, "name": p.name, "username": p.username}


@router.post("/profiles/{pid}/reset-password")
def reset_password(pid: int, body: ResetPassword, admin: Patient = Depends(current_admin),
                   session: Session = Depends(get_session)):
    p = session.get(Patient, pid)
    if not p or p.username is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    p.password_hash = hash_password(body.password)
    session.add(p)
    session.commit()
    return {"ok": True}


@router.delete("/profiles/{pid}")
def delete_profile(pid: int, admin: Patient = Depends(current_admin),
                   session: Session = Depends(get_session)):
    if pid == admin.id:
        raise HTTPException(status_code=400, detail="You can't delete your own admin profile")
    p = session.get(Patient, pid)
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")
    for o in session.exec(select(Observation).where(Observation.patient_id == pid)).all():
        session.delete(o)
    for r in session.exec(select(NarrativeReport).where(NarrativeReport.patient_id == pid)).all():
        session.delete(r)
    for d in session.exec(select(SourceDocument).where(SourceDocument.patient_id == pid)).all():
        session.delete(d)
    session.delete(p)
    session.commit()
    return {"deleted": pid}
