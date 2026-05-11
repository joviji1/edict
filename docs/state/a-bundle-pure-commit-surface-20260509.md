# A 包纯提交面候选（2026-05-09 11:23）

## 结论

- 纯 A 包提交面候选：**21 项**
- 其中核心代码/测试：**16 项**
- 其中 replay 合同文件：**5 项**
- 明确排除的纯生成产物：**4 项**
- 暂不纳入本轮纯 A 包的人工保留项：**1 项**

## 1. 核心代码 / 测试

- `edict/backend/app/workers/orchestrator_worker.py`
- `scripts/refresh_live_data.py`
- `tests/test_orchestrator_stalled.py`
- `scripts/autopsy_draft.py`
- `scripts/export_backend_tasks_to_legacy_json.py`
- `scripts/guard_openclaw_sessions.py`
- `scripts/rebuild_task_views.py`
- `scripts/sync_governance_samples.py`
- `tests/test_autopsy_draft.py`
- `tests/test_export_backend_tasks_to_legacy_json.py`
- `tests/test_guard_openclaw_sessions.py`
- `tests/test_rebuild_task_views.py`
- `tests/test_rebuild_task_views_merge_priority.py`
- `tests/test_refresh_live_data_layers.py`
- `tests/test_sync_governance_samples.py`
- `tests/test_sync_governance_samples_priority.py`

## 2. replay 合同文件

- `overlays/edict/README.md`
- `overlays/edict/scripts/replay-official-overlay.sh`
- `overlays/edict/upgrade-patches/p0-manifest-20260508.md`
- `overlays/edict/upgrade-patches/replay-queue-20260508.md`
- `overlays/edict/layer5-tests-verification/reality-sync-20260508.md`

## 3. 明确排除：纯生成产物

- `overlays/edict/scripts/replay-20260509-094506.summary.json`
- `overlays/edict/scripts/replay-20260509-095728.summary.json`
- `overlays/edict/scripts/replay-20260509-100943.summary.json`
- `overlays/edict/scripts/replay-20260509-111957.summary.json`

## 4. 暂不纳入纯 A 包

- `overlays/edict/layer0-upstream-baseline/file-inventory-20260508.md`

## 口径说明

- `overlays/edict/scripts/replay-*.summary.json` 属于 replay 运行生成物，保留为证据，但不应并入纯 A 包提交面。
- `overlays/edict/*` 中只保留 replay 合同与说明文件；不把生成 summary 当源码交付。
- `overlays/edict/layer0-upstream-baseline/file-inventory-20260508.md` 更像基线上游盘点材料，不是 A 包主链必要提交物，因此先留在纯 A 包之外。
- 本清单只针对 A 包；不自动吸入 P1/P2 的 deploy/docs 交付层。
