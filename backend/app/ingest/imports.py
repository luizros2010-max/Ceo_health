"""Import helpers usable from both the CLI and the web (per-patient scoped)."""
from __future__ import annotations

import csv
import io
import json
from datetime import datetime

from sqlmodel import Session, select

from ..models import NarrativeReport, Observation, Patient, SourceDocument
from .normalize import convert_value, match_biomarker, parse_reference_range

_DATE_FORMATS = ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%d/%m/%Y", "%Y")


def _parse_date(value: str):
    value = (value or "").strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _source(session: Session, name: str, patient_id: int | None) -> SourceDocument:
    doc = session.exec(
        select(SourceDocument).where(
            SourceDocument.original_name == name, SourceDocument.patient_id == patient_id
        )
    ).first()
    if doc:
        return doc
    doc = SourceDocument(
        patient_id=patient_id, file_sha256=f"csv-import:{patient_id}:{name}", file_path="",
        original_name=name, mime_type="text/csv", source_type="manual", ingest_status="reviewed",
    )
    session.add(doc)
    session.flush()
    return doc


def import_csv_text(session: Session, text: str, source_name: str, patient_id: int | None) -> dict:
    """Import a long-format CSV (biomarker,date,value,unit[,ref_range]) as confirmed rows."""
    doc = _source(session, source_name, patient_id)
    imported = duplicates = skipped = unmatched = 0
    unmatched_names: set[str] = set()

    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        name = (row.get("biomarker") or "").strip()
        raw_value = (row.get("value") or "").strip()
        date = _parse_date(row.get("date") or "")
        unit = (row.get("unit") or "").strip() or None
        ref_raw = (row.get("ref_range") or "").strip() or None
        if not name or not raw_value or date is None:
            skipped += 1
            continue
        try:
            value = float(raw_value.replace(",", "."))
        except ValueError:
            skipped += 1
            continue
        match = match_biomarker(session, name)
        if not match.biomarker:
            unmatched += 1
            unmatched_names.add(name)
            continue
        conv = convert_value(session, match.biomarker, value, unit)
        exists = session.exec(
            select(Observation).where(
                Observation.biomarker_id == match.biomarker.id,
                Observation.collection_date == date,
                Observation.source_document_id == doc.id,
            )
        ).first()
        if exists:
            duplicates += 1
            continue
        ref_low, ref_high = parse_reference_range(ref_raw) if ref_raw else (None, None)
        if ref_low is None and ref_high is None:
            ref_low, ref_high, ref_source = (
                match.biomarker.default_ref_low, match.biomarker.default_ref_high, "catalog_default")
        else:
            ref_source = "report"
        session.add(Observation(
            source_document_id=doc.id, patient_id=patient_id, raw_name=name, raw_value=raw_value,
            raw_unit=unit, raw_ref_range=ref_raw, biomarker_id=match.biomarker.id,
            value_num=conv.value_num, canonical_unit=conv.canonical_unit, ref_low=ref_low,
            ref_high=ref_high, ref_source=ref_source, collection_date=date,
            extraction_method="manual", mapping_confidence=1.0, status="confirmed",
        ))
        imported += 1
    session.commit()
    return {"imported": imported, "duplicates": duplicates, "skipped": skipped,
            "unmatched": unmatched, "unmatched_names": sorted(unmatched_names)}


def import_reports_json(session: Session, text: str, patient_id: int | None) -> dict:
    items = json.loads(text)
    imported = duplicates = 0
    for item in items:
        title = (item.get("title") or "").strip()
        if not title:
            continue
        report_date = _parse_date(str(item.get("report_date") or ""))
        exists = session.exec(
            select(NarrativeReport).where(
                NarrativeReport.title == title, NarrativeReport.report_date == report_date,
                NarrativeReport.patient_id == patient_id,
            )
        ).first()
        if exists:
            duplicates += 1
            continue
        session.add(NarrativeReport(
            patient_id=patient_id, title=title, category=(item.get("category") or None),
            report_date=report_date, facility=(item.get("facility") or None),
            body=item.get("body") or "", impression=(item.get("impression") or None),
        ))
        imported += 1
    session.commit()
    return {"imported": imported, "duplicates": duplicates}
