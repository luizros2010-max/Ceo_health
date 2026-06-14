"""FastAPI app: mounts the JSON API and (in local-prod) the built frontend.

Bind to 127.0.0.1 only — health data never leaves the machine except for explicit,
user-triggered Claude extraction/analysis calls made server-side.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import REPO_ROOT
from .db import init_db
from .routes import analysis, biomarkers, documents, observations


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


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
