"""SQLModel tables — the schema is the source of truth.

Core idea: store what the lab *literally reported* (raw, immutable audit trail)
separately from the *canonical biomarker* it maps to (normalized, queryable across
decades). Normalization is a derived layer that can be recomputed without re-uploading.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlmodel import Field, SQLModel


def _now() -> datetime:
    return datetime.utcnow()


class Patient(SQLModel, table=True):
    __tablename__ = "patient"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    date_of_birth: Optional[date] = None
    sex: Optional[str] = None  # 'male' | 'female' | other — feeds sex-specific ranges
    created_at: datetime = Field(default_factory=_now)


class SourceDocument(SQLModel, table=True):
    __tablename__ = "source_document"

    id: Optional[int] = Field(default=None, primary_key=True)
    patient_id: Optional[int] = Field(default=None, foreign_key="patient.id", index=True)
    file_sha256: str = Field(unique=True, index=True)
    file_path: str
    original_name: str
    mime_type: str
    source_type: str = "pdf"  # 'pdf' | 'scan' | 'manual'
    lab_name: Optional[str] = None
    collection_date: Optional[date] = None  # the DRAW date = the time axis
    report_date: Optional[date] = None
    ingest_status: str = "uploaded"  # 'uploaded'|'parsed'|'reviewed'|'failed'
    raw_text: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=_now)


class Biomarker(SQLModel, table=True):
    """Canonical catalog — collapses naming variants into one trend line."""

    __tablename__ = "biomarker"

    id: Optional[int] = Field(default=None, primary_key=True)
    slug: str = Field(unique=True, index=True)  # e.g. 'glucose_fasting'
    display_name: str
    category: Optional[str] = None
    canonical_unit: str
    loinc_code: Optional[str] = None
    default_ref_low: Optional[float] = None
    default_ref_high: Optional[float] = None
    higher_is_better: Optional[bool] = None
    description: Optional[str] = None


class BiomarkerAlias(SQLModel, table=True):
    __tablename__ = "biomarker_alias"

    id: Optional[int] = Field(default=None, primary_key=True)
    biomarker_id: int = Field(foreign_key="biomarker.id", index=True)
    alias_text: str = Field(unique=True, index=True)  # normalized, accent-folded
    unit_hint: Optional[str] = None


class UnitConversion(SQLModel, table=True):
    """Per-biomarker because mg/dL<->mmol/L factors are analyte-specific."""

    __tablename__ = "unit_conversion"

    id: Optional[int] = Field(default=None, primary_key=True)
    biomarker_id: int = Field(foreign_key="biomarker.id", index=True)
    from_unit: str
    to_unit: str
    factor: float
    offset: float = 0.0


class Observation(SQLModel, table=True):
    """Time-series fact table. One row per analyte per report. Every chart queries it."""

    __tablename__ = "observation"

    id: Optional[int] = Field(default=None, primary_key=True)
    source_document_id: int = Field(foreign_key="source_document.id", index=True)
    patient_id: Optional[int] = Field(default=None, foreign_key="patient.id", index=True)

    # Raw — never overwritten.
    raw_name: str
    raw_value: Optional[str] = None  # TEXT preserves "<5", "negativo"
    raw_unit: Optional[str] = None
    raw_ref_range: Optional[str] = None

    # Normalized.
    biomarker_id: Optional[int] = Field(default=None, foreign_key="biomarker.id", index=True)
    value_num: Optional[float] = None  # in canonical_unit
    canonical_unit: Optional[str] = None
    ref_low: Optional[float] = None
    ref_high: Optional[float] = None
    ref_source: Optional[str] = None  # 'report' | 'catalog_default'
    operator: str = "="  # '=' | '<' | '>' | '<=' | '>='

    # Provenance + trust.
    collection_date: Optional[date] = Field(default=None, index=True)  # denormalized
    page_index: Optional[int] = None
    bbox: Optional[str] = None  # JSON [x0,y0,x1,y1]
    source_text_snippet: Optional[str] = None
    extraction_method: str = "text_pdf"  # 'text_pdf' | 'vision' | 'manual'
    mapping_confidence: float = 0.0
    status: str = Field(default="needs_review", index=True)  # 'needs_review'|'confirmed'|'rejected'
    created_at: datetime = Field(default_factory=_now)


class ExtractionRun(SQLModel, table=True):
    __tablename__ = "extraction_run"

    id: Optional[int] = Field(default=None, primary_key=True)
    source_document_id: int = Field(foreign_key="source_document.id", index=True)
    model_id: str
    prompt_version: str
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None
    ms: Optional[int] = None
    ok: bool = True
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=_now)
