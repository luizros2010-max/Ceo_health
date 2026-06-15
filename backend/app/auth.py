"""Lightweight auth for self-hosted family use.

- Passwords: PBKDF2-HMAC-SHA256 (stdlib, no extra deps).
- Sessions: HMAC-signed cookie carrying the patient id (no server-side store).

Designed for a small trusted group on a private network (Tailscale), not as a
hardened public auth system. Set a long SECRET_KEY in .env so sessions persist
across restarts.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from typing import Optional

from fastapi import Depends, HTTPException, Request
from sqlmodel import Session, select

from .config import settings
from .db import get_session
from .models import Patient

COOKIE_NAME = "ceo_session"
_SECRET = (settings.secret_key or secrets.token_hex(32)).encode()


# ---- password hashing ----
def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)
    return f"{salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: Optional[str]) -> bool:
    if not stored or "$" not in stored:
        return False
    salt_hex, dk_hex = stored.split("$", 1)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), 200_000)
    return hmac.compare_digest(dk.hex(), dk_hex)


# ---- session token ----
def make_token(patient_id: int) -> str:
    sig = hmac.new(_SECRET, str(patient_id).encode(), hashlib.sha256).hexdigest()
    return f"{patient_id}.{sig}"


def parse_token(token: Optional[str]) -> Optional[int]:
    if not token or "." not in token:
        return None
    pid, sig = token.rsplit(".", 1)
    expected = hmac.new(_SECRET, pid.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return None
    try:
        return int(pid)
    except ValueError:
        return None


# ---- FastAPI dependencies ----
def current_patient_id(request: Request) -> int:
    """Required auth: the logged-in patient's id, or 401."""
    if not settings.require_auth:
        # Single-user mode: fall back to the first patient.
        from .db import engine

        with Session(engine) as s:
            p = s.exec(select(Patient)).first()
            if p:
                return p.id
        raise HTTPException(status_code=401, detail="No patient")
    pid = parse_token(request.cookies.get(COOKIE_NAME))
    if pid is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return pid


def current_patient(
    pid: int = Depends(current_patient_id), session: Session = Depends(get_session)
) -> Patient:
    p = session.get(Patient, pid)
    if not p:
        raise HTTPException(status_code=401, detail="Unknown patient")
    return p


def current_admin(patient: Patient = Depends(current_patient)) -> Patient:
    if not patient.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")
    return patient
