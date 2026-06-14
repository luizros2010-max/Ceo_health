"""Phase 4 analysis routes — user-initiated, minimal-slice AI insights.

- /status   : whether the AI layer is available (never returns the key)
- /preview  : the EXACT slice + deterministic flags that would be shared (no LLM)
- /flags    : deterministic trend flags only (no LLM, no key needed)
- /run      : send the minimal slice to Claude and return insights (needs a key)
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from sqlmodel import Session

from ..analysis_service import build_slice, compute_flags, run_analysis, stream_analysis
from ..config import settings
from ..db import get_session
from ..plan_service import compute_plan
from ..scoring import compute_score

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


@router.get("/score")
def analysis_score(session: Session = Depends(get_session)):
    """Transparent health score vs. age-peers (deterministic; no key needed)."""
    return compute_score(session)


@router.get("/plan")
def analysis_plan(session: Session = Depends(get_session)):
    """Action plan: score-gap targets + workout/nutrition/lifestyle levers (deterministic)."""
    return compute_plan(session)


PLAN_QUESTION = (
    "Draft a specific, prioritized workout and nutrition plan to improve my lowest-scoring "
    "areas and raise my overall health score. Give a concrete weekly structure (aerobic + "
    "resistance, adapted to any flagged musculoskeletal findings), the highest-impact nutrition "
    "changes, and what to discuss with my physician. Be specific with numbers."
)


@router.post("/plan/stream")
def analysis_plan_stream(session: Session = Depends(get_session)):
    """Stream an AI-drafted plan from the minimal slice (needs a key)."""
    if not settings.has_api_key:
        return JSONResponse(status_code=400, content={"ok": False, "error": "no_api_key"})
    payload = build_slice(session, include_reports=True)
    flags = compute_flags(payload)
    gen = stream_analysis(payload, flags, question=PLAN_QUESTION)
    return StreamingResponse(gen, media_type="text/plain; charset=utf-8")


@router.post("/stream")
def analysis_stream(body: AnalysisRequest, session: Session = Depends(get_session)):
    """Stream the AI summary token-by-token (text/plain chunks)."""
    if not settings.has_api_key:
        return JSONResponse(status_code=400, content={"ok": False, "error": "no_api_key"})
    payload = build_slice(
        session, biomarker_slugs=body.biomarker_slugs, include_reports=body.include_reports
    )
    flags = compute_flags(payload)
    gen = stream_analysis(payload, flags, question=body.question)
    return StreamingResponse(gen, media_type="text/plain; charset=utf-8")
