#!/bin/bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAMP="$(date +%Y%m%d-%H%M%S)"
DEFAULT_OUT="${HOME}/.openclaw/backups/edict-memory-${STAMP}"
OUT_DIR="${1:-$DEFAULT_OUT}"
# 统一转成绝对路径，避免调用方传相对路径时递归保护失效。
# 例：在 repo 根目录传 isolation/... 时，逻辑上位于 workspace 内，
# 但旧 case 用相对路径比较，无法命中 "$workspace_src"/*。
mkdir -p "$OUT_DIR"
OUT_DIR="$(cd "$OUT_DIR" && pwd)"

mkdir -p "$OUT_DIR"

echo "备份输出目录: $OUT_DIR"

copy_if_exists() {
  local src="$1"
  local dest="$2"
  if [[ -e "$src" ]]; then
    mkdir -p "$(dirname "$dest")"
    if [[ -d "$src" ]]; then
      tar \
        --warning=no-file-changed \
        --ignore-failed-read \
        --exclude='*.tmp' \
        --exclude='*.lock' \
        --exclude='.venv*' \
        --exclude='node_modules' \
        --exclude='isolation' \
        --exclude='logs' \
        -C "$(dirname "$src")" \
        -cf - "$(basename "$src")" | tar -C "$(dirname "$dest")" -xf -
    else
      cp -a "$src" "$dest"
    fi
    echo "✅ 已备份: $src"
  else
    echo "⚠️  跳过不存在路径: $src"
  fi
}

copy_if_exists "$REPO_DIR/data/agent_memory" "$OUT_DIR/data/agent_memory"
copy_if_exists "$REPO_DIR/data/task_memory" "$OUT_DIR/data/task_memory"
copy_if_exists "$REPO_DIR/data/shared_memory.json" "$OUT_DIR/data/shared_memory.json"
copy_if_exists "$REPO_DIR/data/tasks_source.json" "$OUT_DIR/data/tasks_source.json"
copy_if_exists "$REPO_DIR/data/tasks.json" "$OUT_DIR/data/tasks.json"
copy_if_exists "$HOME/.openclaw/openclaw.json" "$OUT_DIR/openclaw.json"

# 备份 workspace 时不能把备份目录放在 workspace 内，否则 cp 会递归复制自身。
workspace_src="$HOME/.openclaw/workspace"
if [[ -d "$workspace_src" ]]; then
  case "$OUT_DIR" in
    "$workspace_src"|"$workspace_src"/*)
      echo "⚠️  跳过 workspace 整体备份：输出目录位于 workspace 内，会导致递归复制。"
      ;;
    *)
      copy_if_exists "$workspace_src" "$OUT_DIR/openclaw-workspace"
      ;;
  esac
fi

echo "备份完成: $OUT_DIR"
