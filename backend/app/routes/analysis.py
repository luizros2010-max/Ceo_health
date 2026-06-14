"""Analysis routes. Phase 4 will add user-initiated, minimal-slice Claude calls here.

For now only the privacy-safe status endpoint exists: it reports whether a key is
configured WITHOUT ever returning the key itself.
"""
from __future__ import annotations

from fastapi import APIRouter

from ..config import settings

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


@router.get("/status")
def analysis_status():
    # Never returns the key — only whether the AI layer is available.
    return {
        "api_key_configured": settings.has_api_key,
        "extract_model": settings.extract_model,
        "phase4_enabled": False,
    }
