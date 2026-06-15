"""Shared helpers for wearable connectors (Oura, Apple Health).

Wearable readings are written as confirmed observations under a per-source
synthetic document, deduped on (biomarker, date, source) so re-syncing is
idempotent and never duplicates a day's value.
"""
from __future__ import annotations

from datetime import date

from sqlmodel import Session, select

from ..ingest.normalize import convert_value, match_biomarker
from ..models import Observation, Patient, SourceDocument


def get_source(session: Session, name: str) -> SourceDocument:
    doc = session.exec(
        select(SourceDocument).where(SourceDocument.original_name == name)
    ).first()
    if doc:
        return doc
    patient = session.exec(select(Patient)).first()
    doc = SourceDocument(
        patient_id=patient.id if patient else None,
        file_sha256=f"connector:{name}",
        file_path="",
        original_name=name,
        mime_type="application/x-wearable",
        source_type="manual",
        ingest_status="reviewed",
        notes="Wearable connector source.",
    )
    session.add(doc)
    session.flush()
    return doc


def upsert_reading(
    session: Session,
    doc: SourceDocument,
    *,
    slug_or_name: str,
    value: float,
    unit: str | None,
    day: date,
    extraction_method: str,
) -> bool:
    """Insert (or update) one daily reading. Returns True if a new row was added."""
    match = match_biomarker(session, slug_or_name)
    if not match.biomarker:
        return False
    conv = convert_value(session, match.biomarker, value, unit)

    existing = session.exec(
        select(Observation).where(
            Observation.biomarker_id == match.biomarker.id,
            Observation.collection_date == day,
            Observation.source_document_id == doc.id,
        )
    ).first()
    if existing:
        existing.value_num = conv.value_num
        existing.canonical_unit = conv.canonical_unit
        session.add(existing)
        return False

    patient = session.exec(select(Patient)).first()
    session.add(
        Observation(
            source_document_id=doc.id,
            patient_id=patient.id if patient else None,
            raw_name=slug_or_name,
            raw_value=str(value),
            raw_unit=unit,
            biomarker_id=match.biomarker.id,
            value_num=conv.value_num,
            canonical_unit=conv.canonical_unit,
            ref_low=match.biomarker.default_ref_low,
            ref_high=match.biomarker.default_ref_high,
            ref_source="catalog_default",
            collection_date=day,
            extraction_method=extraction_method,
            mapping_confidence=1.0,
            status="confirmed",
        )
    )
    return True
