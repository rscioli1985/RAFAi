#!/usr/bin/env bash

# Build and run the local Prometheus monitoring stack.

set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MONITORING_DIR="$ROOT_DIR/infra/monitoring"
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
  echo "[run-prometheus] $*"
}

if ! command -v docker >/dev/null 2>&1; then
  log "Docker CLI not found. Install Docker Desktop or Colima before running Prometheus."
  exit 1
fi

COMPOSE_FILE="$MONITORING_DIR/docker-compose.yml"
if [[ ! -f "$COMPOSE_FILE" ]]; then
  log "Compose file not found at $COMPOSE_FILE"
  exit 1
fi

cd "$MONITORING_DIR"

if [[ "$ACTION" == "up" ]]; then
  log "Starting Prometheus stack..."
  if [[ ${#EXTRA_ARGS[@]} -gt 0 ]]; then
    docker compose up -d --build "${EXTRA_ARGS[@]}"
  else
    docker compose up -d --build
  fi
  log "Prometheus available at http://localhost:9090"
else
  log "Stopping Prometheus stack..."
  if [[ ${#EXTRA_ARGS[@]} -gt 0 ]]; then
    docker compose down "${EXTRA_ARGS[@]}"
  else
    docker compose down
  fi
fi
