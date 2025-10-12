#!/usr/bin/env bash
set -euo pipefail

# Launch the React frontend (Vite dev server) with sensible defaults.
# - Installs dependencies on first run if node_modules is missing
# - Proxies to backend at VITE_BACKEND_URL (default: http://localhost:8000)
# - Opens browser at http://localhost:$PORT

PROJ_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="$PROJ_ROOT/frontend"

if [[ ! -d "$FRONTEND_DIR" ]]; then
  echo "[run-frontend] frontend/ not found at $FRONTEND_DIR" >&2
  echo "Ensure the frontend has been scaffolded." >&2
  exit 1
fi

if ! command -v node >/dev/null 2>&1; then
  echo "[run-frontend] Node.js is required. Install with Homebrew: brew install node@20" >&2
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "[run-frontend] npm is required. It usually ships with Node.js." >&2
  exit 1
fi

cd "$FRONTEND_DIR"

if [[ ! -d node_modules ]]; then
  echo "[run-frontend] Installing frontend dependencies..."
  if [[ -f package-lock.json ]]; then
    npm ci
  else
    npm install
  fi
fi

# Defaults (can be overridden via env)
export VITE_BACKEND_URL="${VITE_BACKEND_URL:-http://localhost:8000}"
export VITE_API_BASE="${VITE_API_BASE:-/api}"
PORT="${PORT:-5173}"

echo "[run-frontend] Starting Vite dev server on http://localhost:${PORT}"
echo "[run-frontend] Proxying API to: ${VITE_BACKEND_URL} (base: ${VITE_API_BASE})"

# Open browser shortly after start (macOS). Ignore errors if unavailable.
if command -v open >/dev/null 2>&1; then
  (sleep 2 && open "http://localhost:${PORT}") &
fi

exec npm run dev -- --port "${PORT}" --strictPort

