#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_DIR="$ROOT_DIR/edict/backend"
VENV_DIR="${EDICT_BACKEND_VENV:-$ROOT_DIR/.venv-edict-backend}"
COMPONENT="${1:-}"
HOST="${BACKEND_HOST:-127.0.0.1}"
PORT="${PORT:-${BACKEND_PORT:-18000}}"

export BACKEND_HOST="$HOST"
export BACKEND_PORT="$PORT"
export PORT="$PORT"
export OPENCLAW_PROJECT_DIR="${OPENCLAW_PROJECT_DIR:-$ROOT_DIR}"
export EDICT_HOME="${EDICT_HOME:-$ROOT_DIR}"
export PYTHONUNBUFFERED=1

if [[ -z "$COMPONENT" ]]; then
  echo "usage: $0 {api|outbox-relay|orchestrator|dispatch}" >&2
  exit 1
fi

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  echo "[backend-runner] missing venv python: $VENV_DIR/bin/python" >&2
  echo "[backend-runner] run scripts/setup_backend_runtime.sh first" >&2
  exit 1
fi

cd "$APP_DIR"

case "$COMPONENT" in
  api)
    exec "$VENV_DIR/bin/python" -m uvicorn app.main:app --host "$HOST" --port "$PORT"
    ;;
  outbox-relay)
    exec "$VENV_DIR/bin/python" -m app.workers.outbox_relay
    ;;
  orchestrator)
    exec "$VENV_DIR/bin/python" -m app.workers.orchestrator_worker
    ;;
  dispatch)
    exec "$VENV_DIR/bin/python" -m app.workers.dispatch_worker
    ;;
  *)
    echo "unknown component: $COMPONENT" >&2
    exit 1
    ;;
esac
