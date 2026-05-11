#!/bin/bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

MODE="${1:-plan}"
BACKUP_ROOT="${EDICT_BACKUP_ROOT:-$HOME/.openclaw/backups}"
STAMP="$(date +%Y%m%d-%H%M%S)"
RUN_DIR="$BACKUP_ROOT/safe-update-$STAMP"
PLAN_FILE="$RUN_DIR/plan.json"
LOG_FILE="$RUN_DIR/safe_update.log"
RESTART_TOKEN="CONFIRM_RESTART_EDICT"
ROLLBACK_TOKEN="CONFIRM_ROLLBACK_EDICT"

log() { echo "[safe_update] $*" | tee -a "$LOG_FILE"; }
fail() { log "失败: $*"; exit 1; }

usage() {
  cat <<EOF
用法: scripts/safe_update.sh [plan|prepare|test|apply|restart|rollback] [run_dir]

阶段说明：
  plan      只生成升级计划与风险提示，不改服务
  prepare   备份关键数据/配置/代码指针，并做 JSON/doctor 预检
  test      运行 py_compile 与 pytest，不重启
  apply     执行低风险迁移/依赖检查；默认不 git pull、不重启
  restart   需要 EDICT_SAFE_UPDATE_CONFIRM=$RESTART_TOKEN 才会重启 edict 服务
  rollback  需要 EDICT_SAFE_UPDATE_CONFIRM=$ROLLBACK_TOKEN 才会按备份提示回滚数据并重启

示例：
  scripts/safe_update.sh prepare
  scripts/safe_update.sh test /root/.openclaw/backups/safe-update-YYYYmmdd-HHMMSS
  EDICT_SAFE_UPDATE_CONFIRM=$RESTART_TOKEN scripts/safe_update.sh restart /root/.openclaw/backups/safe-update-YYYYmmdd-HHMMSS
EOF
}

if [[ "$MODE" == "-h" || "$MODE" == "--help" ]]; then
  usage
  exit 0
fi

if [[ "${2:-}" != "" ]]; then
  RUN_DIR="$2"
  PLAN_FILE="$RUN_DIR/plan.json"
  LOG_FILE="$RUN_DIR/safe_update.log"
fi
mkdir -p "$RUN_DIR"
touch "$LOG_FILE"

write_plan() {
  python3 - <<'PY' "$PLAN_FILE" "$REPO_DIR" "$RUN_DIR" "$RESTART_TOKEN" "$ROLLBACK_TOKEN"
import json, subprocess, sys, datetime
from pathlib import Path
plan_path = Path(sys.argv[1])
repo = sys.argv[2]
run_dir = sys.argv[3]
restart_token = sys.argv[4]
rollback_token = sys.argv[5]
def cmd(args):
    try:
        return subprocess.check_output(args, cwd=repo, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return ''
plan = {
    'generatedAt': datetime.datetime.now().isoformat(timespec='seconds'),
    'repo': repo,
    'runDir': run_dir,
    'git': {
        'branch': cmd(['git','rev-parse','--abbrev-ref','HEAD']),
        'head': cmd(['git','rev-parse','HEAD']),
        'status': cmd(['git','status','--short']),
    },
    'services': ['edict-dashboard.service', 'edict-loop.service'],
    'stages': [
        {'name': 'prepare', 'sideEffect': 'file backups only'},
        {'name': 'test', 'sideEffect': 'none'},
        {'name': 'apply', 'sideEffect': 'local validation/migration dry-run only by default'},
        {'name': 'restart', 'sideEffect': 'systemctl restart edict-dashboard.service edict-loop.service', 'requiresEnv': f'EDICT_SAFE_UPDATE_CONFIRM={restart_token}'},
        {'name': 'rollback', 'sideEffect': 'restore selected backup files and restart services', 'requiresEnv': f'EDICT_SAFE_UPDATE_CONFIRM={rollback_token}'},
    ],
    'policy': 'No service restart, destructive migration, git pull, or rollback unless explicit confirmation token is present.',
}
Path(plan_path).write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding='utf-8')
print(plan_path)
PY
}

backup_file() {
  local src="$1"
  local rel="$2"
  if [[ -e "$src" ]]; then
    mkdir -p "$RUN_DIR/$(dirname "$rel")"
    if [[ -d "$src" ]]; then
      # 数据目录可能被运行态 atomic write 留下短生命周期 *.tmp。
      # 备份快照只需要稳定文件，避免 cp 复制目录过程中源 tmp 被 rename/unlink 后中断整个 prepare。
      tar \
        --warning=no-file-changed \
        --ignore-failed-read \
        --exclude='*.tmp' \
        --exclude='*.lock' \
        -C "$(dirname "$src")" \
        -cf - "$(basename "$src")" | tar -C "$RUN_DIR/$(dirname "$rel")" -xf -
    else
      cp -a "$src" "$RUN_DIR/$rel"
    fi
    log "已备份: $src -> $RUN_DIR/$rel"
  else
    log "跳过备份，路径不存在: $src"
  fi
}

stage_plan() {
  write_plan | tee -a "$LOG_FILE"
  log "已生成升级计划: $PLAN_FILE"
  log "安全策略: 默认不 git pull、不迁移写库、不重启；restart/rollback 必须带确认令牌。"
}

stage_prepare() {
  stage_plan
  log "步骤 prepare: 备份关键记忆、任务数据、配置、systemd 单元和 git 指针"
  EDICT_MEMORY_BACKUP_SKIP_WORKSPACE=1 bash "$REPO_DIR/scripts/memory_backup.sh" "$RUN_DIR/memory" | tee -a "$LOG_FILE"
  backup_file "$HOME/.openclaw/openclaw.json" "config/openclaw.json"
  backup_file "$REPO_DIR/data" "data"
  backup_file "/etc/systemd/system/edict-dashboard.service" "systemd/edict-dashboard.service"
  backup_file "/etc/systemd/system/edict-loop.service" "systemd/edict-loop.service"
  git rev-parse HEAD > "$RUN_DIR/git-head.txt" 2>/dev/null || true
  git status --short > "$RUN_DIR/git-status.txt" 2>/dev/null || true

  log "JSON 配置校验"
  python3 - <<'PY'
import json
from pathlib import Path
for p in [Path.home()/'.openclaw'/'openclaw.json', Path('data/tasks_source.json'), Path('data/officials_stats.json')]:
    if p.exists():
        json.loads(p.read_text(encoding='utf-8'))
        print(f'ok {p}')
    else:
        print(f'skip missing {p}')
PY

  log "执行 doctor 预检"
  bash "$REPO_DIR/scripts/doctor_edict.sh" | tee -a "$LOG_FILE"
}

stage_test() {
  log "步骤 test: 语法检查与回归测试，不重启"
  python3 -m py_compile dashboard/server.py dashboard/court_discuss.py scripts/sync_officials_stats.py scripts/kanban_update.py
  python3 -m pytest -q tests/test_sync_officials_stats.py tests/test_server.py tests/test_kanban.py tests/test_kanban_autopsy.py tests/test_safe_update_script.py
  log "test 阶段通过"
}

stage_apply() {
  log "步骤 apply: 低风险应用阶段"
  if [[ -f requirements.txt ]]; then
    python3 -m pip install --dry-run -r requirements.txt | tee -a "$LOG_FILE" || log "pip dry-run 不可用或依赖解析警告，未执行真实安装"
  fi
  if [[ -f edict/migration/migrate_json_to_pg.py ]]; then
    log "检测到 PG 迁移脚本；本机 JSON 看板模式不自动写库，仅保留 dry-run 入口。"
  fi
  bash "$REPO_DIR/scripts/doctor_edict.sh" | tee -a "$LOG_FILE"
  log "apply 阶段完成：未重启服务。若需要切换运行态，显式执行 restart 阶段并提供确认令牌。"
}

stage_restart() {
  [[ "${EDICT_SAFE_UPDATE_CONFIRM:-}" == "$RESTART_TOKEN" ]] || fail "restart 需要 EDICT_SAFE_UPDATE_CONFIRM=$RESTART_TOKEN"
  log "步骤 restart: 重启 edict dashboard/loop 服务"
  systemctl restart edict-dashboard.service
  systemctl restart edict-loop.service
  sleep 2
  bash "$REPO_DIR/scripts/doctor_edict.sh" | tee -a "$LOG_FILE"
  log "restart 阶段完成"
}

stage_rollback() {
  [[ "${EDICT_SAFE_UPDATE_CONFIRM:-}" == "$ROLLBACK_TOKEN" ]] || fail "rollback 需要 EDICT_SAFE_UPDATE_CONFIRM=$ROLLBACK_TOKEN"
  [[ -d "$RUN_DIR/data" ]] || fail "缺少备份数据目录: $RUN_DIR/data"
  log "步骤 rollback: 恢复 data 与 openclaw 配置备份，然后重启 edict 服务"
  cp -a "$RUN_DIR/data/." "$REPO_DIR/data/"
  if [[ -f "$RUN_DIR/config/openclaw.json" ]]; then
    cp -a "$RUN_DIR/config/openclaw.json" "$HOME/.openclaw/openclaw.json"
  fi
  systemctl restart edict-dashboard.service
  systemctl restart edict-loop.service
  sleep 2
  bash "$REPO_DIR/scripts/doctor_edict.sh" | tee -a "$LOG_FILE"
  log "rollback 阶段完成"
}

case "$MODE" in
  plan) stage_plan ;;
  prepare) stage_prepare ;;
  test) stage_test ;;
  apply) stage_apply ;;
  restart) stage_restart ;;
  rollback) stage_rollback ;;
  *) usage; fail "未知阶段: $MODE" ;;
esac
