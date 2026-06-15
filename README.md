# CEO of Your Own Health

A **local-first** personal health-records aggregation system. Upload medical exams
spanning 20–30 years, aggregate them into one longitudinal track record, and visualize
biomarker trends over time — so you can be the CEO of your own health.

> **Privacy:** All data lives on your machine. The backend binds to `127.0.0.1` only.
> Slices are sent to the **Claude API** *only* when you explicitly upload a document for
> extraction (or, later, run analysis). Nothing auto-syncs to any cloud. Your
> `ANTHROPIC_API_KEY` stays server-side and never reaches the browser.

This repository contains the **Phase 1 foundation**: data model + ingest real exams +
biomarker timelines.

---

## Architecture

| Layer | Tech |
|---|---|
| API / backend | FastAPI + uvicorn (127.0.0.1) |
| Pipeline | Python 3.11+ |
| DB | SQLite (WAL) via SQLModel |
| PDF text | PyMuPDF (`fitz`) |
| LLM extraction | `anthropic` SDK, Claude tool-use (forced JSON) |
| Fuzzy matching | rapidfuzz |
| Frontend | React + Vite + TypeScript |
| Charts | Recharts |

**Core data idea:** store *what the lab literally reported* (`raw_*`, immutable audit
trail) separately from *the canonical biomarker it maps to* (normalized, queryable across
decades). Normalization is a derived layer that can be recomputed without re-uploading.

The ingestion pipeline is:
`intake → dedup (sha256) → type detect → text extract → Claude structured extraction →
normalize (alias + unit conversion) → validate (value-in-source, plausibility, dates) →
review (you confirm) → commit to timeline`.

Nothing enters the longitudinal record until you **confirm** it.

---

## Quick start

### One command (recommended)

After cloning, just run the launcher — it creates the virtualenv, installs
deps, builds the frontend, and serves the whole app from a single local URL:

```bash
./start.sh            # macOS / Linux  →  http://127.0.0.1:8000
start.bat             # Windows
./start.sh --dev      # backend + Vite hot-reload (two ports) for development
```

To load your data first, drop your CSV/JSON files into `data/imports/` and run
`./load_data.sh`. The manual steps below are equivalent.

**Accounts:** the app requires a login (multi-patient). On first open, **create a
profile** — the first profile claims any data already loaded; additional family
members get their own isolated profiles. For **family/self-host access over a private
network, see [DEPLOY.md](DEPLOY.md)** (Tailscale). For single-user local-only, set
`REQUIRE_AUTH=false` in `.env`.

### 1. Backend

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Optional: enable AI extraction of uploaded PDFs.
cp .env.example .env        # then put your key in ANTHROPIC_API_KEY=...

cd backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

On first boot, the DB is created at `data/ceo_health.db` and the biomarker catalog
(~30 analytes with English + Portuguese aliases and analyte-specific unit conversions)
is seeded. `GET http://127.0.0.1:8000/api/health` returns `{"status":"ok"}`.

Without an `ANTHROPIC_API_KEY`, uploaded PDFs are stored and their text captured, but
automatic extraction is skipped — you can still use **manual entry** to build timelines.

### 2. Frontend (dev)

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173  (proxies /api → :8000)
```

### 3. Frontend (local-prod, single process)

```bash
cd frontend && npm run build      # emits frontend/dist
# then just run uvicorn — FastAPI serves the built bundle at http://127.0.0.1:8000
```

---

## Loading your data

Two ways to get real history in, besides the web Upload page:

**1. Structured CSV (no API key needed)** — for values you already have tidy
(e.g. exported from a tracking spreadsheet). One measurement per row:

```csv
biomarker,date,value,unit
Glucose,2019-10-01,91,mg/dl
LDL cholesterol,2018-05-01,132,mg/dl
```

```bash
cd backend
python import_csv.py ../data/imports/your_data.csv --source-name "My Spreadsheet"
```

`biomarker` may be a catalog slug or any English/Portuguese name (matched, with
fuzzy fallback); `unit` is optional and values are converted to each biomarker's
canonical unit. Imported rows are written as **confirmed** so they chart
immediately. Keep your CSV under `data/` (gitignored) — never commit health data.

**Bulk load (one command):** drop all your CSV files and `narrative_reports.json`
into `data/imports/`, then from the repo root run `./load_data.sh` — it imports
every CSV plus the reports JSON in one go (re-running is safe; duplicates are skipped).

**3. Wearables (Connectors page)** — Oura Ring (API) and Apple Health (file import):
- **Oura:** create a Personal Access Token at cloud.ouraring.com, set `OURA_TOKEN`
  in `.env` (or paste it on the Connectors page), then *Sync* — pulls resting HR,
  HRV, sleep, SpO₂, steps. Apple has no cloud API, so export from the iPhone Health
  app (*Export All Health Data* → `export.zip`) and import it on the Connectors page,
  or via `python backend/import_apple_health.py path/to/export.zip` for large files.

**2. Lab PDFs via the extraction pipeline (needs an API key)**:

```bash
cd backend
python extract_cli.py path/to/report.pdf        # one file
python extract_cli.py path/to/folder/           # all PDFs in a folder
```

This runs intake → dedup → text extract → Claude extraction → normalize →
validate, then drops rows into the Review queue to confirm. Without
`ANTHROPIC_API_KEY` it stores the PDF + text but skips extraction.

## Tests

```bash
source .venv/bin/activate
cd backend
pytest -q
```

Covers analyte-specific unit conversions against known reference values
(e.g. glucose 5.49 mmol/L → 98.9 mg/dL), the value-in-source / future-date validators,
alias matching (EN + PT + fuzzy), and sha256 dedup.

---

## API surface (all under `/api`)

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | liveness |
| POST | `/documents` | multipart upload → store, extract, normalize, validate |
| GET | `/documents` | list (+ status, observation counts) |
| GET | `/documents/:id` | doc + observations |
| GET | `/documents/:id/file` | stream original (for side-by-side review) |
| PATCH | `/documents/:id` | edit lab name / collection date |
| DELETE | `/documents/:id` | remove doc + its observations |
| GET | `/observations` | `?biomarker= &from= &to= &status=` |
| POST | `/observations` | manual entry (confirmed immediately) |
| PATCH | `/observations/:id` | confirm / re-map (learns alias) / reject |
| GET | `/observations/review` | the needs-review queue |
| GET | `/biomarkers` | catalog (+ whether you have data) |
| GET | `/biomarkers/:slug/timeline` | points in canonical unit + reference band |
| GET | `/overview` | latest value per biomarker, in/out-of-range, stats |
| GET | `/patient`, PATCH `/patient` | profile (age/sex) for analysis context |
| GET | `/analysis/status` | whether a key is configured (never returns the key) |
| GET | `/analysis/score` | health score vs age-peers (transparent, deterministic) |
| GET | `/analysis/plan` | action-plan targets + workout/nutrition levers |
| POST | `/analysis/preview` | exact minimal slice + trend flags that would be shared |
| POST | `/analysis/run`, `/analysis/stream` | AI summary on the slice (key required) |
| POST | `/analysis/plan/stream` | AI-drafted plan (key required) |
| GET | `/connectors/status` | wearable connector availability |
| POST | `/connectors/oura/sync` | pull Oura daily data (token) |
| POST | `/connectors/apple-health` | import an Apple Health export (zip/xml) |
| GET | `/reports`, POST/DELETE | imaging / narrative reports |

---

## Dashboard pages

- **Overview** — biomarker cards + a vitals quick-entry (BP / BMI auto-calc / waist / weight).
- **Upload** — drag-drop PDFs/scans + manual-entry form.
- **Documents** — every source document; detail shows the **original file side-by-side with parsed observations**.
- **Connectors** — Oura Ring (API token sync) and Apple Health (export import).
- **Biomarker Timeline** — reference-band line chart with a **source filter** and **per-source overlay**.
- **Health Score** — overall gauge + domain breakdown vs age-peers, with explicit scoring anchors.
- **Action Plan** — score-gap targets + workout/nutrition/lifestyle levers + optional AI draft.
- **AI Insights** — deterministic trend flags + streaming, minimal-slice AI summary.
- **Imaging & Reports** — narrative reports (MRI, echo, endoscopy…) beside the timelines.
- **Doctor Report** — printable / Save-as-PDF: score, plan targets, flags, all biomarkers, imaging.
- **Review** — low-confidence / unmapped rows; confirm, re-map (teaches the catalog), or reject.

---

## Roadmap

- **Phase 1 — done:** foundation — schema, seed catalog, text-PDF extraction → review/commit, timelines.
- **Phase 2 — done:** richer catalog (EN/PT/ES aliases), unit conversions, multi-source robustness.
- **Phase 3 — partial:** structured CSV import + wearables (Oura API, Apple Health export). Scanned-PDF OCR still pending.
- **Phase 4 — done:** AI insights (minimal-slice, streaming), Health Score, Action Plan, Doctor Report.

---

## Privacy notes

- The server binds to `127.0.0.1`. `data/` and `.env` are gitignored.
- The Claude key is read only by the backend (pydantic-settings). It is never sent to the
  frontend; `/api/analysis/status` exposes only a boolean.
- Original files are content-addressed (`data/documents/<sha256>.<ext>`) and never mutated.
