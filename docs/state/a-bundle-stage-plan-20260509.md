# A 包 stage 草案（2026-05-09 11:31）

## 结论

当前 A 包纯提交面候选共 21 项，但**实际有内容差异、值得本轮 stage 的只有 20 项**：
- 原因：`overlays/edict/README.md` 当前是未跟踪，但不在现行 replay 队列里承担验证闭环职责；可保留在 A 包合同层候选中，但本轮不是必须跟首个 commit 绑定。
- 另一个关键边界：`edict/backend/app/workers/orchestrator_worker.py` 同时落在 C 包（backend/dispatch/runtime）范围内，是当前唯一实质性交叉文件。

## 建议的两种 stage 方式

### 方式 A：保守收口（备选）
把 `orchestrator_worker.py` 暂时留给 C 包，先提交 A 包其余纯治理 / replay / sample 资产。

```bash
git add \
  scripts/refresh_live_data.py \
  tests/test_orchestrator_stalled.py \
  scripts/autopsy_draft.py \
  scripts/export_backend_tasks_to_legacy_json.py \
  scripts/guard_openclaw_sessions.py \
  scripts/rebuild_task_views.py \
  scripts/sync_governance_samples.py \
  tests/test_autopsy_draft.py \
  tests/test_export_backend_tasks_to_legacy_json.py \
  tests/test_guard_openclaw_sessions.py \
  tests/test_rebuild_task_views.py \
  tests/test_rebuild_task_views_merge_priority.py \
  tests/test_refresh_live_data_layers.py \
  tests/test_sync_governance_samples.py \
  tests/test_sync_governance_samples_priority.py \
  overlays/edict/scripts/replay-official-overlay.sh \
  overlays/edict/upgrade-patches/p0-manifest-20260508.md \
  overlays/edict/upgrade-patches/replay-queue-20260508.md \
  overlays/edict/layer5-tests-verification/reality-sync-20260508.md
```

适用场景：
- 想让 A 包保持“治理样本 / replay / 证据链”纯度
- 不想把 backend dispatch 主线代码提前卷进来

### 方式 B：按纯 A 包 21 项原样收
把 `edict/backend/app/workers/orchestrator_worker.py` 一起纳入，形成完整 A 包候选。

```bash
git add \
  edict/backend/app/workers/orchestrator_worker.py \
  scripts/refresh_live_data.py \
  tests/test_orchestrator_stalled.py \
  scripts/autopsy_draft.py \
  scripts/export_backend_tasks_to_legacy_json.py \
  scripts/guard_openclaw_sessions.py \
  scripts/rebuild_task_views.py \
  scripts/sync_governance_samples.py \
  tests/test_autopsy_draft.py \
  tests/test_export_backend_tasks_to_legacy_json.py \
  tests/test_guard_openclaw_sessions.py \
  tests/test_rebuild_task_views.py \
  tests/test_rebuild_task_views_merge_priority.py \
  tests/test_refresh_live_data_layers.py \
  tests/test_sync_governance_samples.py \
  tests/test_sync_governance_samples_priority.py \
  overlays/edict/scripts/replay-official-overlay.sh \
  overlays/edict/upgrade-patches/p0-manifest-20260508.md \
  overlays/edict/upgrade-patches/replay-queue-20260508.md \
  overlays/edict/layer5-tests-verification/reality-sync-20260508.md \
  overlays/edict/README.md
```

适用场景：
- 接受 A/C 之间当前唯一交叉点先落到 A 包
- 想让 autopsy 调用链与 replay 合同一次性收在同一提交里

## 明确不要 stage 的文件

### 生成产物（只留证据，不入源码提交）
```bash
# 不要 add
overlays/edict/scripts/replay-20260509-094506.summary.json
overlays/edict/scripts/replay-20260509-095728.summary.json
overlays/edict/scripts/replay-20260509-100943.summary.json
overlays/edict/scripts/replay-20260509-111957.summary.json
```

### 暂缓材料
```bash
# 先不纳入纯 A 包
overlays/edict/layer0-upstream-baseline/file-inventory-20260508.md
```

## 与 B/C 包交叉复核

- **与 B 包交叉：当前未发现实质代码交叉。**
- **与 C 包交叉：`edict/backend/app/workers/orchestrator_worker.py` 是唯一明确交叉文件。**
- A 包其余脚本 / 测试 / replay 合同文件当前未落进 B 包 diff 清单。

## 推荐

本轮优先采用**方式 B**。

原因：
1. `tests/test_orchestrator_stalled.py` 的当前 diff 已经明确依赖 `edict/backend/app/workers/orchestrator_worker.py` 的实现改动；测试不再接受 `scripts/kanban_update.py autopsy`，而是显式断言 `autopsy_draft.py`、`--reason`、且不再出现 `autopsy` 子命令。
2. 如果把 `orchestrator_worker.py` 留给 C 包、只先提测试与脚本，极易形成**假原子提交**：staged 结果里的测试语义已经前移，但实现改动还留在工作区。
3. A/C 之间当前唯一交叉点就是 `orchestrator_worker.py`，与其硬拆出一个不稳的“纯 A 包”，不如承认这条交叉并把它和 stalled/autopsy 行为链一起收在同一提交里，解释成本反而更低。
4. 与 B 包当前没有实质代码交叉，因此改用方式 B 不会把前端/dashboard 面一起卷进来。
