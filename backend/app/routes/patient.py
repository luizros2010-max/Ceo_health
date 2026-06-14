"""Patient profile — name, date of birth, sex (feeds age/sex into analysis)."""
from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from ..db import get_session
from ..models import Patient

router = APIRouter(prefix="/api/patient", tags=["patient"])


class PatientPatch(BaseModel):
    name: Optional[str] = None
    date_of_birth: Optional[date] = None
    sex: Optional[str] = None


@router.get("")
def get_patient(session: Session = Depends(get_session)):
    p = session.exec(select(Patient)).first()
    if not p:
        raise HTTPException(status_code=404, detail="No patient")
    return p


@router.patch("")
def patch_patient(body: PatientPatch, session: Session = Depends(get_session)):
    p = session.exec(select(Patient)).first()
    if not p:
        p = Patient(name=body.name or "Me")
        session.add(p)
    if body.name is not None:
        p.name = body.name
    if body.date_of_birth is not None:
        p.date_of_birth = body.date_of_birth
    if body.sex is not None:
        p.sex = body.sex
    session.add(p)
    session.commit()
    session.refresh(p)
    return p
