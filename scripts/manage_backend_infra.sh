#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${EDICT_BACKEND_ENV_FILE:-/etc/edict/backend.env}"
COMPOSE_FILE="$ROOT_DIR/deploy/backend/docker-compose.infra.yml"
ACTION="${1:-up}"

if [[ ! -f "$COMPOSE_FILE" ]]; then
  echo "[backend-infra] compose file not found: $COMPOSE_FILE" >&2
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "[backend-infra] env file not found: $ENV_FILE" >&2
  exit 1
fi

case "$ACTION" in
  up)
    exec docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d
    ;;
  down)
    exec docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" down
    ;;
  ps)
    exec docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps
    ;;
  logs)
    exec docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" logs --tail=200
    ;;
  *)
    echo "usage: $0 {up|down|ps|logs}" >&2
    exit 1
    ;;
esac
