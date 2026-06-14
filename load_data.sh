#!/bin/bash
# Convenience loader: imports every CSV in data/imports/ as confirmed observations,
# and narrative_reports.json (if present) as imaging/narrative reports.
#
# Put the files I sent you into data/imports/ first, then run:  ./load_data.sh
set -euo pipefail
cd "$(dirname "$0")"

# Activate venv if present (created during setup; see README).
if [ -f .venv/bin/activate ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

IMPORTS="data/imports"
if [ ! -d "$IMPORTS" ]; then
  echo "No $IMPORTS directory. Create it and drop your CSV/JSON files there."
  exit 1
fi

cd backend

shopt -s nullglob
for csv in ../"$IMPORTS"/*.csv; do
  name="$(basename "$csv" .csv)"
  echo "== importing $name =="
  python import_csv.py "$csv" --source-name "$name"
done

if [ -f ../"$IMPORTS"/narrative_reports.json ]; then
  echo "== importing narrative reports =="
  python import_reports.py ../"$IMPORTS"/narrative_reports.json
fi

echo "Done. Start the app and open the dashboard."
