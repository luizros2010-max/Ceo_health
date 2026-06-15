"""Pipeline orchestrator: intake -> extract -> normalize -> validate -> persist.

Stages communicate through the DB, so a single document can be reprocessed without
re-upload. Confirmed observations are never overwritten by reprocessing.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

from sqlmodel import Session, select

from ..config import settings
from ..models import ExtractionRun, NarrativeReport, Observation, Patient, SourceDocument
from . import extract_llm, extract_rules, normalize, validate
from .extract_pdf import extract_pdf
from .intake import PDF_MIME, source_type_for, store_document

# Confidence at/above which a row is auto-confirmed; below it goes to the review queue.
AUTO_CONFIRM_THRESHOLD = 0.90


@dataclass
class IngestSummary:
    document_id: int
    is_duplicate: bool
    status: str
    observations_total: int = 0
    confirmed: int = 0
    needs_review: int = 0
    extraction_error: Optional[str] = None
    message: str = ""


def _parse_iso_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(value.strip()[:10], fmt).date()
        except (ValueError, TypeError):
            continue
    return None


def ingest_document(
    session: Session,
    *,
    data: bytes,
    mime_type: str,
    original_name: str,
    patient_id: int | None = None,
) -> IngestSummary:
    from .intake import sha256_bytes

    digest = sha256_bytes(data)

    # Dedup at document level by sha256, scoped to this patient.
    dedup = select(SourceDocument).where(SourceDocument.file_sha256 == digest)
    if patient_id is not None:
        dedup = dedup.where(SourceDocument.patient_id == patient_id)
    existing = session.exec(dedup).first()
    if existing:
        counts = _count_observations(session, existing.id)
        return IngestSummary(
            document_id=existing.id,
            is_duplicate=True,
            status=existing.ingest_status,
            observations_total=counts[0],
            confirmed=counts[1],
            needs_review=counts[2],
            message="Document already ingested (identical content).",
        )

    _, dest = store_document(data, mime_type, original_name)
    patient = session.get(Patient, patient_id) if patient_id else session.exec(select(Patient)).first()

    doc = SourceDocument(
        patient_id=patient.id if patient else None,
        file_sha256=digest,
        file_path=str(dest),
        original_name=original_name,
        mime_type=mime_type,
        source_type=source_type_for(mime_type),
        ingest_status="uploaded",
    )
    session.add(doc)
    session.flush()

    # Phase 1 handles text PDFs. Non-PDF (scans) are stored and flagged for Phase 3 OCR.
    if mime_type != PDF_MIME:
        doc.ingest_status = "failed"
        doc.notes = "Scan/image stored. OCR extraction arrives in Phase 3."
        session.add(doc)
        return IngestSummary(
            document_id=doc.id, is_duplicate=False, status=doc.ingest_status,
            message="Image stored; OCR not yet available (Phase 3).",
        )

    pdf = extract_pdf(str(dest))
    doc.raw_text = pdf.full_text

    if not pdf.has_text:
        doc.ingest_status = "failed"
        doc.notes = "No extractable text (likely a scanned PDF). OCR arrives in Phase 3."
        session.add(doc)
        return IngestSummary(
            document_id=doc.id, is_duplicate=False, status=doc.ingest_status,
            message="No extractable text — looks like a scanned PDF (Phase 3 / OCR).",
        )

    # Choose extraction engine: Claude when a key is set, else the built-in
    # key-free text parser. Fall back to the parser if the LLM call fails.
    rows = []
    method = "text_rules"
    if settings.has_api_key:
        result = extract_llm.extract_from_text(pdf.full_text)
        session.add(ExtractionRun(
            source_document_id=doc.id, model_id=result.model_id or "n/a", prompt_version="v1",
            tokens_in=result.tokens_in, tokens_out=result.tokens_out, ms=result.ms,
            ok=result.ok, error=result.error,
        ))
        if result.ok:
            rows = result.rows
            method = "text_pdf"
            doc.lab_name = result.lab_name
            doc.collection_date = _parse_iso_date(result.collection_date)
            doc.report_date = _parse_iso_date(result.report_date)

    if not rows:  # no key, or LLM failed/empty -> deterministic parser
        rr = extract_rules.extract_from_text(session, pdf.full_text)
        session.add(ExtractionRun(
            source_document_id=doc.id, model_id="rules", prompt_version="v1", ok=True,
        ))
        rows = rr.rows
        method = "text_rules"
        if doc.collection_date is None:
            doc.collection_date = rr.collection_date

    if not rows:
        # Maybe it's an imaging / narrative report (echo, MRI, ultrasound, endoscopy).
        narrative = extract_rules.detect_narrative(pdf.full_text)
        if narrative:
            session.add(NarrativeReport(
                patient_id=doc.patient_id,
                source_document_id=doc.id,
                title=narrative.title,
                category=narrative.category,
                report_date=narrative.report_date,
                impression=narrative.impression,
                body=narrative.body,
            ))
            doc.ingest_status = "reviewed"
            doc.collection_date = doc.collection_date or narrative.report_date
            doc.notes = f"Imported as {narrative.category} report."
            session.add(doc)
            return IngestSummary(
                document_id=doc.id, is_duplicate=False, status=doc.ingest_status,
                message=f"Saved as an imaging/{narrative.category} report (see Imaging & Reports).",
            )
        doc.ingest_status = "failed"
        doc.notes = ("Couldn't recognize biomarker values in this PDF's text. "
                     "You can add values via manual entry, or set an ANTHROPIC_API_KEY "
                     "for AI extraction of unusual formats.")
        session.add(doc)
        return IngestSummary(
            document_id=doc.id, is_duplicate=False, status=doc.ingest_status,
            message=doc.notes,
        )

    birth = patient.date_of_birth if patient else None
    confirmed = needs_review = 0

    for r in rows:
        match = normalize.match_biomarker(session, r.raw_analyte_name)
        conv = (
            normalize.convert_value(session, match.biomarker, r.value_numeric, r.unit_raw)
            if match.biomarker
            else normalize.Converted(r.value_numeric, None, False)
        )

        ref_low, ref_high, ref_source = r.reference_low, r.reference_high, None
        if ref_low is None and ref_high is None and r.reference_raw:
            ref_low, ref_high = normalize.parse_reference_range(r.reference_raw)
        if ref_low is not None or ref_high is not None:
            ref_source = "report"
        elif match.biomarker:
            ref_low = match.biomarker.default_ref_low
            ref_high = match.biomarker.default_ref_high
            ref_source = "catalog_default"

        coll_date = doc.collection_date
        val = validate.validate_row(
            value_raw=r.value_raw,
            value_num=conv.value_num,
            source_text_snippet=r.source_text_snippet,
            full_text=pdf.full_text,
            ref_low=ref_low,
            ref_high=ref_high,
            collection_date=coll_date,
            birth_date=birth,
        )
        confidence = validate.compose_confidence(r.confidence, match.match_confidence, val.penalties)

        status = "needs_review"
        if match.biomarker and confidence >= AUTO_CONFIRM_THRESHOLD and val.ok and not conv.note:
            status = "confirmed"

        notes_bits = list(val.issues)
        if conv.note:
            notes_bits.append(conv.note)

        obs = Observation(
            source_document_id=doc.id,
            patient_id=doc.patient_id,
            raw_name=r.raw_analyte_name,
            raw_value=r.value_raw,
            raw_unit=r.unit_raw,
            raw_ref_range=r.reference_raw,
            biomarker_id=match.biomarker.id if match.biomarker else None,
            value_num=conv.value_num,
            canonical_unit=conv.canonical_unit,
            ref_low=ref_low,
            ref_high=ref_high,
            ref_source=ref_source,
            operator=r.operator or "=",
            collection_date=coll_date,
            page_index=r.page_index,
            source_text_snippet=(", ".join(notes_bits) + " | " if notes_bits else "")
            + (r.source_text_snippet or ""),
            extraction_method=method,
            mapping_confidence=confidence,
            status=status,
        )
        session.add(obs)
        if status == "confirmed":
            confirmed += 1
        else:
            needs_review += 1

    doc.ingest_status = "parsed"
    session.add(doc)

    total = confirmed + needs_review
    return IngestSummary(
        document_id=doc.id,
        is_duplicate=False,
        status=doc.ingest_status,
        observations_total=total,
        confirmed=confirmed,
        needs_review=needs_review,
        message=f"Extracted {total} observations ({confirmed} auto-confirmed, "
        f"{needs_review} need review).",
    )


def _count_observations(session: Session, document_id: int) -> tuple[int, int, int]:
    rows = session.exec(
        select(Observation).where(Observation.source_document_id == document_id)
    ).all()
    confirmed = sum(1 for r in rows if r.status == "confirmed")
    needs_review = sum(1 for r in rows if r.status == "needs_review")
    return len(rows), confirmed, needs_review
