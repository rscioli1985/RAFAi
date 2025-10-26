#!/usr/bin/env bash

# Initialize the local database (containers + migrations) and seed default data.
# Creates/updates the admin@goanalog.com user and ensures Go Analog org exists.

set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SETUP_DIR="$ROOT_DIR/scripts/setup"
DB_INIT_SCRIPT="$SETUP_DIR/db-init.sh"
SEED_DIR="$ROOT_DIR/scripts/bootstrapping/py"

ADMIN_EMAIL="${ADMIN_EMAIL:-admin@goanalog.com}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-password}"
ADMIN_FULL_NAME="${ADMIN_FULL_NAME:-Go Analog Admin}"
ADMIN_DISPLAY_NAME="${ADMIN_DISPLAY_NAME:-Go Analog Admin}"

ORG_SLUG="${ORG_SLUG:-goanalog}"
ORG_NAME="${ORG_NAME:-Go Analog}"
ORG_DESCRIPTION="${ORG_DESCRIPTION:-Primary organization seed for local development.}"

log() {
  echo "[run-seeds] $*"
}

ensure_python() {
  if [[ -n "${PYTHON_BIN:-}" && -x "$PYTHON_BIN" ]]; then
    return 0
  fi

  local candidates=(
    "$ROOT_DIR/.venv/bin/python"
    python3
    python
  )

  for candidate in "${candidates[@]}"; do
    if command -v "$candidate" >/dev/null 2>&1; then
      PYTHON_BIN="$(command -v "$candidate")"
      return 0
    fi
  done

  log "Python interpreter not found. Run scripts/setup/quickstart.sh first or set PYTHON_BIN."
  exit 1
}

ensure_python

log "Initializing database (containers + migrations)..."
bash "$DB_INIT_SCRIPT"

log "Seeding user $ADMIN_EMAIL"
"$PYTHON_BIN" "$SEED_DIR/seed_user.py" \
  --email "$ADMIN_EMAIL" \
  --password "$ADMIN_PASSWORD" \
  --full-name "$ADMIN_FULL_NAME" \
  --display-name "$ADMIN_DISPLAY_NAME"

log "Seeding organization $ORG_SLUG"
"$PYTHON_BIN" "$SEED_DIR/seed_org.py" \
  --slug "$ORG_SLUG" \
  --name "$ORG_NAME" \
  --owner-email "$ADMIN_EMAIL" \
  --description "$ORG_DESCRIPTION"

log "Seeding complete."
