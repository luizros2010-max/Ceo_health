#!/bin/bash
# One-step loader for the data bundle I sent you.
# 1) Download ceo_health_data.zip (keep it in your Downloads folder).
# 2) From the Ceo_health folder, run:  ./import_bundle.sh
# It unpacks the CSV/JSON files into data/imports/ and loads them.
set -euo pipefail
cd "$(dirname "$0")"

ZIP="${1:-$HOME/Downloads/ceo_health_data.zip}"
if [ ! -f "$ZIP" ]; then
  echo "Couldn't find the bundle. Put ceo_health_data.zip in your Downloads folder,"
  echo "or run: ./import_bundle.sh /path/to/ceo_health_data.zip"
  exit 1
fi

mkdir -p data/imports
unzip -o -j "$ZIP" -d data/imports >/dev/null
echo "Unpacked bundle into data/imports:"
ls -1 data/imports
./load_data.sh
