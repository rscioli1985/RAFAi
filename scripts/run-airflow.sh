#!/usr/bin/env bash

# Build and run the Airflow container that executes our DAGs.

set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AIRFLOW_DIR="$ROOT_DIR/infra/airflow"
ACTION="up"
EXTRA_ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --down)
      ACTION="down"
      shift
      ;;
    *)
      EXTRA_ARGS+=("$1")
      shift
      ;;
  esac
done

log() {
  echo "[run-airflow] $*"
}

if [[ ! -f "$ROOT_DIR/.env" ]]; then
  log "Warning: .env not found at repo root; DAGs may lack database credentials."
fi

if ! command -v docker >/dev/null 2>&1; then
  log "Docker CLI not found. Install Docker Desktop or Colima before running Airflow."
  exit 1
fi

log "Using compose file at $AIRFLOW_DIR/docker-compose.yml"
if [[ "$ACTION" == "up" ]]; then
  log "Building and starting Airflow container..."
  (
    cd "$AIRFLOW_DIR"
    if [[ ${#EXTRA_ARGS[@]} -gt 0 ]]; then
      docker compose up -d --build "${EXTRA_ARGS[@]}"
    else
      docker compose up -d --build
    fi
  )
  log "Airflow web UI available at http://localhost:8080 (default creds set by airflow standalone)."
else
  log "Stopping Airflow container..."
  (
    cd "$AIRFLOW_DIR"
    if [[ ${#EXTRA_ARGS[@]} -gt 0 ]]; then
      docker compose down "${EXTRA_ARGS[@]}"
    else
      docker compose down
    fi
  )
fi
