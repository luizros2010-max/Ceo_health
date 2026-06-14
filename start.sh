#!/bin/bash
# One-command launcher (macOS / Linux): sets up if needed, builds the frontend,
# then serves the whole app from a single local server at http://127.0.0.1:8000.
#
#   ./start.sh            # build (first run) + serve
#   ./start.sh --build    # force a fresh frontend rebuild
#   ./start.sh --dev      # run backend + Vite dev server (hot reload, two ports)
set -euo pipefail
cd "$(dirname "$0")"

PORT=8000
open_browser() {
  url="$1"
  if command -v open >/dev/null 2>&1; then open "$url"
  elif command -v xdg-open >/dev/null 2>&1; then xdg-open "$url"
  fi
}

# --- Python backend deps ---
if [ ! -d .venv ]; then
  echo "Creating Python virtualenv and installing deps..."
  python3 -m venv .venv
  ./.venv/bin/pip install --quiet --upgrade pip
  ./.venv/bin/pip install --quiet -r requirements.txt
fi
# shellcheck disable=SC1091
source .venv/bin/activate

# --- Dev mode: backend + Vite with hot reload ---
if [ "${1:-}" = "--dev" ]; then
  echo "Starting backend (:8000) and Vite dev server (:5173)..."
  ( cd backend && uvicorn app.main:app --host 127.0.0.1 --port "$PORT" ) &
  BACK=$!
  ( cd frontend && [ -d node_modules ] || npm install; npm run dev ) &
  FRONT=$!
  trap 'kill $BACK $FRONT 2>/dev/null' INT TERM
  sleep 2; open_browser "http://localhost:5173"
  wait
  exit 0
fi

# --- Default: build frontend once, serve everything from FastAPI ---
if [ "${1:-}" = "--build" ] || [ ! -d frontend/dist ]; then
  echo "Building frontend..."
  ( cd frontend && { [ -d node_modules ] || npm install; } && npm run build )
fi

echo "Serving at http://127.0.0.1:$PORT  (Ctrl+C to stop)"
( sleep 2; open_browser "http://127.0.0.1:$PORT" ) &
cd backend
exec uvicorn app.main:app --host 127.0.0.1 --port "$PORT"
