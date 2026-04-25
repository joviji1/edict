#!/bin/bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OC_HOME="${HOME}/.openclaw"
OC_CFG="${OC_HOME}/openclaw.json"
DASHBOARD_HOST="${EDICT_DASHBOARD_HOST:-127.0.0.1}"
DASHBOARD_PORT="${EDICT_DASHBOARD_PORT:-7892}"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
PASS=0
WARN=0
FAIL=0

report() {
  local level="$1"; shift
  case "$level" in
    ok)   PASS=$((PASS+1)); echo -e "${GREEN}✅ $*${NC}" ;;
    warn) WARN=$((WARN+1)); echo -e "${YELLOW}⚠️  $*${NC}" ;;
    fail) FAIL=$((FAIL+1)); echo -e "${RED}❌ $*${NC}" ;;
    info) echo -e "${BLUE}ℹ️  $*${NC}" ;;
  esac
}

check_cmd() {
  local cmd="$1"
  if command -v "$cmd" >/dev/null 2>&1; then
    report ok "命令存在: $cmd"
  else
    report warn "命令缺失: $cmd"
  fi
}

check_path() {
  local p="$1"
  if [[ -e "$p" ]]; then
    report ok "路径存在: $p"
  else
    report fail "路径缺失: $p"
  fi
}

check_json() {
  local p="$1"
  if [[ ! -f "$p" ]]; then
    report fail "JSON 文件不存在: $p"
    return
  fi
  if python3 - <<'PY' "$p"
import json, sys
from pathlib import Path
path = Path(sys.argv[1])
json.loads(path.read_text())
print('ok')
PY
  then
    report ok "JSON 校验通过: $p"
  else
    report fail "JSON 校验失败: $p"
  fi
}

check_port() {
  local port="$1"
  if ss -ltn 2>/dev/null | awk '{print $4}' | grep -Eq "[:.]${port}$"; then
    report ok "端口监听中: $port"
  else
    report warn "端口未监听: $port"
  fi
}

check_url() {
  local url="$1"
  if python3 - <<'PY' "$url"
import json, sys, urllib.request
url = sys.argv[1]
with urllib.request.urlopen(url, timeout=3) as r:
    body = r.read().decode('utf-8', 'ignore')
print(body[:200])
PY
  then
    report ok "HTTP 可达: $url"
  else
    report warn "HTTP 不可达: $url"
  fi
}

check_systemd() {
  local mode="$1"
  local unit="$2"
  if [[ "$mode" == "user" ]]; then
    if systemctl --user is-active --quiet "$unit"; then
      report ok "systemd user 服务运行中: $unit"
    else
      report warn "systemd user 服务未运行: $unit"
    fi
  else
    if systemctl is-active --quiet "$unit"; then
      report ok "systemd 服务运行中: $unit"
    else
      report warn "systemd 服务未运行: $unit"
    fi
  fi
}

report info "开始巡检 edict / OpenClaw / dashboard 环境"
report info "REPO_DIR=$REPO_DIR"

check_cmd python3
check_cmd openclaw
check_cmd jq
check_cmd ss

check_path "$REPO_DIR/data"
check_path "$REPO_DIR/dashboard/server.py"
check_path "$REPO_DIR/scripts/run_loop.sh"
check_path "$OC_HOME"
check_json "$OC_CFG"

for rel in tasks_source.json tasks.json officials.json officials_stats.json live_status.json sync_status.json; do
  check_path "$REPO_DIR/data/$rel"
done

for ws in taizi zhongshu menxia shangshu hubu libu bingbu xingbu gongbu libu_hr; do
  if [[ -d "$OC_HOME/workspace-$ws" ]]; then
    report ok "workspace 存在: workspace-$ws"
  else
    report warn "workspace 缺失: workspace-$ws"
  fi
done

check_systemd user hermes-gateway
check_systemd system edict-dashboard.service
check_systemd system edict-loop.service

check_path "/root/.hermes/logs/gateway.log"
check_port "$DASHBOARD_PORT"
check_url "http://${DASHBOARD_HOST}:${DASHBOARD_PORT}/healthz"

report info "最近日志提示（如果存在）"
for f in "/root/.hermes/logs/gateway.log" "$REPO_DIR/logs/server.log" "$REPO_DIR/logs/loop.log"; do
  if [[ -f "$f" ]]; then
    echo "--- tail $f ---"
    tail -n 5 "$f" || true
  fi
done

echo
echo "PASS=$PASS WARN=$WARN FAIL=$FAIL"
if [[ "$FAIL" -gt 0 ]]; then
  exit 1
fi
