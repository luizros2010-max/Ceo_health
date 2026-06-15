"""FastAPI app: mounts the JSON API and (in local-prod) the built frontend.

Bind to 127.0.0.1 only — health data never leaves the machine except for explicit,
user-triggered Claude extraction/analysis calls made server-side.
"""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import REPO_ROOT
from .db import init_db
from .routes import analysis, biomarkers, connectors, documents, observations, patient, reports


log = logging.getLogger("ceo_health")


async def _oura_auto_sync_loop():
    """Periodically sync Oura in the background (non-blocking, errors swallowed)."""
    from sqlmodel import Session

    from .config import settings
    from .connectors.oura import sync_oura
    from .db import engine

    interval = max(1, settings.oura_sync_interval_hours) * 3600
    while True:
        try:
            with Session(engine) as session:
                result = await asyncio.to_thread(
                    sync_oura, session, settings.oura_token, settings.oura_sync_days
                )
            log.info("Oura auto-sync: %s new readings", result.get("added"))
        except Exception as exc:  # noqa: BLE001
            log.warning("Oura auto-sync failed: %s", exc)
        await asyncio.sleep(interval)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    from .config import settings

    task = None
    if settings.has_oura and settings.oura_auto_sync:
        task = asyncio.create_task(_oura_auto_sync_loop())
    try:
        yield
    finally:
        if task:
            task.cancel()


app = FastAPI(title="CEO of Your Own Health", version="0.1.0", lifespan=lifespan)

# Dev convenience: Vite dev server on :5173 talks to the API on :8000.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}


app.include_router(documents.router)
app.include_router(observations.router)
app.include_router(biomarkers.router)
app.include_router(reports.router)
app.include_router(patient.router)
app.include_router(connectors.router)
app.include_router(analysis.router)

# Local-prod: serve the built frontend (frontend/dist) from the same process.
_dist = REPO_ROOT / "frontend" / "dist"
if _dist.exists():

    class SpaStaticFiles(StaticFiles):
        """Serve static assets; fall back to index.html for client-side routes."""

        async def get_response(self, path: str, scope):
            try:
                return await super().get_response(path, scope)
            except StarletteHTTPException as exc:
                if exc.status_code == 404:
                    return FileResponse(_dist / "index.html")
                raise

    app.mount("/", SpaStaticFiles(directory=str(_dist), html=True), name="frontend")
