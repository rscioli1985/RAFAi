#!/usr/bin/env bash

# Start the local Postgres service defined in infra/docker-compose.yml.
# Optionally waits for the container to report ready via pg_isready.

set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INFRA_DIR="$ROOT_DIR/infra"
SERVICE_NAME="${SERVICE_NAME:-postgres}"
CONTAINER_NAME="${CONTAINER_NAME:-nilrag-postgres}"
WAIT_FOR_READY=1
ATTEMPTS="${DB_WAIT_ATTEMPTS:-60}"
OS_NAME="$(uname -s)"

log() {
  echo "[run-database] $*"
}

usage() {
  cat <<EOF
Usage: $0 [--no-wait]

Starts the $SERVICE_NAME service from infra/docker-compose.yml.

Options:
  --no-wait   Do not wait for pg_isready to succeed.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-wait)
      WAIT_FOR_READY=0
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

ensure_docker_cli() {
  if command -v docker >/dev/null 2>&1; then
    return 0
  fi
  log "Docker CLI not found. Install Docker Desktop, Colima, or another Docker distribution."
  exit 1
}

start_docker_daemon_if_needed() {
  if docker info >/dev/null 2>&1; then
    return 0
  fi

  if [[ "$OS_NAME" == "Darwin" ]] && command -v open >/dev/null 2>&1; then
    log "Docker daemon not reachable; attempting to launch Docker Desktop..."
    open -ga Docker || true
    local retries=60
    while (( retries > 0 )); do
      if docker info >/dev/null 2>&1; then
        log "Docker daemon is now running."
        return 0
      fi
      sleep 2
      ((retries--))
    done
    log "Docker Desktop did not become ready; start it manually and rerun."
    exit 1
  fi

  log "Docker daemon is not running. Start your Docker engine and rerun this script."
  exit 1
}

ensure_docker_cli
start_docker_daemon_if_needed

if docker compose version >/dev/null 2>&1; then
  DOCKER_COMPOSE=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  DOCKER_COMPOSE=(docker-compose)
else
  log "docker compose is unavailable. Install a recent Docker or docker-compose binary."
  exit 1
fi

log "Starting $SERVICE_NAME via docker compose..."
(
  cd "$INFRA_DIR"
  "${DOCKER_COMPOSE[@]}" up -d "$SERVICE_NAME"
)

if [[ "$WAIT_FOR_READY" -eq 0 ]]; then
  log "Container started; skipping readiness wait."
  exit 0
fi

log "Waiting for database readiness (up to $ATTEMPTS seconds)..."

while (( ATTEMPTS > 0 )); do
  if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}\$"; then
    if docker exec "$CONTAINER_NAME" pg_isready -U app -d nilrag >/dev/null 2>&1; then
      log "Database is ready."
      exit 0
    fi
  fi
  sleep 1
  ((ATTEMPTS--))
done

log "Database did not become ready in time. Tail the container logs for details:"
log "  docker logs -f $CONTAINER_NAME"
exit 1
