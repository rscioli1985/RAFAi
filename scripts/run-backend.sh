#!/usr/bin/env bash

# Run the FastAPI backend with optional --debug hot reload.

set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_IMPORT_PATH="services.backend.app:app"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/.env}"
DEBUG=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --debug)
      DEBUG=1
      shift
      ;;
    *)
      echo "Unknown argument: $1" >&2
      echo "Usage: $0 [--debug]" >&2
      exit 1
      ;;
  esac
done

UVICORN_BIN="${UVICORN_BIN:-}"
if [[ -z "$UVICORN_BIN" ]]; then
  if [[ -x "$ROOT_DIR/.venv/bin/uvicorn" ]]; then
    UVICORN_BIN="$ROOT_DIR/.venv/bin/uvicorn"
  else
    UVICORN_BIN="$(command -v uvicorn || true)"
  fi
fi

if [[ -z "$UVICORN_BIN" ]]; then
  echo "uvicorn not found. Activate your virtualenv or install requirements first." >&2
  exit 1
fi

ARGS=(
  "$APP_IMPORT_PATH"
  "--host" "$HOST"
  "--port" "$PORT"
)

takes_env_file=0
if [[ -f "$ENV_FILE" ]]; then
  ARGS+=("--env-file" "$ENV_FILE")
  takes_env_file=1
fi

# Ensure DATABASE_URL aligns with .env if uvicorn doesn't auto-load it.
if [[ "$takes_env_file" -eq 0 ]]; then
  export DATABASE_URL="${DATABASE_URL:-postgresql+psycopg://app:app@localhost:5432/nilrag}"
fi

if [[ "$DEBUG" -eq 1 ]]; then
  ARGS+=("--reload" "--reload-delay" "0.5")
fi

cd "$ROOT_DIR"
echo "[run-backend] Launching uvicorn (${UVICORN_BIN})"
exec "$UVICORN_BIN" "${ARGS[@]}"
