#!/bin/bash
# ══════════════════════════════════════════════════════════════
# 三省六部 · 一键启动脚本
# 同时启动看板服务器 + 数据刷新循环
# ══════════════════════════════════════════════════════════════

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_DIR"

DASHBOARD_HOST="${EDICT_DASHBOARD_HOST:-127.0.0.1}"
DASHBOARD_PORT="${EDICT_DASHBOARD_PORT:-7892}"
PYTHON_BIN="${EDICT_PYTHON:-python3}"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

if ! command -v "$PYTHON_BIN" &>/dev/null; then
  echo -e "${RED}❌ 未找到 Python 解释器: $PYTHON_BIN${NC}"
  exit 1
fi

mkdir -p "$REPO_DIR/data"

for f in live_status.json agent_config.json model_change_log.json sync_status.json; do
  if [[ ! -f "$REPO_DIR/data/$f" ]]; then
    echo '{}' > "$REPO_DIR/data/$f"
  fi
done
if [[ ! -f "$REPO_DIR/data/pending_model_changes.json" ]]; then
  echo '[]' > "$REPO_DIR/data/pending_model_changes.json"
fi
if [[ ! -f "$REPO_DIR/data/tasks_source.json" ]]; then
  echo '[]' > "$REPO_DIR/data/tasks_source.json"
fi
if [[ ! -f "$REPO_DIR/data/tasks.json" ]]; then
  echo '[]' > "$REPO_DIR/data/tasks.json"
fi
if [[ ! -f "$REPO_DIR/data/officials.json" ]]; then
  echo '[]' > "$REPO_DIR/data/officials.json"
fi
if [[ ! -f "$REPO_DIR/data/officials_stats.json" ]]; then
  echo '{}' > "$REPO_DIR/data/officials_stats.json"
fi

cleanup() {
  echo ""
  echo -e "${YELLOW}正在关闭服务...${NC}"
  kill $SERVER_PID $LOOP_PID 2>/dev/null
  wait $SERVER_PID $LOOP_PID 2>/dev/null
  echo -e "${GREEN}✅ 已关闭${NC}"
  exit 0
}
trap cleanup SIGINT SIGTERM

echo ""
echo -e "${BLUE}╔══════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  🏛️  三省六部 · 服务启动中               ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════╝${NC}"
echo ""

if command -v openclaw &>/dev/null; then
  echo -e "${GREEN}▶ 启动数据刷新循环...${NC}"
  bash scripts/run_loop.sh &
  LOOP_PID=$!
else
  echo -e "${YELLOW}⚠️  未检测到 OpenClaw CLI，跳过数据刷新循环${NC}"
  echo -e "${YELLOW}   看板将以只读模式运行（使用已有数据）${NC}"
  LOOP_PID=""
fi

echo -e "${GREEN}▶ 启动看板服务器...${NC}"
"$PYTHON_BIN" dashboard/server.py --host "$DASHBOARD_HOST" --port "$DASHBOARD_PORT" &
SERVER_PID=$!

sleep 1
echo ""
echo -e "${GREEN}✅ 服务已启动！${NC}"
echo -e "   内部地址: ${BLUE}http://${DASHBOARD_HOST}:${DASHBOARD_PORT}${NC}"
echo -e "   按 ${YELLOW}Ctrl+C${NC} 关闭所有服务"
echo ""

if command -v open &>/dev/null; then
  open "http://${DASHBOARD_HOST}:${DASHBOARD_PORT}"
elif command -v xdg-open &>/dev/null; then
  xdg-open "http://${DASHBOARD_HOST}:${DASHBOARD_PORT}"
fi

wait $SERVER_PID $LOOP_PID 2>/dev/null
