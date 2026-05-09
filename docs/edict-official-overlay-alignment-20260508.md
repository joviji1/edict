# edict 官方基线对齐 + 本机 overlay 分层提升方案

更新时间：2026-05-08 18:55（北京时间）

## 1. 结论先说

本机 `/root/.openclaw/workspace/edict` 不能再按普通 fork 处理。

它现在是：

- 上游 `cft0808/edict` 的 host-native 生产化分叉；
- 叠加了 backend dual/API/export、PendingConfirm、三层任务视图、OpenClaw session guard、dashboard 登录态、急递铺/审批/UI 等大量本地增强；
- 同时也存在测试预期漂移、三面数据不一致、历史文档与当前运行态不完全一致的问题。

所以以后升级官方版，正确方式不是 `git merge upstream/main`，而是走：

1. 官方基线只读审计；
2. 本机魔改 overlay 分层；
3. P0/P1/P2 patch 队列回放；
4. 再定向吸收上游新增能力；
5. 最后做真实运行验证和主板回写。

## 2. 上游逐块阅读结果

上游只读副本：

- `/root/.openclaw/workspace/_third_party/cft0808-edict-upstream`
- HEAD：`14a2075`
- 文件总数：`221`

### 2.1 backend

路径：`edict/backend`

- 文件数：35
- 核心：FastAPI backend、SQLAlchemy model、TaskService、OutboxEvent、Redis EventBus、orchestrator/dispatch/outbox workers。
- 已读关键文件：
  - `edict/backend/app/services/task_service.py`
  - `edict/backend/app/workers/dispatch_worker.py`
  - `edict/backend/app/workers/orchestrator_worker.py`
  - `edict/backend/app/api/tasks.py`
  - `edict/backend/app/api/legacy.py`
  - `edict/backend/app/models/task.py`

上游能力边界：

- 有基础状态机、outbox、Redis worker、stalled retry/escalation。
- 高风险状态确认、PendingConfirm、通知标记、legacy 兼容和本机生产链相比明显更薄。

### 2.2 frontend

路径：`edict/frontend`

- 文件数：31
- 核心：React/Vite + Zustand store + 10 个基础 tab。
- 已读关键文件：
  - `edict/frontend/src/store.ts`
  - `edict/frontend/src/api.ts`
  - `edict/frontend/src/App.tsx`
  - `edict/frontend/src/components/TaskModal.tsx`
  - `edict/frontend/src/components/EdictBoard.tsx`

上游能力边界：

- 基础看板和模型/技能/官员/任务详情面板存在。
- 本机新增的登录态、急递铺/国史馆、审批面板、JJC 过滤、更多治理字段展示不属于上游基线。

### 2.3 scripts

路径：`scripts`

- 文件数：15
- 核心：`run_loop.sh`、runtime sync、model apply、live refresh、agent config sync、kanban_update。
- 已读关键文件：
  - `scripts/run_loop.sh`
  - `scripts/refresh_live_data.py`
  - `scripts/sync_from_openclaw_runtime.py`
  - `scripts/apply_model_changes.py`
  - `scripts/sync_agent_config.py`

上游能力边界：

- 具备基础 15 秒循环刷新和 120 秒 scheduler scan。
- 本机额外引入 backend export、governance sample、session guard、doctor、backend runtime 管理、migration/export/rebuild 等生产脚本。

### 2.4 tests

路径：`tests`

- 上游测试数：12
- 本机测试已大幅扩张，`tests/test_server.py` 从上游 41 行扩到本机 1996 行。

当前问题：

- 本机测试不是简单“更多覆盖”，而是很多测试已经绑定历史行为预期。
- 本轮目标 pytest 组合结果为 `63 passed / 11 failed`，失败集中在本机生产行为与旧测试预期漂移。

### 2.5 docs

路径：`docs`

- 上游文件数：48，其中大量为截图/素材。
- 上游主文档仍偏通用展示：10 面板、官方演示口径、基础任务分发架构。
- 本机 docs 已变成生产运行账本：`current-progress-board.md`、`closeout.md`、`verification-ledger.json`、`feature-status.json`、正式交付稿和多轮治理方案。

## 3. 本机真实运行态审计

时间：2026-05-08 18:47（北京时间）

### 3.1 服务状态

- `edict-dashboard.service`: active
- `edict-loop.service`: active
- Dashboard: `127.0.0.1:7892/healthz` -> ok
- Backend: `127.0.0.1:18000/health` -> ok, `version=2.0.0`, `engine=edict`
- Deep health: postgres=true, redis=true

### 3.2 当前环境变量

- dashboard: `EDICT_TASK_WRITE_MODE=dual`
- loop: `EDICT_ENABLE_BACKEND_EXPORT=false`

这解释了为什么当前 `live_status.taskSource` 回到 `tasks_source.json`。不能再沿用旧文档里“backend_api_export 已是当前主视图”的口径。

### 3.3 数据面

- backend API：18 条任务，状态为 `Done=3 / Cancelled=14 / Zhongshu=1`
- `data/tasks_source.json`：16 条任务，状态为 `Review=1 / Menxia=1 / Zhongshu=1 / Done=12 / Assigned=1`
- `data/live_status.json`：`taskSource=tasks_source.json`，`taskSourceMeta={}`，layers 为 `runtime=1 / governanceSample=5 / jjcArchive=35`

结论：当前三面不一致。

## 4. 本机 overlay 分层已落地

新目录：

- `/root/.openclaw/workspace/edict/overlays/edict/README.md`
- `/root/.openclaw/workspace/edict/overlays/edict/layer0-upstream-baseline/file-inventory-20260508.md`
- `/root/.openclaw/workspace/edict/overlays/edict/layer5-tests-verification/reality-sync-20260508.md`

分层定义：

| 层 | 用途 |
|---|---|
| layer0-upstream-baseline | 官方基线、文件清单、逐文件阅读摘要 |
| layer1-content-docs | 文档、交付稿、主板、治理说明 |
| layer2-runtime-overrides | host-native/systemd/scripts/OpenClaw 运行态覆盖 |
| layer3-backend-governance | backend API、状态机、PendingConfirm、dispatch/orchestrator |
| layer4-frontend-ui | React/Vite UI、本机新增面板和构建产物 |
| layer5-tests-verification | 测试、验证账本、现实审计 |
| upgrade-patches | 未来最小 patch 队列 |

## 5. 本机魔改优先级

### P0：保命层

升级官方版前必须保护，误回归会直接影响现网：

- `dashboard/server.py`
- `dashboard/court_discuss.py`
- `edict/backend/app/api/tasks.py`
- `edict/backend/app/api/legacy.py`
- `edict/backend/app/models/task.py`
- `edict/backend/app/services/task_service.py`
- `edict/backend/app/services/notification_service.py`
- `edict/backend/app/workers/dispatch_worker.py`
- `edict/backend/app/workers/orchestrator_worker.py`
- `scripts/run_loop.sh`
- `scripts/refresh_live_data.py`
- `scripts/sync_from_openclaw_runtime.py`
- `scripts/sync_governance_samples.py`
- `scripts/rebuild_task_views.py`
- `scripts/export_backend_tasks_to_legacy_json.py`
- `scripts/guard_openclaw_sessions.py`
- `scripts/doctor_edict.sh`

### P1：运维与可回滚层

- `deploy/`
- `scripts/manage_backend_infra.sh`
- `scripts/run_backend_component.sh`
- `scripts/run_backend_migrations.sh`
- `scripts/setup_backend_runtime.sh`
- `docs/current-progress-board.md`
- `docs/closeout.md`
- `docs/governance-upgrade-map.md`
- `docs/review-correction-notes.md`
- `docs/state/verification-ledger.json`
- `docs/state/feature-status.json`

### P2：交付沉淀层

- `docs/JJC-20260416-001-sansheng-governance-executable-review.md`
- `docs/JJC-20260416-001-task-division-plan.txt`
- `docs/backend-host-native-productionization.md`
- `docs/openclaw-feishu-p2p-hotfix.md`
- `docs/exec-plans/`
- `docs/plans/`
- `docs/templates/`

## 6. 当前验证证据

### 6.1 通过项

- Python compile：关键 dashboard/scripts/backend 文件通过。
- 前端构建：`cd edict/frontend && npm run build` 通过，生成：
  - `dashboard/dist/assets/index-DTF-vrkR.js`
  - `dashboard/dist/assets/index-CmV35B_1.css`
- 服务健康：dashboard/backend/deep health 均 ok。

### 6.2 未通过项

目标 pytest 组合：

- 结果：`63 passed, 11 failed`
- 失败文件：集中在 `tests/test_server.py`
- 失败类型：
  1. 解释器路径预期与生产实际不一致；
  2. PendingConfirm 通知标记未按测试预期写回；
  3. taizi/shangshu main-session guard 预期与当前 queued/wake 行为不一致；
  4. dual-mode fallback 路径不符合旧测试预期；
  5. create-task 的 `_FakeNow` monkeypatch 与当前实现不兼容。

所以当前不能宣称测试全绿，也不能宣称本机 edict 已完全收口。

## 7. 提升方案

### 第一阶段：把 overlay 做实

1. 把 P0/P1/P2 文件逐个归入 overlay manifest。
2. 对 P0 文件生成最小 patch，不整文件覆盖。
3. 为每个 patch 写清：来源、目的、触碰文件、回放顺序、验证命令。

### 第二阶段：先修 reality gaps

优先修：

1. 三面一致性：确认 `EDICT_ENABLE_BACKEND_EXPORT=false` 是临时状态还是应恢复 true。
2. dual-mode fallback：决定生产行为正确还是测试预期正确。
3. main-session guard：明确 taizi/shangshu 在 dashboard auto-dispatch/wake 下应该 suppress 还是 queue。
4. PendingConfirm 通知：统一 backend/dashboard 两条路径的 notifications 标记。
5. 测试 rebaseline：把 11 个失败测试逐项改成当前生产事实，或修代码回到既定制度。

### 第三阶段：建立 edict 官方升级 replay

新增脚本建议：

- `overlays/edict/scripts/replay-official-overlay.sh`

行为：

1. 从 `cft0808/edict` 官方 main 新建 clean worktree；
2. 应用 P0/P1/P2 patch；
3. 跑 Python compile；
4. 跑前端 build；
5. 跑目标 pytest；
6. 跑最小 runtime smoke；
7. 输出可回放日志。

### 第四阶段：再吸收上游

只吸收低风险高价值项：

- 环境兼容；
- 安全修复；
- 前端纯展示修复；
- 测试基础设施；
- 不覆盖本机 backend/dispatch/dashboard 生产主链。

## 8. 可交付收口清单

| 项 | 当前状态 | 产物/证据 |
|---|---|---|
| 上游文件清单 | 已形成首版 | `overlays/edict/layer0-upstream-baseline/file-inventory-20260508.md` |
| 本机运行态审计 | 已形成首版 | `overlays/edict/layer5-tests-verification/reality-sync-20260508.md` |
| overlay 分层 | 已落地首版 | `overlays/edict/README.md` |
| 正式提升方案 | 已落地 | 本文件 |
| 主板回写 | 已执行 | `docs/current-progress-board.md` |
| Python compile | 通过 | 本轮命令输出 |
| 前端 build | 通过 | 本轮命令输出 |
| 目标 pytest | 未通过 | `63 passed / 11 failed` |
| 三面一致性 | 未收口 | backend=18, tasks_source=16, live_status meta empty |
| 官方升级 replay 脚本 | 待实现 | 建议放 `overlays/edict/scripts/replay-official-overlay.sh` |

## 9. 下一步执行顺序

1. 生成 P0 overlay manifest 和 patch 草案。
2. 修/重基 11 个失败测试，先不要碰业务主链。
3. 明确 loop export flag 的目标态：如果要恢复 backend export，就先备份 unit 和 data，再最小回切并验证。
4. 补 `replay-official-overlay.sh`。
5. 用 clean upstream + P0/P1/P2 overlay 跑一次完整 replay。
