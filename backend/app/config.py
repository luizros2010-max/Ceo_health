"""Application settings. Secrets are read server-side only and never sent to the frontend."""
from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root is two levels up from this file: backend/app/config.py -> repo root.
REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Claude API key — used only by the backend extraction/analysis layers.
    anthropic_api_key: str = ""

    # Session signing secret (set a long random value in .env for multi-user/self-host;
    # if empty, a random per-process key is used and sessions reset on restart).
    secret_key: str = ""
    # Require login. Turn off only for single-user local use.
    require_auth: bool = True

    # Models: Opus for hard scans (Phase 3), Sonnet for clean text PDFs.
    extract_model: str = "claude-sonnet-4-6"
    extract_model_vision: str = "claude-opus-4-8"
    prompt_version: str = "v1"

    # Oura Ring personal access token (server-side only). Get one at
    # https://cloud.ouraring.com/personal-access-tokens
    oura_token: str = ""
    oura_auto_sync: bool = True          # sync on startup + on an interval when a token is set
    oura_sync_interval_hours: int = 12
    oura_sync_days: int = 14             # lookback window per auto-sync

    # Storage locations (relative paths resolved against repo root).
    db_path: str = "data/ceo_health.db"
    documents_dir: str = "data/documents"

    @property
    def db_file(self) -> Path:
        p = Path(self.db_path)
        return p if p.is_absolute() else REPO_ROOT / p

    @property
    def documents_path(self) -> Path:
        p = Path(self.documents_dir)
        return p if p.is_absolute() else REPO_ROOT / p

    @property
    def has_api_key(self) -> bool:
        return bool(self.anthropic_api_key.strip())

    @property
    def has_oura(self) -> bool:
        return bool(self.oura_token.strip())


settings = Settings()
