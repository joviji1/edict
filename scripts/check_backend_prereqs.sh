#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${EDICT_BACKEND_VENV:-$ROOT_DIR/.venv-edict-backend}"
ENV_FILE="${EDICT_BACKEND_ENV_FILE:-/etc/edict/backend.env}"
BLOCKERS=0
WARNS=0

say() { printf '%s\n' "$*"; }
warn() { printf '[warn] %s\n' "$*"; WARNS=$((WARNS+1)); }
block() { printf '[blocker] %s\n' "$*"; BLOCKERS=$((BLOCKERS+1)); }
port_status() {
  local port="$1"
  local out
  out="$(ss -ltnp "( sport = :$port )" 2>/dev/null || true)"
  if [[ -n "$(printf '%s\n' "$out" | sed -n '2,$p')" ]]; then
    printf '%s\n' "$out" | sed -n '2,$p'
    return 0
  fi
  return 1
}

say "[check] repo=$ROOT_DIR"
say "[check] env_file=$ENV_FILE"
say "[check] venv=$VENV_DIR"

command -v openclaw >/dev/null 2>&1 && say "[ok] openclaw=$(openclaw --version | head -n1)" || block "openclaw CLI missing"
command -v docker >/dev/null 2>&1 && say "[ok] docker present" || warn "docker missing (infra compose unavailable)"
if docker compose version >/dev/null 2>&1; then
  say "[ok] docker compose present"
else
  warn "docker compose missing"
fi

systemctl is-active edict-dashboard.service >/dev/null 2>&1 && say "[ok] edict-dashboard.service active" || warn "edict-dashboard.service not active"
systemctl is-active edict-loop.service >/dev/null 2>&1 && say "[ok] edict-loop.service active" || warn "edict-loop.service not active"

if [[ -x "$VENV_DIR/bin/python" ]]; then
  say "[ok] backend venv present"
else
  block "backend venv missing; run scripts/setup_backend_runtime.sh"
fi

if [[ -f "$ENV_FILE" ]]; then
  say "[ok] backend env file present"
else
  block "backend env file missing: $ENV_FILE"
fi

if port_status 8000 >/tmp/edict_backend_port_8000.txt; then
  warn "port 8000 already occupied"
  cat /tmp/edict_backend_port_8000.txt
else
  say "[ok] port 8000 free"
fi
rm -f /tmp/edict_backend_port_8000.txt

if port_status 18000 >/tmp/edict_backend_port_18000.txt; then
  if systemctl is-active edict-backend-api.service >/dev/null 2>&1; then
    say "[ok] port 18000 already occupied by active edict backend API"
    cat /tmp/edict_backend_port_18000.txt
  else
    block "port 18000 already occupied"
    cat /tmp/edict_backend_port_18000.txt
  fi
else
  say "[ok] port 18000 free"
fi
rm -f /tmp/edict_backend_port_18000.txt

if port_status 5432 >/tmp/edict_backend_port_5432.txt; then
  if systemctl is-active edict-backend-infra.service >/dev/null 2>&1; then
    say "[ok] port 5432 already occupied by active edict backend infra"
    cat /tmp/edict_backend_port_5432.txt
  else
    warn "port 5432 already occupied"
    cat /tmp/edict_backend_port_5432.txt
  fi
else
  say "[ok] port 5432 free"
fi
rm -f /tmp/edict_backend_port_5432.txt

if port_status 6379 >/tmp/edict_backend_port_6379.txt; then
  if systemctl is-active edict-backend-infra.service >/dev/null 2>&1; then
    say "[ok] port 6379 already occupied by active edict backend infra"
    cat /tmp/edict_backend_port_6379.txt
  else
    warn "port 6379 already occupied"
    cat /tmp/edict_backend_port_6379.txt
  fi
else
  say "[ok] port 6379 free"
fi
rm -f /tmp/edict_backend_port_6379.txt

if python3 -m pip show alembic >/dev/null 2>&1; then
  say "[ok] system python already has alembic"
else
  warn "system python lacks alembic; use dedicated backend venv for migrations"
fi

say "[summary] blockers=$BLOCKERS warnings=$WARNS"
if (( BLOCKERS > 0 )); then
  exit 2
fi
