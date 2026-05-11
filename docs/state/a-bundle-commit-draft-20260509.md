# A 包 commit 草稿（2026-05-09 11:31）

## 推荐提交标题（方式 B）

```text
feat(治理回放): 接通 autopsy 旁路与 official replay 合同
```

## 推荐提交正文（方式 B）

```text
- 将 orchestrator stalled 分支与 autopsy_draft 旁路草稿链一起纳入 A 包提交面
- 新增治理样本 / export / guard / replay 合同脚本及测试，补齐 official clean replay 证据链
- 明确排除 replay summary 生成产物，仅提交源码与合同文件

验证：
- python3 -m py_compile scripts/autopsy_draft.py scripts/export_backend_tasks_to_legacy_json.py scripts/guard_openclaw_sessions.py scripts/rebuild_task_views.py scripts/sync_governance_samples.py scripts/refresh_live_data.py edict/backend/app/workers/orchestrator_worker.py tests/test_autopsy_draft.py tests/test_orchestrator_stalled.py tests/test_export_backend_tasks_to_legacy_json.py tests/test_guard_openclaw_sessions.py tests/test_rebuild_task_views.py tests/test_rebuild_task_views_merge_priority.py tests/test_refresh_live_data_layers.py tests/test_sync_governance_samples.py tests/test_sync_governance_samples_priority.py
- python3 -m pytest -q tests/test_autopsy_draft.py tests/test_orchestrator_stalled.py tests/test_export_backend_tasks_to_legacy_json.py tests/test_guard_openclaw_sessions.py tests/test_rebuild_task_views.py tests/test_rebuild_task_views_merge_priority.py tests/test_refresh_live_data_layers.py tests/test_sync_governance_samples.py tests/test_sync_governance_samples_priority.py
- bash overlays/edict/scripts/replay-official-overlay.sh
```

## 备选提交标题（方式 A）

```text
feat(治理回放): 收口 autopsy 草稿链与 replay 合同
```

## 备选提交正文（方式 A）

```text
- 新增 autopsy_draft / export_backend_tasks_to_legacy_json / guard_openclaw_sessions / rebuild_task_views / sync_governance_samples 等治理脚本与回归测试
- 补齐 replay-official-overlay 合同、P0 清单和 reality-sync 文档，形成 A 包独立候选提交面
- 固化治理样本聚合、refresh_live_data 与 stalled/autopsy 行为验证链

验证：
- python3 -m py_compile scripts/autopsy_draft.py scripts/export_backend_tasks_to_legacy_json.py scripts/guard_openclaw_sessions.py scripts/rebuild_task_views.py scripts/sync_governance_samples.py scripts/refresh_live_data.py edict/backend/app/workers/orchestrator_worker.py tests/test_autopsy_draft.py tests/test_orchestrator_stalled.py tests/test_export_backend_tasks_to_legacy_json.py tests/test_guard_openclaw_sessions.py tests/test_rebuild_task_views.py tests/test_rebuild_task_views_merge_priority.py tests/test_refresh_live_data_layers.py tests/test_sync_governance_samples.py tests/test_sync_governance_samples_priority.py
- python3 -m pytest -q tests/test_autopsy_draft.py tests/test_orchestrator_stalled.py tests/test_export_backend_tasks_to_legacy_json.py tests/test_guard_openclaw_sessions.py tests/test_rebuild_task_views.py tests/test_rebuild_task_views_merge_priority.py tests/test_refresh_live_data_layers.py tests/test_sync_governance_samples.py tests/test_sync_governance_samples_priority.py
- bash overlays/edict/scripts/replay-official-overlay.sh
```

## 说明

- 当前推荐口径已切到**方式 B**，因为 `tests/test_orchestrator_stalled.py` 与 `edict/backend/app/workers/orchestrator_worker.py` 存在真实实现/测试联动，不宜硬拆。
- 若你仍想采用方式 A，提交前必须再跑一次 `git diff --cached --name-only`，确认 `tests/test_orchestrator_stalled.py` 与未纳入的 `edict/backend/app/workers/orchestrator_worker.py` 不会形成失配。
- 只要发现 staged 状态下测试语义依赖 `orchestrator_worker.py` 的实现改动，就应改用方式 B，不要硬拆出假原子提交。
