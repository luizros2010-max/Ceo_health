"""Import structured biomarker history from a long-format CSV.

Use this when you already have tidy values (e.g. exported from a tracking
spreadsheet) and don't need LLM extraction. Imported rows are written as
*confirmed* observations so they appear on timelines immediately.

CSV format (header required), one measurement per row:

    biomarker,date,value,unit
    Glucose,2019-10-01,91,mg/dl
    LDL cholesterol,2018-05-01,132,mg/dl

- `biomarker` may be a catalog slug (e.g. ``ldl_cholesterol``) or any name/alias
  (English or Portuguese) — it is matched against the catalog, with fuzzy fallback.
- `date` accepts YYYY-MM-DD, YYYY, MM/DD/YYYY, etc.
- `unit` is optional; values are converted into each biomarker's canonical unit.

Usage:
    python import_csv.py path/to/data.csv [--source-name "My Spreadsheet"]

Privacy: this only writes to your local SQLite DB. Keep your CSV out of git
(the repo's ``data/`` directory is gitignored).
"""
from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime

from sqlmodel import Session, select

from app.db import engine, init_db
from app.ingest.normalize import convert_value, match_biomarker, parse_reference_range
from app.models import Observation, Patient, SourceDocument

_DATE_FORMATS = ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%d/%m/%Y", "%Y")


def parse_date(value: str):
    value = (value or "").strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def get_or_create_source(session: Session, name: str) -> SourceDocument:
    doc = session.exec(
        select(SourceDocument).where(SourceDocument.original_name == name)
    ).first()
    if doc:
        return doc
    patient = session.exec(select(Patient)).first()
    doc = SourceDocument(
        patient_id=patient.id if patient else None,
        file_sha256=f"csv-import:{name}",
        file_path="",
        original_name=name,
        mime_type="text/csv",
        source_type="manual",
        ingest_status="reviewed",
        notes="Imported from a structured CSV.",
    )
    session.add(doc)
    session.flush()
    return doc


def import_csv(path: str, source_name: str) -> dict:
    init_db()
    imported = skipped = unmatched = duplicates = 0
    unmatched_names: set[str] = set()

    with Session(engine) as session:
        doc = get_or_create_source(session, source_name)
        patient = session.exec(select(Patient)).first()

        with open(path, newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                name = (row.get("biomarker") or "").strip()
                raw_value = (row.get("value") or "").strip()
                date = parse_date(row.get("date") or "")
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

                # Dedup: same biomarker + date + value from this source.
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
                    ref_low = match.biomarker.default_ref_low
                    ref_high = match.biomarker.default_ref_high
                    ref_source = "catalog_default"
                else:
                    ref_source = "report"

                session.add(
                    Observation(
                        source_document_id=doc.id,
                        patient_id=patient.id if patient else None,
                        raw_name=name,
                        raw_value=raw_value,
                        raw_unit=unit,
                        raw_ref_range=ref_raw,
                        biomarker_id=match.biomarker.id,
                        value_num=conv.value_num,
                        canonical_unit=conv.canonical_unit,
                        ref_low=ref_low,
                        ref_high=ref_high,
                        ref_source=ref_source,
                        collection_date=date,
                        extraction_method="manual",
                        mapping_confidence=1.0,
                        status="confirmed",
                    )
                )
                imported += 1
        session.commit()

    return {
        "imported": imported,
        "duplicates": duplicates,
        "skipped": skipped,
        "unmatched": unmatched,
        "unmatched_names": sorted(unmatched_names),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Import biomarker history from a long-format CSV.")
    ap.add_argument("csv_path")
    ap.add_argument("--source-name", default="CSV import")
    args = ap.parse_args()

    result = import_csv(args.csv_path, args.source_name)
    print(f"Imported : {result['imported']}")
    print(f"Duplicates skipped: {result['duplicates']}")
    print(f"Rows skipped (bad/empty): {result['skipped']}")
    print(f"Unmatched biomarkers: {result['unmatched']}")
    if result["unmatched_names"]:
        print("  names not in catalog:", ", ".join(result["unmatched_names"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
