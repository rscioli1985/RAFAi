#!/usr/bin/env bash

# Quickstart script for setting up Python environment and dependencies.
# Ensures Python 3.12 is available (installs Homebrew + python@3.12 if needed).

set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OS_NAME="$(uname -s)"
BREW_CMD="${BREW_BIN:-}"
VENV_DIR="${VENV_DIR:-$ROOT_DIR/.venv}"

log() {
  echo "[quickstart] $*"
}

detect_brew_binary() {
  if [[ -n "$BREW_CMD" && -x "$BREW_CMD" ]]; then
    return 0
  fi

  local candidates=(
    "$BREW_CMD"
    /opt/homebrew/bin/brew
    /usr/local/bin/brew
  )

  for candidate in "${candidates[@]}"; do
    if [[ -n "$candidate" && -x "$candidate" ]]; then
      BREW_CMD="$candidate"
      return 0
    fi
  done

  if command -v brew >/dev/null 2>&1; then
    BREW_CMD="$(command -v brew)"
    return 0
  fi

  return 1
}

apply_brew_shellenv() {
  if [[ -n "$BREW_CMD" ]]; then
    eval "$("$BREW_CMD" shellenv)" >/dev/null 2>&1 || true
  elif [[ -x /opt/homebrew/bin/brew ]]; then
    eval "$(/opt/homebrew/bin/brew shellenv)" >/dev/null 2>&1 || true
  elif [[ -x /usr/local/bin/brew ]]; then
    eval "$(/usr/local/bin/brew shellenv)" >/dev/null 2>&1 || true
  fi
}

ensure_homebrew() {
  if detect_brew_binary; then
    apply_brew_shellenv
    return 0
  fi

  if [[ "$OS_NAME" != "Darwin" ]]; then
    echo "Homebrew is required to auto-install Python 3.12. Install Python manually or set PYTHON_BIN." >&2
    exit 1
  fi

  log "Homebrew not found; installing from official script..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  apply_brew_shellenv

  if ! detect_brew_binary; then
    echo "Homebrew installation finished but 'brew' is still unavailable. Ensure your shell PATH includes it and rerun." >&2
    exit 1
  fi

  apply_brew_shellenv
}

install_python312() {
  ensure_homebrew

  log "Installing python@3.12 via Homebrew (this may take a moment)..."
  "$BREW_CMD" install python@3.12

  local prefix
  prefix="$("$BREW_CMD" --prefix python@3.12 2>/dev/null || true)"
  if [[ -z "$prefix" ]]; then
    prefix="$("$BREW_CMD" --prefix)/opt/python@3.12"
  fi

  PYTHON_BIN="$prefix/bin/python3.12"

  if [[ ! -x "$PYTHON_BIN" ]]; then
    echo "python@3.12 was installed but the executable was not found at $PYTHON_BIN." >&2
    echo "Check your Homebrew installation or set PYTHON_BIN manually." >&2
    exit 1
  fi

  log "Using Python binary: $PYTHON_BIN"
}

ensure_python_binary() {
  if [[ -n "${PYTHON_BIN:-}" ]]; then
    if command -v "$PYTHON_BIN" >/dev/null 2>&1; then
      return 0
    else
      echo "Specified PYTHON_BIN ($PYTHON_BIN) not found on PATH." >&2
      exit 1
    fi
  fi

  if command -v python3.12 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3.12)"
    return 0
  fi

  install_python312
}

ensure_python_binary

if [[ ! -d "$VENV_DIR" ]]; then
  log "Creating virtual environment at $VENV_DIR"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
else
  log "Using existing virtual environment at $VENV_DIR"
fi

log "Activating virtual environment"
# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate"

log "Upgrading pip/setuptools/wheel"
pip install --upgrade pip setuptools wheel

log "Installing Python requirements"
pip install -r "$ROOT_DIR/requirements.txt"

log "Environment ready. Activate later with: source \"$VENV_DIR/bin/activate\""
