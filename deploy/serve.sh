#!/bin/bash
# Production serve for self-hosting: builds the frontend (if needed) and serves the
# whole app on all interfaces so devices on your Tailscale network can reach it.
# Used by the systemd service. Override host/port with HOST / PORT env vars.
set -euo pipefail
cd "$(dirname "$0")/.."

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"

if [ ! -d .venv ]; then
  python3 -m venv .venv
  ./.venv/bin/pip install --quiet --upgrade pip
  ./.venv/bin/pip install --quiet -r requirements.txt
fi
# shellcheck disable=SC1091
source .venv/bin/activate

if [ ! -d frontend/dist ] || [ "${REBUILD:-}" = "1" ]; then
  (cd frontend && { [ -d node_modules ] || npm install; } && npm run build)
fi

exec uvicorn --app-dir backend app.main:app --host "$HOST" --port "$PORT"
