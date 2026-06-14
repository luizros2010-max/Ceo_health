"""Run the full extraction pipeline on a lab PDF (or a folder of PDFs) from the CLI.

This is the fastest way to iterate extraction quality against your real reports
without the web UI. It runs: intake -> dedup -> text extract -> Claude structured
extraction -> normalize -> validate -> persist (to the review queue / timeline).

Requirements:
- ANTHROPIC_API_KEY set in your .env (copy .env.example -> .env). Without it, the
  PDF is stored and its text captured, but extraction is skipped.

Usage:
    python extract_cli.py path/to/report.pdf
    python extract_cli.py path/to/folder/          # all *.pdf in the folder
    python extract_cli.py path/to/folder/ --quiet  # summary lines only

After importing, open the dashboard (or the Review page) to confirm rows.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sqlmodel import Session

from app.config import settings
from app.db import engine, init_db
from app.ingest.pipeline import ingest_document


def run_one(path: Path, quiet: bool) -> None:
    data = path.read_bytes()
    with Session(engine) as session:
        summary = ingest_document(
            session,
            data=data,
            mime_type="application/pdf",
            original_name=path.name,
        )
        session.commit()
        doc_id = summary.document_id

    flag = "DUP" if summary.is_duplicate else summary.status.upper()
    print(f"[{flag}] {path.name}: {summary.message}")
    if quiet:
        return

    # Show the parsed rows for eyeballing accuracy.
    from app.models import Biomarker, Observation
    from sqlmodel import select

    with Session(engine) as session:
        rows = session.exec(
            select(Observation).where(Observation.source_document_id == doc_id)
        ).all()
        if not rows:
            return
        print(f"    {'raw name':28} {'raw value':14} {'normalized':18} conf  status")
        for o in rows:
            bm = session.get(Biomarker, o.biomarker_id) if o.biomarker_id else None
            norm = f"{o.value_num} {o.canonical_unit}" if o.value_num is not None else "—"
            label = bm.slug if bm else "(unmapped)"
            print(
                f"    {o.raw_name[:27]:28} {str(o.raw_value or '')[:13]:14} "
                f"{(label + ' ' + norm)[:18]:18} {o.mapping_confidence:.2f}  {o.status}"
            )
        print()


def main() -> int:
    ap = argparse.ArgumentParser(description="Extract a lab PDF through the pipeline.")
    ap.add_argument("path", help="a PDF file or a folder of PDFs")
    ap.add_argument("--quiet", action="store_true", help="summary lines only")
    args = ap.parse_args()

    init_db()
    if not settings.has_api_key:
        print("WARNING: ANTHROPIC_API_KEY is not set — PDFs will be stored but not "
              "extracted. Set it in .env to enable extraction.\n")

    target = Path(args.path)
    if target.is_dir():
        pdfs = sorted(target.glob("*.pdf"))
        if not pdfs:
            print(f"No PDFs found in {target}")
            return 1
        for p in pdfs:
            run_one(p, args.quiet)
    elif target.is_file():
        run_one(target, args.quiet)
    else:
        print(f"Not found: {target}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
