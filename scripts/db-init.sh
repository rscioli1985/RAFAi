#!/usr/bin/env bash
set -euo pipefail

# Initialize local Postgres (docker-compose) and run Alembic migrations.
# - Starts container if not running
# - Waits for readiness
# - Runs `alembic upgrade head`

PROJ_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INFRA_DIR="$PROJ_ROOT/infra"
SERVICE_NAME="postgres"
CONTAINER_NAME="nilrag-postgres"

if ! command -v docker >/dev/null 2>&1; then
  echo "[db-init] Docker is required. Install Docker Desktop or Colima." >&2
  exit 1
fi

echo "[db-init] Starting Postgres via docker compose..."
cd "$INFRA_DIR"
docker compose up -d "$SERVICE_NAME"

echo "[db-init] Waiting for database readiness..."
ATTEMPTS=60
until docker exec "$CONTAINER_NAME" pg_isready -U app -d nilrag >/dev/null 2>&1; do
  ((ATTEMPTS--)) || {
    echo "[db-init] Database did not become ready in time." >&2
    docker compose logs "$SERVICE_NAME" | tail -n 50 || true
    exit 1
  }
  sleep 1
done

echo "[db-init] Database ready. Running migrations..."
cd "$PROJ_ROOT"

ALEMBIC_BIN="alembic"
if [[ -x "$PROJ_ROOT/venv/bin/alembic" ]]; then
  ALEMBIC_BIN="$PROJ_ROOT/venv/bin/alembic"
fi

DATABASE_URL_DEFAULT="postgresql+psycopg://app:app@localhost:5432/nilrag"
export DATABASE_URL="${DATABASE_URL:-$DATABASE_URL_DEFAULT}"

"$ALEMBIC_BIN" upgrade head

echo "[db-init] Done. Postgres running and schema migrated."

