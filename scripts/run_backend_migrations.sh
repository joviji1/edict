#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${EDICT_BACKEND_ENV_FILE:-/etc/edict/backend.env}"
VENV_DIR="${EDICT_BACKEND_VENV:-$ROOT_DIR/.venv-edict-backend}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "[backend-migrate] env file not found: $ENV_FILE" >&2
  exit 1
fi

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  echo "[backend-migrate] missing venv python: $VENV_DIR/bin/python" >&2
  exit 1
fi

cd "$ROOT_DIR/edict"
set -a
source "$ENV_FILE"
set +a
exec "$VENV_DIR/bin/python" -m alembic -c alembic.ini upgrade head
