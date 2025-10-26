#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SECRETS_DIR="${SECRETS_DIR:-$ROOT_DIR/.secrets}"
REDDIT_FILE="${REDDIT_SECRETS_FILE:-$SECRETS_DIR/reddit.yaml}"
LLM_FILE="${LLM_SECRETS_FILE:-$SECRETS_DIR/llm.yaml}"
TEMPLATE_DIR="$ROOT_DIR/infra/secrets/templates"

log() {
  echo "[render-secrets] $*"
}

mkdir -p "$SECRETS_DIR"

if [[ ! -f "$REDDIT_FILE" ]]; then
  cp "$TEMPLATE_DIR/reddit.yaml" "$REDDIT_FILE"
  log "Created $REDDIT_FILE from template"
else
  log "$REDDIT_FILE already exists; skipping"
fi

if [[ ! -f "$LLM_FILE" ]]; then
  cp "$TEMPLATE_DIR/llm.yaml" "$LLM_FILE"
  log "Created $LLM_FILE from template"
else
  log "$LLM_FILE already exists; skipping"
fi

log "Update the generated files with real secrets."
