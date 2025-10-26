#!/usr/bin/env bash

# Run the Airflow reconciliation worker to sync job statuses from DAG runs.

set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-$ROOT_DIR/.venv/bin/python}"

if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="$(command -v python3 || true)"
fi

if [[ -z "$PYTHON_BIN" ]]; then
  echo "[run-reconciler] python3 not found. Run scripts/setup/quickstart.sh first." >&2
  exit 1
fi

exec "$PYTHON_BIN" -m services.backend.orchestration.reconciler "$@"
