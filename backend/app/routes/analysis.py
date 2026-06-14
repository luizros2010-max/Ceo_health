"""Phase 4 analysis routes — user-initiated, minimal-slice AI insights.

- /status   : whether the AI layer is available (never returns the key)
- /preview  : the EXACT slice + deterministic flags that would be shared (no LLM)
- /flags    : deterministic trend flags only (no LLM, no key needed)
- /run      : send the minimal slice to Claude and return insights (needs a key)
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session

from ..analysis_service import build_slice, compute_flags, run_analysis
from ..config import settings
from ..db import get_session

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


class AnalysisRequest(BaseModel):
    biomarker_slugs: Optional[list[str]] = None  # None -> all with data
    include_reports: bool = False
    question: Optional[str] = None


@router.get("/status")
def analysis_status():
    # Never returns the key — only whether the AI layer is available.
    return {
        "api_key_configured": settings.has_api_key,
        "extract_model": settings.extract_model,
        "phase4_enabled": True,
    }


@router.post("/preview")
def analysis_preview(body: AnalysisRequest, session: Session = Depends(get_session)):
    """Show exactly what would be shared with Claude — for the 'what will be shared' panel."""
    payload = build_slice(
        session,
        biomarker_slugs=body.biomarker_slugs,
        include_reports=body.include_reports,
    )
    flags = compute_flags(payload)
    n_points = sum(len(s["points"]) for s in payload["biomarkers"])
    return {
        "slice": payload,
        "flags": flags,
        "summary": {
            "biomarkers": len(payload["biomarkers"]),
            "data_points": n_points,
            "reports": len(payload.get("reports", [])),
            "shares_age_sex": payload["subject"]["age"] is not None
            or payload["subject"]["sex"] is not None,
        },
    }


@router.post("/flags")
def analysis_flags(body: AnalysisRequest, session: Session = Depends(get_session)):
    """Deterministic trend flags only — works offline, no API key required."""
    payload = build_slice(session, biomarker_slugs=body.biomarker_slugs)
    return {"flags": compute_flags(payload)}


@router.post("/run")
def analysis_run(body: AnalysisRequest, session: Session = Depends(get_session)):
    payload = build_slice(
        session,
        biomarker_slugs=body.biomarker_slugs,
        include_reports=body.include_reports,
    )
    flags = compute_flags(payload)
    result = run_analysis(payload, flags, question=body.question)
    result["flags"] = flags
    return result
