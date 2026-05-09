#!/bin/bash
# 三省六部 · 数据刷新循环
# 用法: ./run_loop.sh [间隔秒数 [保留参数]]
#   间隔秒数：数据刷新频率，默认 15 秒
#   保留参数：历史兼容位，默认 120；当前仅用于展示，实际 scheduler-scan
#             已由 dashboard/server.py 内部 120 秒定时线程负责

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export EDICT_HOME="${EDICT_HOME:-$(dirname "$SCRIPT_DIR")}"
PYTHON_BIN="${EDICT_PYTHON:-python3}"
INTERVAL="${1:-15}"
LOG="/tmp/sansheng_liubu_refresh.log"
PIDFILE="/tmp/sansheng_liubu_refresh.pid"
MAX_LOG_SIZE=$((10 * 1024 * 1024))  # 10MB

# ── 单实例保护 ──
if [[ -f "$PIDFILE" ]]; then
  OLD_PID=$(cat "$PIDFILE" 2>/dev/null)
  if kill -0 "$OLD_PID" 2>/dev/null; then
    echo "❌ 已有实例运行中 (PID=$OLD_PID)，退出"
    exit 1
  fi
  rm -f "$PIDFILE"
fi
echo $$ > "$PIDFILE"

# ── 优雅退出 ──
cleanup() {
  echo "$(date '+%H:%M:%S') [loop] 收到退出信号，清理中..." >> "$LOG"
  rm -f "$PIDFILE"
  exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# ── 日志轮转 ──
rotate_log() {
  if [[ -f "$LOG" ]] && (( $(stat -f%z "$LOG" 2>/dev/null || stat -c%s "$LOG" 2>/dev/null || echo 0) > MAX_LOG_SIZE )); then
    mv "$LOG" "${LOG}.1"
    echo "$(date '+%H:%M:%S') [loop] 日志已轮转" > "$LOG"
  fi
}

SCAN_INTERVAL="${2:-120}"  # 历史兼容展示位；实际巡检由 dashboard 内部线程负责
SCAN_COUNTER=0
SCRIPT_TIMEOUT=30  # 普通脚本最大执行时间(秒)
MODEL_APPLY_TIMEOUT=75  # 模型应用脚本允许更长的 Gateway 重启窗口
DASHBOARD_PORT="${EDICT_DASHBOARD_PORT:-7891}"  # 看板端口，可通过环境变量覆盖
BACKEND_EXPORT_ENABLED="${EDICT_ENABLE_BACKEND_EXPORT:-0}"  # 默认关闭；显式开启后才用 backend 导出覆盖 tasks_source

echo "🏛️  三省六部数据刷新循环启动 (PID=$$)"
echo "   脚本目录: $SCRIPT_DIR"
echo "   间隔: ${INTERVAL}s"
echo "   巡检提示(兼容参数): ${SCAN_INTERVAL}s（实际由 dashboard 内部 120s 线程执行）"
echo "   脚本超时: ${SCRIPT_TIMEOUT}s"
echo "   日志: $LOG"
echo "   PID文件: $PIDFILE"
echo "   按 Ctrl+C 停止"

# ── 安全执行（带超时保护）──
safe_run_timeout() {
  local script="$1"
  local timeout_sec="$2"
  if command -v timeout &>/dev/null; then
    timeout "$timeout_sec" "$PYTHON_BIN" "$script" >> "$LOG" 2>&1 || {
      local rc=$?
      if [[ $rc -eq 124 ]]; then
        echo "$(date '+%H:%M:%S') [loop] ⚠️ 脚本超时(${timeout_sec}s): $script" >> "$LOG"
      fi
    }
  else
    "$PYTHON_BIN" "$script" >> "$LOG" 2>&1 || true
  fi
}

safe_run() {
  local script="$1"
  safe_run_timeout "$script" "$SCRIPT_TIMEOUT"
}

is_true() {
  local value="${1:-}"
  case "${value,,}" in
    1|true|yes|on) return 0 ;;
    *) return 1 ;;
  esac
}

while true; do
  rotate_log
  safe_run "$SCRIPT_DIR/guard_openclaw_sessions.py"
  safe_run "$SCRIPT_DIR/sync_from_openclaw_runtime.py"
  safe_run "$SCRIPT_DIR/sync_governance_samples.py"
  safe_run "$SCRIPT_DIR/rebuild_task_views.py"
  if is_true "$BACKEND_EXPORT_ENABLED"; then
    safe_run "$SCRIPT_DIR/export_backend_tasks_to_legacy_json.py"
  else
    echo "$(date '+%H:%M:%S') [loop] backend export 默认关闭；如需启用请设置 EDICT_ENABLE_BACKEND_EXPORT=true" >> "$LOG"
  fi
  safe_run "$SCRIPT_DIR/sync_agent_config.py"
  safe_run_timeout "$SCRIPT_DIR/apply_model_changes.py" "$MODEL_APPLY_TIMEOUT"
  safe_run "$SCRIPT_DIR/sync_officials_stats.py"
  safe_run "$SCRIPT_DIR/refresh_live_data.py"
  safe_run "$SCRIPT_DIR/baota_webserver_patrol.py"

  # scheduler-scan 已由 dashboard/server.py 内部 120s 定时线程负责。
  # 这里不再额外 curl /api/scheduler-scan，避免在 JWT 开启后持续产生 401 噪音与假动作。

  sleep "$INTERVAL"
done
