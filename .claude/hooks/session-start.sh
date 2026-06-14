#!/bin/bash
# SessionStart hook: install backend (Python) and frontend (Node) dependencies so
# tests, type-checks, and the dev servers work in Claude Code on the web sessions.
set -euo pipefail

# Only needed in the remote (web) environment.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-.}"

# --- Backend: Python venv + deps ---
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
./.venv/bin/pip install --quiet --upgrade pip
./.venv/bin/pip install --quiet -r requirements.txt

# Make the venv the default Python/pytest for the session.
if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  echo "export PATH=\"${CLAUDE_PROJECT_DIR:-$PWD}/.venv/bin:\$PATH\"" >> "$CLAUDE_ENV_FILE"
  echo "export VIRTUAL_ENV=\"${CLAUDE_PROJECT_DIR:-$PWD}/.venv\"" >> "$CLAUDE_ENV_FILE"
fi

# --- Frontend: Node deps ---
if [ -d frontend ]; then
  (cd frontend && npm install --no-audit --no-fund)
fi

echo "session-start hook: dependencies installed."
