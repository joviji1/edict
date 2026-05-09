# edict overlay replay queue — 2026-05-08

> 用途：从官方 clean baseline 开始，按 P0 → P1 → P2 连续回放本机 overlay，并在每层后做 compile/build 验证。不要直接整仓 merge。

## Baseline

- upstream: `/root/.openclaw/workspace/_third_party/cft0808-edict-upstream` @ `14a2075`
- local overlay source: `/root/.openclaw/workspace/edict` @ `a239c8e` + 当前工作树生产增量
- latest queue extension: 2026-05-09 将 P4 `autopsy / stalled` 旁路草稿器纳入 P0/replay 验证，并将前端依赖审计修复纳入 P0，避免 clean replay 漏带新脚本、测试与 `npm audit` 安全基线。

## P0 — 保命层

误回归会直接打断 dashboard/backend/dispatch/runtime/export/self-heal 主链。

```text
dashboard/server.py
dashboard/court_discuss.py
install.sh
start.sh
edict.sh
edict/frontend/package.json
edict/frontend/package-lock.json
scripts/run_loop.sh
scripts/apply_model_changes.py
scripts/autopsy_draft.py
scripts/sync_agent_config.py
scripts/sync_from_openclaw_runtime.py
scripts/sync_officials_stats.py
scripts/refresh_live_data.py
scripts/sync_governance_samples.py
scripts/rebuild_task_views.py
scripts/export_backend_tasks_to_legacy_json.py
scripts/guard_openclaw_sessions.py
scripts/utils.py
edict/backend/app/api/tasks.py
edict/backend/app/api/legacy.py
edict/backend/app/models/task.py
edict/backend/app/services/task_service.py
edict/backend/app/services/notification_service.py
edict/backend/app/workers/__init__.py
edict/backend/app/workers/dispatch_worker.py
edict/backend/app/workers/orchestrator_worker.py
edict/migration/versions/002_add_outbox_events.py
tests/test_server.py
tests/test_autopsy_draft.py
tests/test_sync_governance_samples.py
```

## P1 — 保运维与可回滚层

影响升级、排障、回滚效率；不一定立刻打断主链，但必须随 P0 保持一致。

```text
scripts/doctor_edict.sh
scripts/check_backend_prereqs.sh
scripts/manage_backend_infra.sh
scripts/run_backend_component.sh
scripts/run_backend_migrations.sh
scripts/setup_backend_runtime.sh
deploy/
docs/current-progress-board.md
docs/closeout.md
docs/governance-upgrade-map.md
docs/review-correction-notes.md
docs/task-dispatch-architecture.md
docs/backend-host-native-productionization.md
```

## P2 — 保交付沉淀层

不直接决定服务存活，但决定主线交付口径、复盘、后续解释是否可恢复。

```text
docs/JJC-20260416-001-sansheng-governance-executable-review.md
docs/JJC-20260416-001-task-division-plan.txt
docs/openclaw-feishu-p2p-hotfix.md
docs/edict-official-overlay-alignment-20260508.md
docs/edict-completion-status-20260426.md
docs/natural-governance-sample-thickening-plan.md
docs/openclaw-feishu-bypass-compensation-runbook.md
docs/openclaw-feishu-bypass-duty-template.md
docs/ARCHITECTURE.md
docs/FRONTEND.md
docs/RELIABILITY.md
docs/SECURITY.md
docs/exec-plans/
docs/plans/
docs/state/
docs/templates/
overlays/edict/
```

## Replay contract

1. 创建官方 clean worktree。
2. 验证 official baseline：Python compile + frontend build。
3. apply P0，验证 Python compile + shell syntax + frontend audit + frontend build。
4. apply P1，验证 Python compile + shell syntax。
5. apply P2，验证 docs/overlay 文件存在。
6. final behavior：运行 `tests/test_server.py` + `tests/test_autopsy_draft.py` + `tests/test_sync_governance_samples.py`，必须以真实输出为准。
7. replay 成功后输出机器可读摘要：`overlays/edict/scripts/replay-<timestamp>.summary.json`，至少包含 baseline、log、worktree、P0/P1/P2 文件清单和 behavior 命令。

## 当前状态

- P0/P1/P2 已固化入队列。
- replay 实现脚本：`overlays/edict/scripts/replay-official-overlay.sh`。
