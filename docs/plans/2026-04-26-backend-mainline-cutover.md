# edict backend 主链切换实施方案

> **For Hermes:** Use `writing-plans` / `test-driven-development` / `subagent-driven-development` skills if this plan enters implementation.

**Goal:** 在不打断当前 dashboard 可见性与 agent 任务更新能力的前提下，把 edict 主现场从 JSON 看板链路逐步切到 backend(Postgres + Redis) 主链。

**Architecture:** 不能直接把现网 `scripts/kanban_update.py` 一把替换成现成 API wrapper，也不能只切 agent 入口而不管前台。正确顺序应是：先拆出 legacy JSON 实现，再补 API-first 入口与测试，再提供前台/兼容出口的双写或镜像能力，最后再切默认入口并做真实 smoke。

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy async, Redis Streams, systemd, edict dashboard(stdlib server), legacy JSON files.

---

## 0. 已确认的现实约束

1. backend 常驻链已好：
   - `edict-backend-api.service`
   - `edict-backend-outbox-relay.service`
   - `edict-backend-orchestrator.service`
   - `edict-backend-dispatch.service`
   - `edict-backend-infra.service`
2. 但当前主现场还在 JSON：
   - `edict-loop.service -> scripts/run_loop.sh 15 120`
   - `dashboard/server.py::load_tasks()/save_tasks()` 直接读写 `data/tasks_source.json`
   - `scripts/sync_agent_config.py` 会把各 workspace 的 `scripts/kanban_update.py` symlink 到项目根 `scripts/kanban_update.py`
3. backend 当前没有现成的 JSON mirror 写回：
   - `GET http://127.0.0.1:18000/api/tasks` 当前为 `count=0`
   - `data/tasks_source.json` 当前仍为前台主出口
4. 现成 API wrapper 还不完整：
   - `edict/scripts/kanban_update_edict.py` 只覆盖 `create/state/flow/done/block/progress/todo`
   - legacy 还额外有 `autopsy/confirm/delegate/delegate_result/memory/task_memo/shared_memo`
5. 所以**绝不能**直接把根 `scripts/kanban_update.py` 替成现成 wrapper；否则会丢命令，且可能把前台与 backend 裂成两套账。

---

## 1. 切换原则

1. **先保兼容，再切默认。**
2. **任何一步都必须可回滚。**
3. **先补测试，再动生产入口。**
4. **切 agent 入口之前，必须先解决前台可见性问题。**
5. **现阶段最稳的是 dual-write / mirror 过渡，不是一刀切纯 API。**

---

## 2. Phase A：拆分 legacy 实现，给入口切换腾挪空间

### Task A1：冻结当前纯 JSON 实现

**Objective:** 把当前根 `scripts/kanban_update.py` 的纯 JSON 逻辑原样沉淀为可独立导入的 legacy 模块，避免后面入口切换时递归 fallback。

**Files:**
- Create: `scripts/kanban_update_legacy.py`
- Modify: `scripts/kanban_update.py`
- Test: `tests/test_kanban.py`
- Test: `tests/test_kanban_update_entrypoint.py` (new)

**Implementation notes:**
- `scripts/kanban_update_legacy.py` 初始内容应尽量等于当前根 `scripts/kanban_update.py`。
- `tests/test_kanban.py` 若直接 import `kanban_update`，要明确改成 import legacy 模块，保证原有 JSON 行为回归测试仍测到真实 legacy 实现。
- 新增入口测试文件只测“根入口分发与 fallback”，不要把 legacy 行为测试混进来。

**Verification:**
- `pytest tests/test_kanban.py -q`
- 预期：legacy 现有行为测试仍全绿。

**Status (2026-04-26 21:5x 北京时间):**
- 已落地 `scripts/kanban_update_legacy.py`，当前先按“冻结快照”方式保留纯 JSON 实现。
- 已新增 `tests/test_kanban_phase_a_groundwork.py`，覆盖：
  - legacy 模块存在且导出核心命令
  - API wrapper fallback 优先 legacy 模块
- 已实跑：
  - `python3 -m pytest tests/test_kanban.py tests/test_kanban_update_edict.py tests/test_kanban_phase_a_groundwork.py -q`
  - `python3 -m pytest tests/test_state_machine_consistency.py tests/test_sync_symlinks.py -q`
  - `python3 -m py_compile scripts/kanban_update.py scripts/kanban_update_legacy.py edict/scripts/kanban_update_edict.py`
  当前结果全绿。

### Task A2：让根入口只负责分发

**Objective:** 把根 `scripts/kanban_update.py` 改为“API-first / legacy-fallback 入口壳”，而不是继续承载全部 JSON 细节。

**Files:**
- Modify: `scripts/kanban_update.py`
- Reuse/reference: `edict/scripts/kanban_update_edict.py`
- Test: `tests/test_kanban_update_entrypoint.py`

**Implementation notes:**
- 根入口优先复用 `edict/scripts/kanban_update_edict.py` 的 API 探测与 HTTP 调用逻辑。
- fallback 目标必须是 `scripts/kanban_update_legacy.py`，不能再 fallback 回根 `scripts/kanban_update.py` 自己。
- 对 wrapper 目前未实现的命令：
  - `autopsy`
  - `confirm`
  - `delegate`
  - `delegate_result`
  - `memory`
  - `task_memo`
  - `shared_memo`
  先明确走 legacy fallback，不能静默丢弃。

**Verification:**
- 新增测试要覆盖：
  1. API 健康探测通过时，`create/state/progress/todo` 走 API
  2. API 失败/404 时，回退 legacy
  3. `autopsy/confirm/...` 等未实现命令直接走 legacy
  4. fallback 不递归

**Status (2026-04-26 22:2x 北京时间):**
- groundwork 已完成：`scripts/kanban_update_legacy.py` 已落地，`edict/scripts/kanban_update_edict.py::_fallback_json()` 现在会优先加载 `scripts/kanban_update_legacy.py`。
- 根 `scripts/kanban_update.py` 也已完成入口壳改造：
  - import 期直接承接 legacy 源码命名空间，保证旧测试/旧 monkeypatch（如直接改 `TASKS_FILE`）不失效；
  - CLI 默认仍走 legacy；
  - 仅在显式设置 `EDICT_KANBAN_ENTRY_MODE=api/auto/json` 时，才转发到 `edict/scripts/kanban_update_edict.py`。
- 新增并实跑通过：
  - `tests/test_kanban_entry_shell.py`
  - `tests/test_kanban_update_edict.py`
  - `tests/test_kanban_autopsy.py`（补齐临时 `EDICT_HOME` 下 legacy 依赖）
  - 合并相关回归：`49 passed`
- 这一步仍然**没有切现网默认行为**；只是把后续主链切换需要的壳、fallback 与兼容测试先垫平。

---

## 3. Phase B：先解决“前台可见性”，再切 agent 默认写路径

### Task B1：确定过渡策略，只能二选一

**Objective:** 在切 agent 默认入口前，先解决“backend 成功写入后前台怎么看到”的问题。

**可选策略 A：wrapper dual-write（更小步）**
- agent 侧成功写 backend 后，同时维护 legacy JSON 出口
- 优点：改动集中在入口层，先不大动 dashboard
- 缺点：状态一致性复杂；尤其 `dashboard / create-task` 仍是 JSON-only 时，backend 可能找不到对应 legacy 任务

**可选策略 B：dashboard/server.py 引入 backend adapter（更正统）**
- `create/review/dispatch/progress/todos` 逐步改走 backend
- `tasks_source.json` 退化为兼容导出层，而不是主写路径
- 优点：长期结构更对
- 缺点：一次改动面更大

**当前建议：**
- 先做 **B + 兼容导出**，不要只做 A。
- 原因：只改 agent 入口无法覆盖 dashboard 手工建任务与审批入口，生产主线仍会裂。

### Task B2：补 backend -> 前台兼容导出层

**Objective:** 让前台在尚未完全改造前，仍能从熟悉的兼容出口读取，但底层源头改成 backend。

**Files:**
- Create: `scripts/export_backend_tasks_to_legacy_json.py` 或等价模块
- Modify: `scripts/run_loop.sh`
- Modify: `scripts/refresh_live_data.py`
- Modify: `dashboard/server.py`（如需读取导出层元信息）
- Test: `tests/test_export_backend_tasks_to_legacy_json.py` (new)

**Implementation notes:**
- 导出脚本至少要把 backend 任务映射回当前前台仍依赖的关键字段：
  - `id`
  - `title`
  - `state`
  - `org`
  - `official`
  - `now`
  - `flow_log`
  - `progress_log`
  - `todos`
  - `pending_confirm`
  - `gate_checks`
  - `review_round`
  - `autopsy`
  - `memory_extracted`
  - `templateId/templateParams/targetDept`
- 该导出层是过渡层，不应反向覆盖 backend。
- `refresh_live_data.py` / `live_status.json` 要能标识当前任务源来自 backend export，而不是继续伪装成历史纯 JSON 主源。

**Verification:**
- 先写一个 backend 样本任务到测试数据库
- 跑导出脚本
- 断言导出的 `tasks_source.json` 保留关键治理字段

**Status (2026-04-26 22:3x 北京时间):**
- 已新增 `scripts/export_backend_tasks_to_legacy_json.py`：
  - 拉取 `GET /api/tasks?limit=200`
  - 复用 backend API 已给出的兼容字段，导出到 `data/tasks_source.json`
  - 额外写 `data/tasks_backend_export_meta.json`，记录 `taskSource=backend_api_export / backendUrl / count / exportedAt`
  - fetch 失败时返回非 0，且**不会覆盖现有 `tasks_source.json`**
  - backend 返回空任务列表时，默认也**不会覆盖现有 `tasks_source.json`**；只有显式设置 `EDICT_BACKEND_EXPORT_ALLOW_EMPTY=true` 才允许导出空结果
- `scripts/refresh_live_data.py` 已能透传上述导出来源，写入 `live_status.json.taskSource/taskSourceMeta`，便于前台和排障时识别“当前 tasks_source 到底是不是 backend 导出的”。
- 已新增并实跑通过：
  - `tests/test_export_backend_tasks_to_legacy_json.py`
  - `tests/test_refresh_live_data_layers.py`
  - `tests/test_backend_export_flag_wiring.py`
- **仍未做：**
  - 没有默认启用覆盖
- 现状已前进一步：`run_loop.sh` 与 `install.sh` 里都已经把 backend export 接成**显式 feature flag**，只有设置 `EDICT_ENABLE_BACKEND_EXPORT=true` 时才会跑 `export_backend_tasks_to_legacy_json.py`；默认仍走原有 JSON 聚合链，不影响现网。
- 原因不是忘了开，而是当前现场 backend `GET /api/tasks` 仍为空；若直接默认开启，会把前台兼容出口覆盖成 0 任务。现脚本已额外带 `EDICT_BACKEND_EXPORT_ALLOW_EMPTY` 保护，默认空结果也不会覆盖。

### Task B3：把 dashboard 写路径逐步改到 backend

**Objective:** 先把产品层最关键的前台写入口切过去，再考虑是否完全废弃 JSON 直写。

**Files:**
- Modify: `dashboard/server.py`
- Possible create: `dashboard/backend_task_client.py`
- Test: `tests/test_server.py`

**写入口优先级：**
1. `/api/create-task`
2. `/api/review-action`
3. `/api/dispatch-task`
4. `/api/advance-state`
5. `/api/task-progress`
6. `/api/task-todos`

**Implementation notes:**
- 不要在 `server.py` 里到处散落 `urllib.request`；提一个小 client/adaptor，便于切换 `json|dual|api` 模式。
- 模式建议：
  - `json`：完全旧模式
  - `dual`：backend 为主，失败可回退/并保留兼容导出
  - `api`：纯 backend
- 先让测试证明 `dual` 模式可用，再考虑上 `api`。

**Verification:**
- 先新增 failing tests，覆盖：
  - dashboard create-task 在 `dual` 模式下会调用 backend client
  - backend 成功后，兼容导出层可被前台读取
  - backend 失败时行为明确（回退或报错，不能静默）

---

## 4. Phase C：再切 workspace 默认入口

### Task C1：让 workspace 默认 `scripts/kanban_update.py` 走新入口壳

**Objective:** 在 dashboard 写路径与兼容导出层都稳住后，再把 workspace 默认入口切成 API-first。

**Files:**
- Modify: `scripts/kanban_update.py`
- Verify: `scripts/sync_agent_config.py`
- Test: `tests/test_kanban_update_entrypoint.py`

**Implementation notes:**
- 由于 `sync_agent_config.py` 已经把 workspace `kanban_update.py` symlink 到根脚本，这一步不需要额外改 workspace 分发策略；只要根脚本安全切换即可。
- 但必须确保：
  - 未实现命令继续 fallback 到 `kanban_update_legacy.py`
  - backend 404/500 时回退策略符合预期
  - 日志里能看出当前走的是 API 还是 legacy

### Task C2：补切换开关与回滚开关

**Objective:** 让主链切换具备现场可控性，而不是靠改源码回滚。

**Files:**
- Modify: `scripts/kanban_update.py`
- Modify: `dashboard/server.py`
- Modify: `/etc/edict/backend.env`（若最终采用环境变量控制）
- Docs: `docs/backend-host-native-productionization.md`

**Suggested flags:**
- `EDICT_TASK_BACKEND_MODE=json|dual|api`
- `EDICT_KANBAN_FORCE_LEGACY=1`
- `EDICT_EXPORT_BACKEND_TO_JSON=1`

**Verification:**
- `json` 模式：全旧链路仍通
- `dual` 模式：backend 有数据，前台仍可见
- `api` 模式：前台与 workspace 都能完全靠 backend 工作
- 强制 legacy 开关：现场一键回退可用

---

## 5. Phase D：真实 smoke 与收口标准

### Task D1：最小真实链 smoke

**Objective:** 用真实服务验证“创建 -> 流转/进度 -> todos -> 审批/完成 -> 前台可见”闭环。

**Smoke steps:**
1. 创建一个临时任务（legacy id 明确）
2. 更新 progress
3. 更新 todos
4. 做一次状态流转
5. 若链路支持，再做一次 `PendingConfirm -> approve/reject`
6. 确认：
   - backend `GET /api/tasks` 中能看到该任务
   - 前台兼容出口仍能看到同一任务
   - `live_status.json` 指向的新口径正确
7. 清理 smoke 数据

### Task D2：主线收口标准

**只有同时满足下面几条，才能说“主现场已切 backend 主链”：**

- backend 常驻链 active 且健康检查稳定
- dashboard 关键写入口默认走 backend
- workspace 默认 `kanban_update.py` 已是 API-first 入口壳
- legacy-only 命令仍能安全 fallback
- 前台可见性不再依赖人工维护的 JSON 主写路径
- 至少一轮真实 smoke 证明 backend `count > 0`
- 文档已明确：
  - backend 已是主写链
  - JSON 仅剩兼容导出/只读过渡用途（若仍保留）

---

## 6. 风险清单

1. **命令覆盖不全风险**
   - 直接替换根脚本会丢 `autopsy/confirm/...` 等命令
2. **双账本风险**
   - agent 先切 API，但 dashboard 仍只认 JSON
3. **404 回退误判风险**
   - backend 尚无 legacy task 映射时，wrapper 可能频繁 fallback，看似“没坏”，实则没切成
4. **治理字段丢失风险**
   - backend -> JSON 导出若字段映射不全，会把 `pending_confirm/gate_checks/autopsy/...` 冲没
5. **回滚能力不足风险**
   - 没有环境开关就直接切默认，现场出问题只能再发版改代码

---

## 7. 推荐实施顺序（最小可逆）

1. **先做测试与 legacy 拆分**
2. **再做根入口壳**（但默认仍可保持 legacy）
3. **先补 backend -> 前台兼容导出层**
4. **再改 dashboard 写入口到 dual 模式**
5. **最后才切 workspace 默认入口**
6. **真实 smoke 通过后，再讨论纯 API 模式**

---

## 8. 本轮建议结论

- **可以继续推进。**
- 但下一刀不该直接砍 `scripts/kanban_update.py` 上线。
- 最稳的下一步实现项应该是：
  1. 先拆 `scripts/kanban_update_legacy.py`
  2. 给根入口补测试与 fallback 去递归保护
  3. 同时设计 backend -> JSON 兼容导出脚本

这三件做完，才有资格进入真实主链切换。