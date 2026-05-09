#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${EDICT_BACKEND_VENV:-$ROOT_DIR/.venv-edict-backend}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
REQ_FILE="$ROOT_DIR/edict/backend/requirements.txt"

if [[ ! -f "$REQ_FILE" ]]; then
  echo "[backend-setup] requirements file not found: $REQ_FILE" >&2
  exit 1
fi

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "[backend-setup] python not found: $PYTHON_BIN" >&2
  exit 1
fi

if [[ ! -d "$VENV_DIR" ]]; then
  echo "[backend-setup] creating venv: $VENV_DIR"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
else
  echo "[backend-setup] reusing venv: $VENV_DIR"
fi

"$VENV_DIR/bin/python" -m pip install --upgrade pip wheel setuptools
"$VENV_DIR/bin/python" -m pip install -r "$REQ_FILE"

cat <<EOF
[backend-setup] runtime ready
  root: $ROOT_DIR
  venv: $VENV_DIR
  python: $VENV_DIR/bin/python

Next:
  1. copy deploy/backend/backend.env.example to /etc/edict/backend.env and fill secrets
  2. run Alembic migration with that env loaded
  3. install deploy/systemd/*.service if you decide to productionize
EOF
