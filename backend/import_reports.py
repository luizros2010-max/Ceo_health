"""Import imaging / narrative reports from a JSON file.

JSON format: a list of objects, e.g.

    [
      {
        "title": "Lumbar spine MRI",
        "category": "MRI",
        "report_date": "2026-01-15",
        "facility": "Hospital Britanico",
        "body": "Full findings text...",
        "impression": "Optional short conclusion"
      }
    ]

Usage:
    python import_reports.py path/to/reports.json

Dedup: a report with the same title + report_date is skipped. Privacy: writes
only to your local SQLite DB; keep the JSON under data/ (gitignored).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime

from sqlmodel import Session, select

from app.db import engine, init_db
from app.models import NarrativeReport, Patient


def parse_date(value):
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y"):
        try:
            return datetime.strptime(str(value).strip()[:10], fmt).date()
        except ValueError:
            continue
    return None


def import_reports(path: str) -> dict:
    init_db()
    with open(path, encoding="utf-8") as fh:
        items = json.load(fh)

    imported = duplicates = skipped = 0
    with Session(engine) as session:
        patient = session.exec(select(Patient)).first()
        for item in items:
            title = (item.get("title") or "").strip()
            if not title:
                skipped += 1
                continue
            report_date = parse_date(item.get("report_date"))

            exists = session.exec(
                select(NarrativeReport).where(
                    NarrativeReport.title == title,
                    NarrativeReport.report_date == report_date,
                )
            ).first()
            if exists:
                duplicates += 1
                continue

            session.add(
                NarrativeReport(
                    patient_id=patient.id if patient else None,
                    title=title,
                    category=(item.get("category") or None),
                    report_date=report_date,
                    facility=(item.get("facility") or None),
                    body=item.get("body") or "",
                    impression=(item.get("impression") or None),
                )
            )
            imported += 1
        session.commit()

    return {"imported": imported, "duplicates": duplicates, "skipped": skipped}


def main() -> int:
    ap = argparse.ArgumentParser(description="Import narrative/imaging reports from JSON.")
    ap.add_argument("json_path")
    args = ap.parse_args()
    result = import_reports(args.json_path)
    print(f"Imported : {result['imported']}")
    print(f"Duplicates skipped: {result['duplicates']}")
    print(f"Rows skipped (no title): {result['skipped']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
