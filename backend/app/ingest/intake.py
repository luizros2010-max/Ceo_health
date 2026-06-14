"""Intake: content-addressed storage + dedup + type detection."""
from __future__ import annotations

import hashlib
from pathlib import Path

from ..config import settings

PDF_MIME = "application/pdf"
IMAGE_MIMES = {"image/jpeg", "image/png", "image/heic", "image/heif", "image/tiff"}

_EXT_BY_MIME = {
    "application/pdf": "pdf",
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/heic": "heic",
    "image/heif": "heif",
    "image/tiff": "tiff",
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def guess_extension(mime_type: str, original_name: str) -> str:
    if mime_type in _EXT_BY_MIME:
        return _EXT_BY_MIME[mime_type]
    suffix = Path(original_name).suffix.lstrip(".").lower()
    return suffix or "bin"


def source_type_for(mime_type: str) -> str:
    if mime_type == PDF_MIME:
        return "pdf"
    if mime_type in IMAGE_MIMES:
        return "scan"
    return "pdf"


def store_document(data: bytes, mime_type: str, original_name: str) -> tuple[str, Path]:
    """Write bytes immutably to data/documents/<sha256>.<ext>. Returns (sha256, path).

    If the file already exists (same content), it is left untouched — dedup is a no-op.
    """
    digest = sha256_bytes(data)
    ext = guess_extension(mime_type, original_name)
    dest = settings.documents_path / f"{digest}.{ext}"
    if not dest.exists():
        dest.write_bytes(data)
    return digest, dest
