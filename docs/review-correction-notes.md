# review correction notes

更新时间：2026-05-05 11:06（北京时间）

## 2026-05-05 复查补记：按主板要求对文字层 / 代码层 / DB层 / dry-run 产物层 / runtime 层做现场核实

这轮不是泛读代码，而是按 `docs/current-progress-board.md` 里 A6-5、2.5.1 的口径，直接对 edict 现网做五层复查，并专门核实“任务是否还能真实派发进 edict”。

先说总结：

> **edict 不是完全不可用，任务派发链也不是全断。当前现场仍能看到任务被自动派发进 `zhongshu`，并且 runtime 会话里已经推进到 `Menxia`。但系统稳定性并未收口：主板宣称过的若干“已切回 tasks_source / 已去掉 backend export 误报 / 三层视图已对齐”的结论，在 2026-05-05 这次现网复查下并不完全成立；当前最突出的现实问题是主视图、runtime 视图、governance sample、backend live-status 四层仍有状态脱节。**

---

### 1. 文字层核实：主板当前口径与现网存在明显偏差

本轮先按主板指定章节复查：
- `A6-5. 阿爪执行清单（2026-04-29 再完善版）`
- `2.5.1 2026-04-29 再完善版收口`
- 以及 2026-05-02 / 2026-05-03 / 2026-05-04 的后续收口记录

主板里有几条关键口径，和今天现网不完全一致：

#### 1.1 “live_status 已回到 tasks_source.json、taskSourceMeta={}” 这条，今天现网不成立
本轮现场直读：
- `data/live_status.json`
  - `taskLayers = {'runtimeCount': 2, 'governanceSampleCount': 5, 'jjcArchiveCount': 35}`
  - **`taskSource = backend_api_export`**

这和主板 2026-05-03 16:57 那条“已回退为真实 `taskSource=tasks_source.json`、`taskSourceMeta={}`”的收口口径冲突。

#### 1.2 `tasks_source.json` 当前仍大量保留 `sourceLayer=backend_export`
本轮直读 `data/tasks_source.json`，18 条任务中尾部样本可见多个：
- `sourceLayer = backend_export`
- 如：
  - `766435df-8ea9-4f9d-865e-cd12c5571901`
  - `33b3c181-2566-4c0a-aab6-0f849319a0c4`
  - `2bc15cc5-0f0a-4a41-bcbd-0e24357d5d65`
  - `0d018beb-fd10-463b-882c-77779a25a486`
  - `a38d3eab-415d-4e08-8109-e8f84ca7fce6`

这说明“backend export 只是一段历史、现网主视图已经完全摆脱它”的口径，现在不能继续直接沿用。

#### 1.3 “三层分离已稳定收口”只能算部分成立，不能再表述成完全对齐
今天现场四层数据同时存在：
- `tasks_source.json`：18 条
- `tasks_runtime_view.json`：2 条
- `tasks_governance_samples.json`：5 条
- `live_status.json`：18 条（但 `taskSource=backend_api_export`）

数量上看，系统还在跑；但**同一任务在不同层的状态不一致**，说明“三层分离”不是没做，而是**做了但仍未稳态对齐**。

---

### 2. 代码层核实：派发、回写、聚合、runtime 桥接几条关键代码都还在

本轮直接 grep 了现场关键入口，确认下面几段真实存在：

#### 2.1 dashboard 侧自动派发链仍在
- `dashboard/server.py`
  - `dispatch_for_state(...)`
  - `handle_scheduler_scan(...)`
  - `startup-recovery`
  - `taizi-scan-retry`
  - `manual-dispatch`

说明 edict 当前不是“没有派发代码”，而是**派发链仍在运行**。

#### 2.2 backend 回写链代码仍在
- `edict/backend/app/workers/dispatch_worker.py`
  - `await svc.add_progress(task_id, agent, sanitized_stdout or raw_stdout)`
  - `task.output = raw_stdout`
- `edict/backend/app/services/task_service.py`
  - `review_action(...)`
  - `add_progress(...)`
  - `task.output = comment`

所以从代码结构上看：

> **“agent 输出 / review 结论自动回写任务本体”这条修法并没有丢。**

#### 2.3 runtime / governance / live-status 三层脚本都还在参与现网
以下脚本都还在现场代码里：
- `scripts/sync_from_openclaw_runtime.py`
- `scripts/sync_governance_samples.py`
- `scripts/rebuild_task_views.py`
- `scripts/refresh_live_data.py`
- `scripts/export_backend_tasks_to_legacy_json.py`
- `scripts/run_loop.sh`

这说明当前 edict 不是单纯 backend API 单面在跑，而是仍然依赖**多层同步 + 聚合 + 导出**的混合运行态。

---

### 3. DB 层核实：backend API 和 worker 进程都活着，任务也确实在 backend 里

本轮现场进程核实到：
- backend API：
  - `/root/.openclaw/workspace/edict/.venv-edict-backend/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 18000`
- workers：
  - `app.workers.outbox_relay`
  - `app.workers.orchestrator_worker`
  - `app.workers.dispatch_worker`
- dashboard loop：
  - `scripts/run_loop.sh 15 120`

并且直接访问：
- `GET http://127.0.0.1:18000/api/tasks/live-status` → **200 OK**
- `GET http://127.0.0.1:18000/api/tasks?limit=5` → **200 OK**

其中 `live-status` 返回的任务 `bbbf369f-959b-484e-890d-9c28d56b748a`（`OpenClaw 飞书直聊稳定性监控`）可见：
- `state = Zhongshu`
- `flow_log` 里确实有：
  - `Taizi -> Zhongshu`
- 但仍有：
  - `progress_log = []`
  - `output = ""`

这说明：

> **backend 不是死的，任务实体也不在“只存在 legacy JSON、不在 backend”那种假活状态。backend 里有真实任务、真实状态推进记录。**

但也同时说明：

> **不是所有任务在推进后都会立刻沉淀出 `progress_log / output`，所以“回写链已补”不能直接等价成“现网所有任务都有沉淀结果”。**

---

### 4. dry-run / 产物层核实：主板宣称的测试文件都在，但现场虚拟环境缺 pytest，不能假装已跑绿

本轮按主板与 review notes 提到的最关键回归点，尝试执行：
- `tests/test_dispatch_output_persistence.py`
- `tests/test_backend_review_action.py`
- `tests/test_refresh_live_data_layers.py`
- `tests/test_sync_from_openclaw_runtime.py`
- `tests/test_rebuild_task_views.py`
- `tests/test_sync_governance_samples.py`

现场实际结果：
- `/usr/bin/python3: No module named pytest`
- `/root/.openclaw/workspace/edict/.venv-edict-backend/bin/python: No module named pytest`

所以这一层的准确口径只能是：

> **测试文件仍在仓里，说明相关修法没有被直接删掉；但当前这台现场运行环境里，系统 Python 和 `.venv-edict-backend` 都缺 pytest，本轮无法原地复跑这些回归测试。任何“今天已再次跑绿”的表述都不成立。**

这点必须直说，不能拿旧文档里的 `passed` 结果冒充今天的现网复核结果。

---

### 5. runtime 层核实：今天拿到了“任务真实被派发进 edict”的硬证据，但也同时坐实了视图脱节

这是本轮最关键的核实点。

#### 5.1 今天现网仍在自动派发任务进 zhongshu
`journalctl -u edict-dashboard.service --since '2026-05-05 10:58:00'` 现场证据：
- `10:59:11 [server] 🚀 bbbf369f-959b-484e-890d-9c28d56b748a 推进后自动派发 → zhongshu`
- `10:59:11 [server] 🔄 自动派发 ... → zhongshu (第1次)...`
- `10:59:15 [server] ✅ ... 自动派发成功 → zhongshu`
- `11:01:11 [server] 🚀 ... 推进后自动派发 → zhongshu`
- `11:01:16 [server] ✅ ... 自动派发成功 → zhongshu`

这已经足够说明：

> **“edict 当前无法派发任务”这类绝对化结论，今天现网不成立。至少对 `zhongshu` 这条链路，任务仍能真实派发并拿到 success 回执。**

#### 5.2 openclaw-gateway 侧也有对应回执痕迹
`openclaw-gateway.service` 的 status 输出里已出现：
- `最新状态更新回执：✅ ... 状态更新: Zhongshu → Menxia`
- `最新看板进展回执：... 当前仍在等待门下审议链路恢复...`

这说明：
- 不是只有 dashboard 自己写日志自嗨；
- **OpenClaw runtime / 会话侧也确实收到了该任务的推进回执。**

#### 5.3 但同一任务在不同层出现了明显脱节
同一任务 `bbbf369f-959b-484e-890d-9c28d56b748a` 本轮直读结果：

- `tasks_source.json`
  - `title = OpenClaw 飞书直聊稳定性监控`
  - `state = Zhongshu`
  - `org = 中书省`
  - `sourceLayer = backend_export`
  - `now = 批量推进：修正持久化后重新分拣`

- `tasks_runtime_view.json`
  - `taskId = bbbf369f-...`
  - `sessionKey = agent:zhongshu:edict-dispatch`
  - `state = Menxia`
  - `org = 门下省`
  - `now = 思考中: 已接旨`

- `tasks_governance_samples.json`
  - **根本找不到这条任务**

- `live_status.json`
  - 又回到了和 `tasks_source.json` 一样的：
    - `state = Zhongshu`
    - `org = 中书省`
    - `sourceLayer = backend_export`

这组证据已经把问题钉得很死：

> **任务确实在派发、会话也确实在推进，但主视图没有稳定吃到 runtime 推进态；governance sample 对这条任务甚至没跟上。这说明当前最大问题不是“任务派不出去”，而是“派出去以后，多层视图没有稳定收敛到同一状态”。**

---

### 6. 这轮对 edict 可用性 / 稳定性的复查结论

#### 6.1 可用性结论
- **可用，但不是稳态可用。**
- backend API 活着；dashboard 活着；workers 活着；run_loop 活着。
- 至少 `Taizi/Zhongshu` 方向的自动派发，今天仍然能看到真实成功证据。
- runtime 侧也能看到任务继续推进到 `Menxia`。

所以不能把 edict 定性成“已经完全瘫痪”。

#### 6.2 稳定性结论
- **稳定性仍未收口，且主问题已经非常明确：多层状态脱节。**
- `tasks_source.json` / `tasks_runtime_view.json` / `tasks_governance_samples.json` / `live_status.json` 对同一任务不能稳定一致；
- `live_status.taskSource` 今天仍是 `backend_api_export`，和此前“已切回 tasks_source”口径冲突；
- runtime 推进到了 `Menxia`，但 source/live-status 仍停在 `Zhongshu`；
- governance sample 对同一任务缺席，说明它不是稳定的治理沉淀层。

#### 6.3 这次最该更新的值守口径
以后再看 edict 现场，不要再用这种二元化说法：
- “派发链断了 / 没断”
- “backend 活了 / 死了”
- “任务有 / 没有被处理”

更准确的当前口径应改成：

> **任务派发链还能跑，backend 也还活着；但任务推进后的多层收敛不稳定，主视图经常落后于 runtime，会导致可见性、调度判断和稳定性判断都失真。**

---

### 7. 这轮复查后，下一步最优先要盯的不是“能不能派”，而是“派后怎么收敛”

按今天证据，下一步优先级应是：
1. **先修主视图收敛**：为什么 `tasks_runtime_view` 已到 `Menxia`，`tasks_source/live_status` 还在 `Zhongshu`；
2. **再查 governance sample 缺席**：为什么同一任务 runtime 有、source 有、sample 没有；
3. **最后才谈更多自动派发链验收**：因为当前主要矛盾不是“发不出去”，而是“发出去以后各层认知不一致”。

一句话收口：

> **这轮复查已经证明 edict 还能派发，但也同时证明它还没稳到可以把多层状态当成同一事实源来信。现阶段最大风险不是完全不可用，而是“看起来在跑、实际上每层看到的不是同一个任务现实”。**

---

## 这次纠偏的核心结论

这不是“任务设计上就不回写结果”的问题。

更准确的定性是：
- **主链里一直有回写入口**：
  - `POST /tasks/{task_id}/progress` → `TaskService.add_progress()`
  - `transition_state()` 会回写 `flow_log / meta.gate_checks / meta.memory_extracted`
  - `review_action()` 会推进状态并留下 review / gate 痕迹
- **但执行链缺了自动回填任务本体这一步**：
  - `dispatch_worker` 原先只负责派发、收集 agent stdout、发布 `agent.output`
  - 它原本**没有**把 agent 输出自动写回 `task.output` 或 `progress_log`
  - 所以现场会出现：任务已经 `Assigned` / 甚至 agent 已经跑完，但任务本体还像“只派出去了、没沉淀结果”

一句话收口：

> **不是没有回写能力，而是缺了“agent 输出 / 复核结论 → 自动落回任务本体”的收口动作。**

---

## 我这次实际补了什么

### 1. dispatch 输出自动回填
文件：`edict/backend/app/workers/dispatch_worker.py`

补法：
- agent 成功返回后，除了继续发布 `agent.output` 事件
- 还会自动：
  - 调 `TaskService.add_progress(task_id, agent, stdout)`
  - 把 stdout 摘要写进 `progress_log.text` / `task.now`
  - 在成功场景把完整 stdout 写入 `task.output`

效果：
- 不再只是事件流里“看见输出”
- 任务本体本身也能看到结果沉淀

### 2. progress 回写补摘要
文件：`edict/backend/app/services/task_service.py`

补法：
- `add_progress()` 增加摘要逻辑
- 现在每次写 progress 时会同步：
  - 保留原始 `content`
  - 生成短摘要 `text`
  - 刷新 `task.now`

效果：
- 前端 / 看板不必自己猜最近进展
- `progress_log` 的结构也和现有消费侧更一致

### 3. review 结论不再只改状态
文件：`edict/backend/app/services/task_service.py`

补法：
- `review_action()` 在 approve / reject 后
- 会追加一条 `progress_log`
  - 形如：`review:approve · ...` / `review:reject · ...`
- 若审批通过且任务进入 `Done`
  - 同步把正式 review comment 写入 `task.output`

效果：
- review 不再只是状态机动作
- 正式复核结论本身也能沉淀下来

---

## 本次验证

新增 / 调整测试：
- `tests/test_dispatch_output_persistence.py`
- `tests/test_backend_review_action.py`
- `tests/backend_test_env.py`

当前验证结果：

```bash
python3 -m pytest -q tests/test_backend_review_action.py
# 3 passed

python3 -m pytest -q tests/test_dispatch_output_persistence.py
# 2 passed

python3 -m pytest -q tests/test_backend_review_action.py tests/test_dispatch_output_persistence.py
# 5 passed
```

---

## 继续复核的新结论（阶段汇总）

### 1. 代码侧“自动回写链”现在已经有明确证据
- `dispatch_worker` 已有：
  - `TaskService.add_progress(...)`
  - `task.output = raw_stdout`
- `task_service.review_action()` 已有：
  - `progress_log` 追加
  - `Done` 时将 review comment 写入 `task.output`
- 相关测试已覆盖。

### 2. 18000 上跑的确实是当前仓里的 edict backend
- 监听 `127.0.0.1:18000` 的是：
  - `/root/.openclaw/workspace/edict/.venv-edict-backend/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 18000`
- cwd：
  - `/root/.openclaw/workspace/edict/edict/backend`
- 同时存在：
  - `app.workers.outbox_relay`
  - `app.workers.orchestrator_worker`
  - `app.workers.dispatch_worker`

### 3. API 直读 backend，空白不是 dashboard 单独看错文件
- 直接访问 `GET /api/tasks/live-status` 返回 `200 OK`
- 关键正式任务在 API 返回里仍然可见：
  - `Assigned`
  - `progress_log = []`
  - `output = ""`
- 甚至有 `Done` 样本也仍然：

### 4. 重复 dispatch 的 probe 已补到“不是 taizi/provider 假象”的硬证据
- taizi 的 `agent:taizi:edict-dispatch` session `353b313b-bb1b-443f-9034-a8e44a804f02` 真实存在，`updatedAt` 很新，transcript 内连续多次出现：`已在中书省，无需重复流转。`
- 已为 `scripts/sync_from_openclaw_runtime.py` 增补 transcript 状态桥：可从 toolResult / assistant 文本中识别 `状态更新: Taizi → Zhongshu`、`已在中书省` 等治理推进态，并桥接 `taskId`。
- 同时修掉 runtime 过滤误杀：此前 `should_keep_runtime_task()` 只保留 `Doing/Review/Blocked`，导致 dispatch 任务一旦真实推进到 `Zhongshu/Menxia/Assigned` 就被当成“非活跃”直接丢弃；现已对 `:edict-dispatch` 会话放宽保留规则，并补了回归测试。
- 现网复跑后：`sync_from_openclaw_runtime.py` 已从 `synced 0 tasks` 变为 `synced 4 tasks`；probe `4455998e-77ae-446c-b786-f2c476ac94ff` 已真实出现在 `tasks_runtime_view.json` 中，状态为 `Zhongshu / 中书省`，`now=思考中: 已在中书省，无需重复流转。`
- 这说明：**不是 taizi/provider 根本没处理，而是 runtime 映射层此前把真实推进态过滤掉了。**

### 5. 剩余未收口点已经收窄到“旧治理样本回流污染聚合”
- 虽然 `tasks_runtime_view.json` 已显示 probe 为 `Zhongshu / 中书省`，但 `tasks_governance_samples.json` 仍保留旧的 `Taizi / 太子` 样本。
- `rebuild_task_views.py` 聚合后，`tasks_source.json.state/org` 已能跟上 runtime 切到 `Zhongshu/中书省`，但 `updatedAt` 与 `sourceMeta.updatedAt/ageMs/outputTokens` 仍会被旧 governance sample 混回主视图。
- 所以下一刀不该再去怀疑 taizi/provider，而该去修：
  1. `sync_governance_samples.py` 如何避免把旧 `legacy_tasks_source` stale 样本继续抬回样本层；
  2. `rebuild_task_views.py` 对 `updatedAt/sourceMeta/_scheduler` 这类状态性字段的优先级与覆盖规则。
  - `progress_log = []`
  - `output = ""`

这说明：

> **不是 dashboard 单独看错文件；backend API 本体当前返回的数据也还是空白。**

### 4. 新建 probe 任务后的初始异常表象
我继续做了“全新正式任务实跑验证”，新建任务：
- `task_id = 4455998e-77ae-446c-b786-f2c476ac94ff`
- title: `[probe] 回写链现网实跑验证 2026-05-02`

最初现场轮询结果：
- 连续 8 轮（每 3 秒一次）都停在：
  - `state = Taizi`
  - `progress_log = []`
  - `output = ""`
- `flow_log` 只有一条：
  - `任务创建`

同时当时直查：
- `GET /api/events?trace_id=2a7a31e4-39a3-4bac-bc84-fcee74c06c92&limit=50`
  - 返回 `events = []`
- `GET /api/events?limit=5`
  - 也是 `events = []`

### 5. 继续往下抠后，已能排除“outbox / orchestrator 没跑通”
后续继续直查 PostgreSQL + Redis Streams 现场后，已经拿到更硬的证据：

#### 5.1 backend 实际使用的是 Postgres，不是 SQLite
- 进程环境里明确有：
  - `DATABASE_URL=postgresql+asyncpg://edict:GvIqsUtzfDd6zXxne9F5cpxYlY0ieZWZ@127.0.0.1:5432/edict`
- 因此后续排查不应再优先找本地 `.db` 文件。

#### 5.2 outbox 已真实写入且 relay 已成功发布
Postgres 现场：
- `outbox_count = 67`
- `events_count = 0`
- probe 任务 trace：`2a7a31e4-39a3-4bac-bc84-fcee74c06c92`
- 对应 outbox 记录：
  - `topic = task.created`
  - `event_type = task.created`
  - `published = True`
  - `attempts = 0`
  - `last_error = ''`
  - `published_at = 2026-05-02T09:00:06.786733+00:00`

这说明：
- **不是 outbox 没写进去**
- **不是 outbox_relay 明显报错**

#### 5.3 Redis Streams 现场确认 orchestrator 已消费并产出 dispatch request
Redis Streams 现场：
- `edict:stream:task.created`
  - `length = 23`
  - last-entry 就是 probe 任务对应的 `task.created`
  - consumer group: `orchestrator`
  - `pending = 0`
  - `lag = 0`
- `edict:stream:task.dispatch`
  - `length = 56`
  - last-entry 就是 probe 任务对应的 `task.dispatch.request`
  - `producer = orchestrator`
  - payload 中明确包含：
    - `task_id = 4455998e-77ae-446c-b786-f2c476ac94ff`
    - `agent = taizi`
    - `state = Taizi`
    - `message = 新任务已创建: [probe] 回写链现网实跑验证 2026-05-02`
  - consumer group: `dispatcher`
  - `pending = 0`
  - `lag = 0`

这一步已经能明确排除：
- `task.created(outbox)` 没发出
- `outbox_relay` 没把事件送进 Redis
- `orchestrator_worker` 没消费 `task.created`
- `orchestrator_worker` 没生成 `task.dispatch.request`

也就是说，这条链已被实锤跑到了：

> `task.created(outbox) -> outbox_relay -> Redis stream -> orchestrator_worker -> task.dispatch.request`

### 6. 因而主嫌疑点已从 `dispatch_worker` 后半段，继续收紧到 **scheduler scan + 任务聚合主视图失真**
在上一轮只看 event / worker 时，确实会把嫌疑先压到 `task.dispatch.request -> dispatch_worker -> agent call -> transition/progress/output persist` 这一段；但继续对 `dashboard/server.py`、`tasks_source.json`、`tasks_runtime_view.json`、`tasks_governance_samples.json` 与聚合脚本做对位后，现场结论需要再修正一层：

> **重复 dispatch 的直接触发器是 `handle_scheduler_scan()`；而它之所以会稳定重复触发，不是 taizi 一直没处理，也不是单纯 provider 没回，而是 `tasks_source.json` 这份主任务视图长期保留了旧状态，导致 scan 持续把同一 probe 视作“Taizi 停滞未推进”。**

更具体地说：

#### 6.1 直接触发器已定位到 `handle_scheduler_scan()`
`dashboard/server.py:2445+` 的逻辑是明确的：
- 只要任务不是终态/Blocked；
- `lastProgressAt` 距今超过阈值（默认 600s）；
- 且 `retryCount < maxRetry`；
- 就会把 `lastDispatchTrigger` 记成 `taizi-scan-retry`，写一条“停滞 N 秒，触发自动重试第 X 次”，并在循环外直接执行：
  - `dispatch_for_state(task_id, retry_task, state, trigger='taizi-scan-retry')`

这意味着：
- **重复派发不是 taizi 自己凭空再造，而是 scheduler scan 本身就在主动重派。**

#### 6.2 现场主状态为何会一直满足“停滞重派”条件
对 probe 任务 `4455998e-77ae-446c-b786-f2c476ac94ff` 现场直读 `data/tasks_source.json` 后，看到的是：
- `state = Taizi`
- `org = 太子`
- `updatedAt = 2026-05-02T09:00:06.333700+00:00`（仍是创建时刻）
- `_scheduler = {}`
- `progress_log = []`
- `flow_log` 只有“任务创建”

这等于告诉 scheduler：
- 任务自创建后一直没有任何进展；
- 因而每次扫描都非常容易被重新判成 stalled → retry。

#### 6.3 但 runtime / session / governance sample 已证明任务并非真的一直停在 Taizi
继续对位后，已拿到相反证据：
- taizi 的 `agent:taizi:edict-dispatch` session `353b313b-bb1b-443f-9034-a8e44a804f02` 中，同一旨意从 17:10 起被反复灌入；
- session 内 17:14 已出现一次真实 `kanban_update.py` 执行，把任务从 `Taizi -> Zhongshu`；
- `data/tasks_runtime_view.json` 中还能看到 19:34 左右的重复派单，以及 assistant 回的“已在中书省，无需重复流转。”；
- `data/tasks_governance_samples.json` 中已出现：
  - `已入队派发：Taizi → taizi（taizi-scan-retry）`

因此：
- **任务并不是真的完全没动；是主任务视图没有把“已推进”状态反映出来。**

#### 6.4 更深一层的根因：`rebuild_task_views.py` 的合并策略会把旧非空状态钉死
`scripts/rebuild_task_views.py` 当前会把：
- `tasks_runtime_view.json`
- `tasks_governance_samples.json`
- `tasks_jjc_archive.json`

聚合回 `tasks_source.json`。

但它的 `dedupe()` 合并规则是：
- **已有非空字段不覆盖；只有空值才补；dict 才浅更新。**

这意味着：
- 如果先进入聚合的那份任务数据已经带着旧的 `state='Taizi'`、旧 `updatedAt`、空 `_scheduler`；
- 那么后续来源即使拿着更新鲜的 `state='Zhongshu'`、更新的 `updatedAt`、新的 `_scheduler` / `progress_log`；
- 只要这些字段不是“空值”，就**不会覆盖**已有旧值。

结果就是：
- `tasks_source.json` 会长期保留一份“非空但过期”的旧状态。

#### 6.5 `sync_governance_samples.py` 又把旧 `tasks_source.json` 反向喂回样本层，放大失真
`scripts/sync_governance_samples.py` 的 source 里，除了 runtime_view 之外，还直接读取：
- `legacy_tasks_source = tasks_source.json`

这意味着：
- 旧的主任务视图本身又会反向参与治理样本合并；
- 形成“旧主状态 -> 样本层 -> 再聚合回主视图”的回流；
- 从而把本来应该被新状态纠正的字段继续固化。

#### 6.6 所以当前最接近事实的新版结论
应把之前“dispatch_worker 后半段是主嫌疑”的口径，继续修正为：

> **重复 dispatch 的直接触发器是 `handle_scheduler_scan()` 的 `taizi-scan-retry`；真正让它持续触发的深层原因，是 `tasks_source.json` 这份主状态视图因 `rebuild_task_views.py` 的“非空字段不覆盖”合并策略保留了过期任务状态，且 `sync_governance_samples.py` 又把旧主状态反向并入样本层，导致 scheduler 长期看见的仍是“Taizi / 无进展 / _scheduler 为空”的旧现场。**

这也解释了为什么会同时出现下面这组表面矛盾、实则同因的现象：
- runtime/session 里能看到任务已经被处理、甚至回“已在中书省”；
- governance sample 里能看到 `taizi-scan-retry` 痕迹；
- 但 `tasks_source.json` 却还像一条“从未推进过”的旧任务；
- 最终 scheduler 就会继续基于这份旧主状态重复重派。

### 7. 下一步最小修法建议（先定原则，不在这里直接改现场）
既然根因已经从“worker 是否执行”继续收紧到“主任务视图如何聚合”，那后续修法也应优先打在聚合策略，而不是继续盲修 taizi / provider：

#### 7.1 `rebuild_task_views.py` 不能再只按“非空优先”合并关键状态字段
对下列关键字段：
- `state`
- `org`
- `updatedAt`
- `now`
- `_scheduler`
- `progress_log`
- `flow_log`

至少应采用：
- **按时间戳更新鲜者优先覆盖**；
- 或至少为 runtime / governance_sample 设定比旧 legacy 快照更高的覆盖优先级；
- 不能再让“较早进入聚合的非空旧值”永久压住后续新值。

#### 7.2 `sync_governance_samples.py` 需要谨慎处理 `legacy_tasks_source`
当前把 `tasks_source.json` 直接当样本源，会把已经失真的主视图再次灌回样本层。后续应至少评估：
- 是否降低 `legacy_tasks_source` 的优先级；
- 或限制它只补治理字段，不反向污染 `state / org / updatedAt / _scheduler` 这类主状态字段。

#### 7.3 在根修完成前，文档与值守口径必须先改
值守时不应再把这类现象简单归因为：
- “taizi 没处理”
- “provider 没回所以任务没推进”
- “dispatch_worker 没消费到”

更准确的值守口径应改成：
- **scan 在重派；主视图在吃旧状态；runtime 与主任务源已出现状态脱节。**

### 7. `/api/events` 为空的定性也必须纠偏
当前 `events` 表为 `0`，而 Redis Streams 中又能看到真实事件流转。
这意味着：

> **`/api/events` 为空，当前更像不是“事件没发生”，而是系统缺少或未启用“Redis 事件 -> events 表”的审计持久化链。**

所以后续不能再把 `/api/events` 为空直接当作：
- outbox 没发；
- orchestrator 没消费；
- dispatch request 没生成。

它更可能只是：
- **审计落库缺口**
- 或**事件表写入链未实现/未启用**

### 8. 给玄成下一步的明确落点
玄成下一步不要再绕回 outbox / orchestrator 了，优先盯下面这条唯一主链：

> `task.dispatch.request -> dispatch_worker -> agent call -> transition/progress/output persist`

建议按这个顺序抠：
1. probe 那条 `task.dispatch.request` 被哪个 dispatcher consumer 消费；
2. `dispatch_worker` 消费后是否真的调用了 taizi agent；
3. agent 调用失败时是否有异常被吞、是否过早 ACK；
4. 是否已经执行但没有调用 `transition_state()` / `add_progress()` / `task.output` 回写；
5. 是否存在重复补发或旧调度链把现场观感搅乱。

### 9. 现有附加异常仍需保留参考，但不应再压过主嫌疑点
- taizi 的 `agent:taizi:edict-dispatch` session `353b313b-bb1b-443f-9034-a8e44a804f02` 中，任务 `4455998e-77ae-446c-b786-f2c476ac94ff` 的同一条旨意自 17:10 起被持续重复灌入，直到 19:13 仍在重复；session 中可见同一文案按 2~5 分钟节奏反复出现，而 taizi 已在 17:14 完成一次 `kanban_update.py` 把任务从 `Taizi -> Zhongshu`。
- 这说明现场还有**重复补发/调度条件未收敛**的问题。
- 但在当前证据下，主嫌疑点仍应先落在 `dispatch_worker` 消费后的执行与状态/结果回写阶段；重复补发问题属于并行异常，不应再盖过这条主链定位。

---

## 给玄成/后续接手者的短版口径

短版可以直接这么说：

> 继续复核后，已经能排除 outbox / relay / orchestrator 没跑通。Postgres 现场显示 probe 任务对应的 `task.created` 已在 `outbox_events` 中 `published=True`、`attempts=0`、`last_error=''`；Redis Streams 里也能直接看到 `edict:stream:task.created` 被 `orchestrator` group 消费，且 `edict:stream:task.dispatch` 中已有对应 `task.dispatch.request`，`dispatcher` group 同样 `pending=0`、`lag=0`。因此当前主嫌疑点已收缩到 `dispatch_worker` 消费后的执行与回写阶段：消息已经被 dispatcher 拿走，但任务本体仍停在 `Taizi`，没有出现预期的状态推进、`progress_log` 或 `output`。另外，`events` 表为 0 更像是审计持久化缺口，不能再把 `/api/events` 为空直接当成“事件没发生”。

---

## 相关文件
- `edict/backend/app/services/task_service.py`
- `edict/backend/app/workers/orchestrator_worker.py`
- `edict/backend/app/workers/dispatch_worker.py`
- `edict/backend/app/workers/outbox_relay.py`
- `edict/backend/app/services/event_bus.py`
- `edict/backend/app/api/events.py`
- `edict/backend/app/api/tasks.py`
- `edict/backend/app/main.py`
- `tests/test_dispatch_output_persistence.py`
- `tests/test_backend_review_action.py`


---

## 2026-05-05 继续复查补记：已把“为什么派发后没稳定收敛”进一步收紧到聚合与样本链

在上一轮已经确认“任务还能真实派发进 edict”之后，我继续往下抠 `rebuild_task_views.py`、`sync_governance_samples.py`、`refresh_live_data.py` 三段现场代码，并再次对位同一任务 `bbbf369f-959b-484e-890d-9c28d56b748a` 的四层数据。新的收紧结论如下。

### 1. `tasks_source.json` 当前吃不到 runtime 新状态，不是偶发现象，是聚合优先级设计使然
本轮直接读 `scripts/rebuild_task_views.py`，当前聚合顺序是：
1. `runtime_tasks` → 标记 `sourceLayer=runtime`
2. `governance_samples` → 标记 `sourceLayer=governance_sample`
3. `archive` → 标记 `sourceLayer=jjc_archive`

随后统一进 `dedupe()`。

`dedupe()` 当前的关键规则是：
- 一旦同 `task_key` 已存在，就按 `sort_key()` 推导的时间先后决定 `newer_or_equal`
- 对 `state/org/updatedAt/now/_scheduler/progress_log/flow_log/block/output` 这些 **stateful_fields**，只有当“新对象时间更新鲜或相等”时，才允许覆盖旧值
- 否则旧值保留

这意味着：

> **如果 `tasks_source` 里当前在用的 backend_export 任务带着较新的 `updatedAt`，而 runtime 任务只是会话桥接出来的较晚观察快照，但没有把更高优先级时间戳稳定抬上来，那么 runtime 的 `Menxia`/`门下省` 就不会稳定覆盖掉 source 里的 `Zhongshu`/`中书省`。**

今天这个任务现场就是这样：
- `tasks_source.json`
  - `state = Zhongshu`
  - `org = 中书省`
  - `updatedAt = 2026-05-01T09:14:30.061384+00:00`
  - `sourceLayer = backend_export`
- `tasks_runtime_view.json`
  - `state = Menxia`
  - `org = 门下省`
  - `sourceMeta.updatedAt = 1777953342866`
  - `sessionKey = agent:zhongshu:edict-dispatch`

也就是说：
- runtime 已经看到更晚的治理推进态；
- 但主聚合视图仍然保留 backend_export 旧主状态。

所以这一层不能再叫“偶尔不同步”，而应明确叫：

> **聚合后的主视图当前没有把 runtime 推进态稳定抬成主真相。**

### 2. `tasks_governance_samples.json` 对该任务缺席，不是巧合，而是样本准入条件导致的空洞
继续看 `scripts/sync_governance_samples.py`：
- 它会加载四类 source：
  - `runtime_view`
  - `legacy_tasks_source`
  - `mission_control`
  - `manual_parallel`
- 但样本是否保留，还要看：
  - `has_governance_markers(task)`
  - `prune_samples(...)`
  - 以及 probe / 老化过滤

当前 `has_governance_markers(task)` 只认这些字段：
- `pending_confirm`
- `gate_checks`
- `review_round`
- `templateId`
- `templateParams`
- `targetDept`
- `autopsy`
- `notifications`

而今天这条任务 `bbbf369f-...` 的 runtime/source 现场状态虽然已经推进，但并不天然带这些 governance markers，所以最后结果就是：

> **它明明是正在真实推进的任务，却因为不带上述治理字段，被 governance sample 层完全漏收。**

这解释了为什么会出现下面这种割裂：
- runtime 有这条任务；
- source 有这条任务；
- live_status 有这条任务；
- governance_samples 却查无此项。

因此当前更准确的新口径应补成：

> **`tasks_governance_samples.json` 现在不是“所有关键推进任务的稳定治理沉淀层”，它更像“带治理标记字段任务的样本层”；对纯推进态任务，现行准入规则会漏收。**

### 3. `live_status.json` 为什么继续显示 `backend_api_export`，现场原因已经非常直接
继续看 `scripts/refresh_live_data.py`，当前逻辑是：
- 先读 `tasks_source.json`
- 再判断 `tasks` 列表里是否存在 `sourceLayer == 'backend_export'`
- 只要有，就沿用 `tasks_backend_export_meta.json` 里的：
  - `taskSource`
  - `taskSourceMeta`

而今天现场 `tasks_source.json` 中明确还存在多条 `sourceLayer=backend_export` 任务，包含 `bbbf369f-...` 本身。

所以：

> **`live_status.taskSource = backend_api_export` 不是 refresh 脚本误判，而是它忠实反映了“当前聚合主视图里仍在使用 backend_export 任务作为事实源之一”。**

这也意味着，如果不先把 `tasks_source.json` 中这批 backend_export 主视图残留真正收干净，单改 `refresh_live_data.py` 文案没有意义；它只会继续诚实地把现场真相暴露出来。

### 4. 因此这轮继续复查后的新结论，应从“多层状态脱节”再往下收紧一层
上一轮我已经把问题从“完全不可用”纠偏成“多层状态脱节”。

这轮继续抠完代码和数据后，可以再收紧成：

> **当前 edict 的主要稳定性问题，不只是多层状态脱节，而是：**
> 1. **主聚合视图没有把 runtime 推进态稳定提升为主状态；**
> 2. **governance sample 现行准入条件会漏掉纯推进态任务；**
> 3. **live_status 对 backend_api_export 的显示并非幻觉，而是主视图里确实还混着 backend_export 层任务。**

换句话说：

> **现在不是“派不出去”，也不是“runtime 没推进”，而是“推进了以后，主视图、样本层和最终展示层采用了不同的收真相规则”，所以越往上看越像没推进，越往 runtime 里看越能看到真实推进。**

### 5. 下一步优先修法建议也应更新
如果接下来继续修，不应再泛泛说“修同步”。优先级应更具体：

1. **先修 `rebuild_task_views.py` 的主状态覆盖策略**
   - 让 runtime 已识别出的 `state/org/now/updatedAt` 在满足条件时，能稳定压过 backend_export 旧主状态；
   - 否则主视图永远落后半拍。

2. **再修 `sync_governance_samples.py` 的样本准入条件**
   - 对已桥接出明确 `taskId + state/org` 的 runtime 推进态，不能只因为缺 `pending_confirm/gate_checks/...` 就完全不入样本；
   - 否则 governance sample 无法承担“治理推进历史沉淀层”的角色。

3. **最后才决定要不要继续压缩 backend_export 残留面**
   - 因为 `live_status` 当前显示 backend_api_export 并不是根因，而是上游主视图残留的结果。

一句话更新这轮继续复查后的最终口径：

> **edict 当前的核心问题已经收紧为“推进态真相提升失败”：runtime 看得到，主视图抬不上去，样本层还会漏收，最终导致 live_status 继续暴露旧的 backend_export 主状态。**


---

## 2026-05-05 再继续复查补记：backend export 不是历史残留，而是当前 loop 仍在显式开启

这轮继续往下抠后，已经把一个更底层、也更硬的现场事实钉死：

> **当前 `backend_api_export` 不是旧数据尾巴，也不只是某处文档口径没更新；而是运行中的 `run_loop.sh` 进程现在就带着 `EDICT_ENABLE_BACKEND_EXPORT=true`，在持续执行 backend export 覆盖链。**

### 1. 现场进程环境已直接坐实：run loop 现在就是开着 backend export 跑的
本轮直接读取运行中 loop 进程 `PID=3800151` 的环境变量：
- `EDICT_DASHBOARD_PORT=7892`
- `EDICT_HOME=/root/.openclaw/workspace/edict`
- **`EDICT_ENABLE_BACKEND_EXPORT=true`**

同时 `scripts/run_loop.sh` 代码里也写得很直白：
- `BACKEND_EXPORT_ENABLED="${EDICT_ENABLE_BACKEND_EXPORT:-0}"`
- 只要 `is_true "$BACKEND_EXPORT_ENABLED"`，就会执行：
  - `export_backend_tasks_to_legacy_json.py`

所以这条线已经不是推测，而是现网硬事实：

> **当前 loop 每轮都会把 backend 导出重新灌回 `tasks_source.json`。**

### 2. `tasks_source.json` 现在 18 条任务全部是 `backend_export`，不是“混入了一部分”
本轮现场直读：
- `data/tasks_source.json`
  - `count = 18`
  - `layers = {'backend_export': 18}`

这比上一轮“还能看到多条 `backend_export`”更进一步：

> **不是 tasks_source 里还残留几条 backend_export，而是当前整个主任务视图 18 条全都来自 backend_export。**

也就是说，现阶段如果还把 `tasks_source.json` 当成“runtime + governance + archive 聚合后的主真相”，那就是错的；它当前实际更像 backend export 覆盖后的 legacy 主出口。

### 3. `tasks_backend_export_meta.json` 也在持续证明这件事不是旧脏文件假象
本轮直读：
- `data/tasks_backend_export_meta.json`
  - `taskSource = backend_api_export`
  - `backendUrl = http://127.0.0.1:18000`
  - `count = 18`
  - `exportedAt = 2026-05-05T04:19:02.593892+00:00`

再结合 `refresh_live_data.py` 当前逻辑：
- 只要 `tasks_source.json` 里存在 `sourceLayer == 'backend_export'`
- 就会继续把 `live_status.taskSource` 写成 `backend_api_export`

所以：

> **`live_status.taskSource = backend_api_export` 不是 refresh 层误判，它只是把上游真实现场诚实反映出来。真正的问题不在 refresh，而在 loop 当前确实还在导出 backend 覆盖 tasks_source。**

### 4. dashboard 日志还暴露出第二个现象：这条任务正在被高频重复派发，不是单次成功就收口
`journalctl -u edict-dashboard.service --since '2026-05-05 11:30:00'` 现场可见：
- 从 `11:31` 到 `12:17`，几乎每两分钟一次：
  - `推进后自动派发 -> zhongshu`
  - `自动派发成功 -> zhongshu`

也就是说：

> **这条任务不是“派发成功一次后就稳定停住”，而是在持续被重复派发到 zhongshu。**

这进一步说明：
- 上层看到的“还能派发”并不等于“已经稳定”；
- 现网仍存在重复触发 / 重复推进 / 主状态未收敛的问题。

### 5. 因此，这轮之后必须把前面的结论再修正一次
前面我已经把口径从：
- “完全不可用”
修正为：
- “可派发，但多层状态脱节”
又修正为：
- “runtime 真相提升失败”

现在这一轮继续往下抠后，还要再补一个更底层的现实：

> **当前 `tasks_source.json` 根本不处在“已摆脱 backend export、主要由 runtime/governance/archive 聚合主导”的状态；相反，运行中的 loop 明确开着 `EDICT_ENABLE_BACKEND_EXPORT=true`，因此 backend export 仍在作为现网主覆盖链生效。**

这意味着前面很多“为什么 source 没吃到 runtime 真相”的分析，虽然方向没错，但还不够到底；因为在当前现场里：
- runtime / governance / rebuild 确实在跑；
- **但它们产出的主视图，会被后续 backend export 再覆盖一遍。**

换句话说：

> **不是单纯聚合策略吃掉了 runtime 真相，而是 runtime 真相即便短暂聚合出来，也会被当前仍开启的 backend export 主覆盖链重新压回 backend 口径。**

### 6. 这轮继续复查后的新主结论
截至这一轮，最准确的现场结论应更新为：

> **edict 当前并非“任务派不出去”；相反，它还能高频成功派发到 zhongshu。真正的主问题是：当前 loop 仍显式开启 `EDICT_ENABLE_BACKEND_EXPORT=true`，导致 `tasks_source.json` 全量处于 backend_export 覆盖态；因此 runtime / governance / rebuild 即便识别出更新治理推进态，也难以把它稳定保留为主视图真相。与此同时，dashboard 侧还在对同一任务高频重复派发，说明稳定性问题不止是展示失真，还包含重复触发未收敛。**

### 7. 下一步优先级必须再次调整
现在如果继续查，优先级不该再是泛泛“看看聚合脚本”。应改成：

1. **先查 / 收掉当前谁把 `EDICT_ENABLE_BACKEND_EXPORT=true` 带进了运行中的 loop**
   - 不把这条主覆盖链停掉，后面看再多聚合细节也容易被覆盖；
2. **再验证停掉 backend export 后，runtime / rebuild / governance 三层能否自然收敛**
   - 到那时再判断 `rebuild_task_views.py` 和 `sync_governance_samples.py` 的策略问题还有多少是真问题；
3. **最后再收重复派发问题**
   - 因为现在日志已经坐实它在按 2 分钟级节奏反复派发同一任务，不是单轮偶发。

一句话收口这轮新增发现：

> **当前最大的隐藏前提已经揭开：backend export 不是历史，而是现行主覆盖链；不先把这条链路收掉，就很难让 source/live-status 真正反映 runtime 推进态。**


---

## 2026-05-05 再继续补记：systemd 级来源已经钉死，重复派发也有了稳定节奏

这一轮继续往上追，已经把来源链和现象链都钉死到 service 级：

### 1. `EDICT_ENABLE_BACKEND_EXPORT=true` 的来源不再是手工 shell，而是 `edict-loop.service`
现场 `systemctl cat edict-loop.service` 已明确显示：
- `Environment=EDICT_ENABLE_BACKEND_EXPORT=true`
- `ExecStart=/usr/bin/bash /root/.openclaw/workspace/edict/scripts/run_loop.sh 15 120`
- `Requires=edict-dashboard.service`

同时 `systemctl --no-pager --full status edict-loop.service` 显示：
- 服务名：`edict-loop.service - edict data refresh loop`
- `Active: active (running) since Tue 2026-05-05 07:33:23 CST; 6h ago`
- 主进程：`PID 3800151`
- 主命令：`/usr/bin/bash /root/.openclaw/workspace/edict/scripts/run_loop.sh 15 120`

这意味着：

> **backend export 之所以一直存在，不是因为某个孤儿 bash 偶发残留，而是因为 systemd 的 edict-loop 服务本身就被配置成了显式开启状态。**

### 2. 当前主视图被 backend_export 全量覆盖，已经不是“残留几条”的问题
现场再次直读：
- `data/tasks_source.json`
  - `state = Zhongshu`
  - `org = 中书省`
  - `sourceLayer = backend_export`
  - `flow_log = [Taizi, Zhongshu]`
  - `progress_log = []`
- `data/live_status.json`
  - 对应同一任务也仍是：
    - `state = Zhongshu`
    - `org = 中书省`
    - `sourceLayer = backend_export`

结合前一轮已经确认的全量分布：
- `tasks_source.json` 18 条任务全部 `backend_export`
- `tasks_backend_export_meta.json` 仍存在
- `live_status.taskSource` 继续为 `backend_api_export`

因此现网口径应再明确一次：

> **当前主视图不是“混入了一些 backend_export”，而是已经被 backend_export 全量覆盖。**

### 3. 重复派发的时间节奏已经稳定到肉眼可见
`journalctl -u edict-dashboard.service --since '2026-05-05 13:50:00'` 可见从 13:57 一直到 14:19，几乎每两分钟一次固定重复：
- `推进后自动派发 → zhongshu`
- `自动派发成功 → zhongshu`

这说明：

> **同一任务不是偶发被派两次，而是在一个稳定的定时巡检/自动派发节奏下持续被重复推进。**

这个现象的意义是：
- 不再是“偶发噪声”；
- 而是**调度层的默认行为仍在持续触发**；
- 这也解释了为什么 `tasks_source.json` 一直难以沉降成更干净的 runtime 真相。

### 4. 这轮继续复查后的最新收口
前面已经把结论逐步收紧为：
- 不是完全不可用；
- 不是单纯多层状态脱节；
- 不是单纯 runtime 真相提升失败；
- 不是单纯 backend_export 残留。

现在再补上 systemd 级来源后，最准确的现场结论应改成：

> **edict 当前的稳定性问题是“systemd 级 backend_export 全量开启 + dashboard 侧定时自动派发重复触发”叠加造成的：loop 服务持续把主视图导回 backend_export，dashboard 又按定时巡检持续把同一任务重新派发到 zhongshu，于是 runtime / governance / live_status 之间很难形成稳定的单一真相。**

### 5. 下一步真正该查的已非常具体
如果继续往下查，已不该再停留在“看数据层有没有问题”，而应该直接问：
1. **谁把 `edict-loop.service` 设成 `EDICT_ENABLE_BACKEND_EXPORT=true` 作为当前常驻配置；**
2. **dashboard 侧为什么会以固定节奏反复把同一任务推进后自动派发到 zhongshu；**
3. **这两条链路是否是同一个 cutover 设计下的过渡态遗留，还是当前现网误配置；**
4. **如果要恢复 runtime 真相，应该先关哪一个总闸。**

一句话收口：

> **现在已经不是“有没有问题”的阶段，而是已经明确到：systemd 级 backend export 常驻开启，配合 dashboard 定时重复派发，正在持续制造主视图与 runtime 的错位。**


---

## 2026-05-05 根因线继续下钻：已把“配置来源”与“固定节奏重复派发”两条线接上

这一轮继续按用户要求沿两条根因线往下抠：
1. **是谁把 `edict-loop.service` 固化成 `EDICT_ENABLE_BACKEND_EXPORT=true` 常驻态；**
2. **dashboard 为什么会按固定节奏反复把同一任务自动派发到 `zhongshu`。**

现在已经能把这两条线接起来，而不是各说各话。

### 1. `edict-loop.service` 的 `EDICT_ENABLE_BACKEND_EXPORT=true` 不是偶发漂移，而是 4 月底 cutover / 回切文档里明确保留下来的现网过渡态
这轮不再只看当前 systemd unit，而是顺着仓内文档、计划、回滚演练记录往回追，现场证据已经非常一致：

- `/etc/systemd/system/edict-loop.service` 文件时间：`2026-04-30 05:45:14 +0800`
- 同一时间窗口的文档/计划多处都明确写了：
  - `docs/plans/2026-04-28-backend-cutover-minimal-rollout.md`
  - `docs/plans/2026-04-30-systemd-rollback-drill-runbook.md`
  - `docs/closeout.md`
  - `docs/RELIABILITY.md`
  - `docs/current-progress-board.md`

这些材料的共同口径不是“误加了这行配置”，而是：

> **为了让 backend → legacy JSON 兼容导出链进入生产 dual/export 过渡态，故意把 `edict-loop.service` 设成 `Environment=EDICT_ENABLE_BACKEND_EXPORT=true`，并在 2026-04-30 的 systemd 回滚演练后又按既定顺序回切恢复。**

也就是说，这条配置的来源已经可以收紧成：

> **当前常驻态不是“某次误操作遗留”，而是 4 月底 backend host-native cutover / rollback drill 结束后，被明确回切恢复的过渡态配置。**

这点和主板 2026-05-03 那条“总闸已切断、现网纯净 loop 已用 `env -i` 重拉”的说法，已经发生直接冲突。因为今天现场看到的是：
- `edict-loop.service` 仍然 active
- unit 文件仍然带 `EDICT_ENABLE_BACKEND_EXPORT=true`
- `tasks_source.json` 仍被 backend_export 全量覆盖

因此更准确的表述只能是：

> **至少到 2026-05-05 这次现网复查为止，5 月 3 日所声称的“legacy backend export 总闸已切断”并没有稳定保留在 systemd 常驻态里；当前生效的仍是 4 月底 dual/export 过渡态的 loop service 配置。**

### 2. dashboard 固定节奏重复派发的根因，不再是抽象“巡检太激进”，而是 backend export 把 `_scheduler` 状态洗空了
这一轮把 `handle_scheduler_scan()`、`_ensure_scheduler()`、backend 导出脚本和现场数据对位后，重复派发的成因已经非常具体。

#### 2.1 `handle_scheduler_scan()` 的触发规则本身并不神秘
`dashboard/server.py` 当前逻辑：
- `_ensure_scheduler(task)` 会给每个任务补默认调度状态：
  - `stallThresholdSec = 600`
  - `maxRetry = 2`
  - `retryCount = 0`
  - `lastProgressAt = task.updatedAt`（若原任务没带）
  - `snapshot = {state, org, ...}`（若原任务没带）
- `handle_scheduler_scan()` 遍历任务时，会用：
  - `last_progress = sched.lastProgressAt or task.updatedAt`
  - `stalled_sec = now - last_progress`
- 若超过阈值，且：
  - `retryCount < maxRetry` → 先做 `taizi-scan-retry`
  - 然后调用 `dispatch_for_state(task_id, task, state, trigger='taizi-scan-retry')`

所以它不是无缘无故每两分钟发疯，而是**每轮都认为这条任务是“老任务停滞，需要重试”**。

#### 2.2 为什么它会一直这么认为？因为 export 出来的任务把 `_scheduler` 洗成了空字典
现在现场最关键的新证据有三条：

1. `export_backend_tasks_to_legacy_json.py` 会把 backend `/api/tasks` 的 `scheduler/_scheduler` 原样带出来；
2. 但当前 backend 里的这条任务 `bbbf369f-959b-484e-890d-9c28d56b748a` 现场返回就是：
   - `scheduler = {}`
   - `_scheduler = {}`
3. 导出后的 `data/tasks_source.json` 现场也是：
   - **18/18 条任务 `_scheduler = {}`**

这意味着：

> **只要 loop 继续做 backend export，写回 `tasks_source.json` 的就不是带有巡检历史、重试计数、快照与 lastProgressAt 的任务，而是一批 `_scheduler` 全空的“新鲜旧任务”。**

而 `handle_scheduler_scan()` 每轮一看这些任务：
- `_scheduler` 是空的
- `updatedAt` 又是很早以前的时间
- 于是 `_ensure_scheduler()` 只能重新补一套默认值
- 接着就把它们再次认定为“停滞超阈值、需要重试派发”

所以重复派发的更底层机制已经可以明确写成：

> **不是 scheduler 自己记不住，而是 scheduler 记住的东西根本没有稳定存活到下一轮——因为主任务源被 backend export 周期性重写，而 backend 当前又没有把对应的 `_scheduler` 调度状态持久化回来。**

#### 2.3 这也解释了“为什么固定节奏差不多每两分钟一次”
当前 `edict-loop.service` 每 15 秒刷一次 `tasks_source.json`；
而 dashboard 的调度扫描会反复基于“已被重写后的旧任务”重新判断停滞。

虽然是否正好两分钟还和扫描入口/循环节拍有关，但根本点已经够明确：

> **固定节奏重复派发，不是因为任务真的在两分钟内又新卡死了一次，而是因为这条任务的调度记忆每轮都在被 backend export 清洗回“空白停滞态”。**

### 3. 同一任务的 backend/source/runtime 三面已经能完整解释错位
本轮把同一任务 `bbbf369f-959b-484e-890d-9c28d56b748a` 三面对位后，证据链非常完整：

- backend `/api/tasks`
  - `state = Zhongshu`
  - `flow_log` 只有 `Taizi -> Zhongshu`
  - `progress_log = []`
  - `_scheduler = {}`
- `data/tasks_source.json`
  - 和 backend 几乎一致
  - `state = Zhongshu`
  - `sourceLayer = backend_export`
  - `_scheduler = {}`
- `data/tasks_runtime_view.json`
  - 已经看到会话推进到：
    - `state = Menxia`
    - `org = 门下省`
    - `now = 思考中: 已接旨`

所以当前错位不是一个点错，而是三层一起构成的：

1. **runtime 看到了更前的会话推进态；**
2. **backend 主任务实体没同步到这一步；**
3. **loop 又把 backend 的旧态重新导回 `tasks_source.json`；**
4. **scheduler 元数据还在 export 过程中被洗空；**
5. **于是 dashboard 巡检继续把同一任务当成“停滞的 Zhongshu 任务”反复重试派发。**

### 4. 这轮之后，两条根因线已经不是并列问题，而是串联问题
现在可以把“配置来源”和“触发机制”合并成一句更准确的话：

> **4 月底为了 dual/export 过渡态而保留下来的 `edict-loop.service + EDICT_ENABLE_BACKEND_EXPORT=true` 常驻配置，正在持续把 backend 的旧任务态（且 `_scheduler` 为空）重新覆盖回 `tasks_source.json`；dashboard 的 scheduler scan 随后把这些被洗空调度记忆、但 `updatedAt` 很老的任务再次认定为停滞，于是以固定节奏反复自动派发到 `zhongshu`。**

这就不是两个孤立 bug，而是**同一条主链上的上下游耦合故障**。

### 5. 当前最接近根因的结论
截至这一轮，最接近根因的表述应更新为：

> **edict 当前反复派发到 `zhongshu` 的根因，不是单纯 dashboard 调度阈值设置有问题，而是 systemd 常驻的 backend export 过渡态仍在生效，且 backend 导出的任务没有保留 `_scheduler` 调度记忆，导致巡检每轮都把同一条老任务重新识别成“停滞待重试”。**

### 6. 如果后续要继续查，下一步已非常具体
从“根因确认”继续往下做，优先级应是：

1. **确认 backend 主链为何没有把 runtime 推进态（至少 `Menxia`）和调度元数据稳定沉淀回任务实体；**
2. **确认 export 脚本是否应补保真逻辑，还是根本不该继续处于常驻开启态；**
3. **确认 dashboard scheduler scan 是否应对 `_scheduler={}` 且 `sourceLayer=backend_export` 的任务加防抖/抑制条件；**
4. **最终再决定是收掉 loop export，总线切纯聚合视图，还是先修 backend 状态/调度持久化。**

一句话收口：

> **现在已经能把问题讲完整：不是“edict 有点不稳”，而是“4 月底保留下来的 dual/export 过渡态常驻配置 + backend 导出任务缺失 `_scheduler` 记忆 + dashboard 巡检按旧时间戳判停滞”三者叠加，稳定制造了同一任务的重复派发与主视图落后。**


---

## 2026-05-05 继续下钻：backend 主任务实体本身就停在旧态，export 只是把旧态忠实放大

这一轮继续往 backend 主任务实体、调度记忆持久化和 worker 写回链下钻后，现场证据又收紧了一层：

> **当前问题不只是 export 把 `_scheduler` 洗空；更底层的现实是：backend 主任务实体自己就停在 `Zhongshu`，且 `scheduler={}`。export 只是把这个尚未被主链更新的旧实体忠实地导出到了 `tasks_source.json`。**

### 1. backend `/api/tasks` 和 `/api/tasks/live-status` 对这条任务返回的是同一份旧实体
本轮直接拉 backend API：
- `GET http://127.0.0.1:18000/api/tasks?limit=50`
- `GET http://127.0.0.1:18000/api/tasks/live-status`

对同一任务 `bbbf369f-959b-484e-890d-9c28d56b748a` 返回完全一致：
- `state = Zhongshu`
- `org = 中书省`
- `updated_at = 2026-05-01T09:14:30.061384+00:00`
- `flow_log` 只有两段：
  - `任务创建 -> Taizi`
  - `Taizi -> Zhongshu`
- `progress_log = []`
- `scheduler = {}`
- `_scheduler = {}`
- `output = ""`

这说明：

> **backend 自己并没有持有“已推进到 Menxia”的主任务事实。**

因此此前如果把锅全甩给 export，是不完整的；因为 export 当前导出的，正是 backend 主任务表自己提供的旧任务态。

### 2. runtime 已推进到 `Menxia`，但这一步没有沉淀回 backend 任务实体
同一任务在 `data/tasks_runtime_view.json` 里现场仍是：
- `state = Menxia`
- `org = 门下省`
- `now = 思考中: 已接旨`

而 backend 主任务实体仍是：
- `state = Zhongshu`
- `scheduler = {}`
- `progress_log = []`

所以现在已经能明确一句话：

> **runtime 会话推进态并没有稳定回写成 backend 主任务实体的状态推进。**

这意味着主问题比“legacy 视图不准”更深：
- 不是只有 legacy 侧没吃到 runtime 真相；
- **backend 主任务实体自己也没吃到 runtime 真相。**

### 3. backend 代码里明明有 `scheduler`、`progress_log`、`flow_log` 持久化能力，但当前这条链没有真正打通到主任务态
这轮继续翻 backend 代码，确认下面几件事都存在：

#### 3.1 Task 模型确实有这些字段
`edict/backend/app/models/task.py` 已有：
- `flow_log = JSONB`
- `progress_log = JSONB`
- `scheduler = JSONB`
- `updated_at`

并且 `to_dict()` 会把它们导出为：
- `flow_log`
- `progress_log`
- `scheduler`
- `_scheduler`
- `updatedAt`

所以当前 API 返回空 `scheduler` 不是“字段不存在”，而是**数据库里这条任务当前就真是空的**。

#### 3.2 service 层也确实有写这些字段的能力
`edict/backend/app/services/task_service.py` 里已存在：
- `transition_state()`：会追加 `flow_log`
- `add_progress()`：会追加 `progress_log`
- `update_scheduler()`：会写 `task.scheduler = scheduler`

这说明 backend 不是设计上不支持 scheduler / progress / flow，而是**当前主链没有把 runtime 推进态通过这些入口稳定写回去**。

#### 3.3 dispatch worker 只会写 progress/output，不会直接推进主状态到 `Menxia`
`edict/backend/app/workers/dispatch_worker.py` 当前对 agent 输出的持久化逻辑是：
- `await svc.add_progress(task_id, agent, sanitized_stdout or raw_stdout)`
- 成功时把 `task.output = raw_stdout`

但它并不会自己根据“agent 已接旨”去：
- `transition_state(..., Menxia)`
- 或 `update_scheduler(...)`

所以如果 agent/runtime 侧没有另外一条结构化回写链把：
- `state/org`
- `scheduler.lastProgressAt/retryCount/snapshot`
- `progress_log`
同步回 backend 主实体，
那 backend 主实体当然就会继续停在旧状态。

这进一步解释了当前现场：

> **dispatch worker 能写“输出痕迹”，但并不等于它会把 runtime 会话推进事实自动提升成 backend 主任务状态。**

### 4. 这也解释了为什么当前 backend API 样本里大量任务 `scheduler={}`、`progress_log=[]`
本轮现场扫了 backend `/api/tasks` 样本，前几条任务都出现：
- `scheduler = {}`
- `progress_log len = 0`
- `output = ""`

再结合同一轮 `tasks_source.json` 统计：
- **18/18 条任务 `_scheduler = {}`**

这说明问题不是只出在一条任务上，而是更像：

> **当前 backend 主任务表普遍没有沉淀出前台 scheduler 所依赖的调度记忆。**

所以 dashboard scheduler scan 每次基于 export 回流任务去判停滞时，面对的是一批：
- `updatedAt` 很老
- `_scheduler` 为空
- 没有最近 progress 的任务

于是重复派发就会成为系统性的默认结果，而不是单任务偶发问题。

### 5. 这轮之后，根因链应再补一层“backend 主实体未收敛”
前面已经确认：
- dual/export 过渡态常驻
- export 持续覆盖 `tasks_source.json`
- `_scheduler` 在 export 产物里为空
- dashboard scan 因此反复重试

这轮继续下钻后，应再补一句更底层的根因：

> **之所以 export 产物里 `_scheduler` 一直是空的，不只是 export 脚本没补；更是因为 backend 主任务实体本身就没有稳定沉淀 scheduler / progress / runtime 推进态。也就是说，主状态未收敛发生在 backend 主表这一层，而 legacy/export 只是把这个未收敛事实放大了。**

### 6. 当前最准确的结构化表述
截至这一轮，最准确的主链表述应更新为：

1. **systemd 常驻的 `edict-loop.service` 仍开启 backend export；**
2. **backend 主任务实体本身仍停在 `Zhongshu + scheduler={}` 的旧态；**
3. **runtime 会话虽已推进到 `Menxia`，但这一步没有稳定沉淀回 backend 主任务实体；**
4. **export 只是把 backend 旧态忠实写回 `tasks_source.json`；**
5. **dashboard scheduler scan 再把这些 `_scheduler` 为空、`updatedAt` 很老的任务反复识别成停滞任务，于是固定节奏重复派发到 `zhongshu`。**

这比之前的说法更接近完整闭环。

### 7. 下一步该继续抠的已再次收紧
现在继续往下查，不该再泛泛说“看看 backend”。优先级应进一步收紧成：

1. **runtime -> backend 主任务实体 的状态回写链到底缺在哪一跳**
   - 是没有结构化事件；
   - 还是有事件但 orchestrator / service 没消费成 `transition_state()`；
   - 还是写了 progress/output 但没写 state/scheduler。

2. **backend `scheduler` 字段为什么在主任务样本里长期为空**
   - 是当前根本没走 `update_scheduler()`；
   - 还是被别的链覆盖清空。

3. **dashboard 是否应该在读取 `backend_export + _scheduler={}` 任务时加保护，避免重复派发雪上加霜**

一句话收口这轮新增发现：

> **现在已经能确认：重复派发的上游不是单纯 legacy/export 错位，而是 backend 主任务实体自己就没有收敛到 runtime 已推进的状态；export 只是把这个旧态忠实同步给了 dashboard。**


---

## 2026-05-05 继续下钻：runtime → backend 主任务状态回写链缺的不是“小字段”，而是整条事件消费链

这一轮继续顺着 `runtime -> backend 主任务实体` 往下抠，已经拿到目前最关键的一层根因：

> **backend 当前并没有一条“消费 agent 输出 / 会话推进结果 → 驱动主任务 `transition_state()` / `update_scheduler()`”的链路。**

也就是说：
- dispatch worker 能把任务发给 agent；
- agent/runtime 会话也确实能继续推进；
- 但 backend 主任务实体不会因为 agent 已接旨、已推进、已审议而自动变成 `Menxia/Assigned/...`。

### 1. orchestrator 当前监听的 topics 里，根本没有 `agent.thoughts`
本轮直接读 `edict/backend/app/workers/orchestrator_worker.py`：

`WATCHED_TOPICS` 当前只有：
- `TOPIC_TASK_CREATED`
- `TOPIC_TASK_STATUS`
- `TOPIC_TASK_COMPLETED`
- `TOPIC_TASK_STALLED`

而 `dispatch_worker.py` 在 agent 返回后真正发布的是：
- `TOPIC_AGENT_THOUGHTS`
- `event_type = "agent.output"`

也就是说：

> **dispatch worker 发布了 agent 输出事件，但 orchestrator 根本没订阅 / 没消费 `agent.thoughts`。**

这不是“消费了但解析失败”，而是更直接：**它不在 watched topics 里。**

### 2. dispatch worker 当前只会做两件事：写 progress/output，不会写主状态
`edict/backend/app/workers/dispatch_worker.py` 当前在 agent 成功返回后，做的是：
- 发布 `agent.output`
- 调 `svc.add_progress(task_id, agent, sanitized_stdout or raw_stdout)`
- 若返回码为 0 且有输出，则写：
  - `task.output = raw_stdout`

但它不会：
- `transition_state(task_id, TaskState.Menxia, ...)`
- `transition_state(task_id, TaskState.Assigned, ...)`
- `update_scheduler(task_id, {...})`

所以当前 dispatch worker 的语义更像：

> **“我把消息发给 agent，并把 agent 回话内容记个痕迹。”**

而不是：

> **“我根据 agent 推进结果，把主任务状态推进到下一节点。”**

因此如果没有另一条事件消费链接手解析 agent 输出并推动状态机，主任务实体当然会卡在原状态。

### 3. backend 当前真正会改主状态的入口，仍然只有显式状态流转 API / service 调用
本轮继续对 `task_service.py` 做对位，当前真正会改 `task.state` 的主要入口只有：
- `transition_state()`
- `review_action()`（内部也会调 `transition_state()`）
- `orchestrator_worker._on_task_stalled()`（做升级/阻塞时直接改 state）

但现在没有看到任何一条后台链路会在收到：
- `agent.output`
- `agent.dispatch.start`
- runtime 会话推进态
之后，自动调用：
- `transition_state(..., Menxia/Assigned/Doing/...)`

因此当前 backend 的主状态推进机制，仍更像：

> **需要明确的结构化状态事件，不能靠 agent 自由文本输出自然推进。**

可现场恰恰是：
- runtime 会话推进到了 `Menxia`
- 但 backend 没有消费这类“会话推进事实”的结构化入口

这就解释了为什么 backend 主实体长期停在 `Zhongshu`。

### 4. 这也解释了“为什么 runtime_view 能前进，但 backend 主实体完全不动”
前面已经确认：
- `tasks_runtime_view.json` 里这条任务已到 `Menxia`
- backend `/api/tasks` / `/api/tasks/live-status` 里同一任务还在 `Zhongshu`

现在根因已经够具体：

> **runtime_view 的推进，来自 OpenClaw 会话观察 / session bridge；**
> **backend 主任务状态推进，依赖 backend 自己的结构化状态机事件；**
> **而当前系统里这两条链没有打通。**

所以不是 runtime 假推进，也不是 backend 查询错了，而是：

> **它们各自说的是两套没有自动汇流的真相。**

### 5. dashboard 固定节奏重复派发因此变成必然结果，而不是巧合
把前面所有证据串起来，现在重复派发链已经可以完整描述为：

1. `edict-loop.service` 常驻开启 backend export；
2. backend 主任务实体仍停在 `Zhongshu + scheduler={}`；
3. runtime 会话虽然推进到了 `Menxia`，但 backend 没有消费 `agent.output` 去推进主状态；
4. export 于是持续把 backend 旧态写回 `tasks_source.json`；
5. dashboard 的定时巡检每轮看到的都是：
   - 老 `updatedAt`
   - 空 `_scheduler`
   - `state=Zhongshu`
6. 所以每轮都认定这还是一条“停滞待重试的 Zhongshu 任务”；
7. 于是稳定地每两分钟左右再次自动派发到 `zhongshu`。

这条链到这里已经很完整了。

### 6. 当前最接近根因中心的一句话
截至这一轮，最接近根因中心的表述应更新为：

> **系统真正缺的不是某个 if 或时间戳，而是“agent/runtime 推进结果 → backend 主任务状态机”的自动汇流链。dispatch worker 只会记输出，orchestrator 也不消费 `agent.output`，因此 backend 主任务实体不会因会话推进而前进；backend export 再把这个旧态持续放大给 dashboard，最终稳定制造重复派发。**

### 7. 后续继续查，优先级已再次收紧
如果继续往下做，优先级应是：

1. **确认当前 runtime_view 是由哪条 session bridge / sync 脚本观察出来的，为什么它不反向写回 backend；**
2. **确认设计上是否本就打算由 agent 输出触发结构化状态回写，还是缺了专门的 parser/consumer；**
3. **确认 backend 是不是需要新增对 `TOPIC_AGENT_THOUGHTS/agent.output` 的消费器，或把状态推进改成显式 API 回写；**
4. **在这条主链未补齐前，dashboard 应至少对 `backend_export + state=Zhongshu + _scheduler={}` 任务加重复派发抑制。**

一句话收口：

> **现在已经基本坐实：runtime 会推进、backend 不会跟；不是因为 backend 不支持状态流转，而是因为当前根本没有一条把 runtime 推进事实自动喂进 backend 状态机的消费链。**


---

## 2026-05-05 继续下钻：runtime_view 的 `Menxia` 来自 transcript 语义推断，而且这条桥是单向的

这一轮继续顺着“runtime 推进事实为什么没回写 backend”往下查，现场已经把桥中间那段彻底看清了：

> **`tasks_runtime_view.json` 里的 `Menxia` 不是 backend 产物，也不是结构化状态事件；它是 `sync_from_openclaw_runtime.py` 从 OpenClaw session transcript 文本里做语义推断得到的。更关键的是：这条脚本只写 runtime_view，不反写 backend。**

### 1. `sync_from_openclaw_runtime.py` 的职责本质是“观察会话”，不是“推进主状态”
本轮直接读脚本后，可确认其主流程是：
- 扫描 `~/.openclaw/agents/*/sessions/sessions.json`
- 对每个 session 读取 transcript (`sessionFile`)
- 抽取 activity / rawText
- 对 `:edict-dispatch` 会话尝试：
  - `extract_task_id_from_activity(activity)`
  - `infer_governance_state_from_activity(activity)`
- 组装成 runtime 任务对象
- 最后只做：
  - `atomic_json_write(RUNTIME_VIEW, tasks)`

这里非常关键：

> **脚本没有任何一行去调用 backend API、`transition_state()`、`update_scheduler()` 或写数据库。**

它的产物只有：
- `data/tasks_runtime_view.json`
- 以及兼容聚合用的 archive 同步

因此这条链从设计上就是：

> **会话观测层 / runtime 实时映射层**

而不是：

> **主任务状态机写回层**

### 2. `Menxia` 是怎么推出来的：靠 transcript 文本命中规则，不是结构化真相
脚本里 `infer_governance_state_from_activity(activity)` 现在用的是文本规则：
- 如果命中 `状态更新: X -> Y` 这类文本，取目标状态；
- 或命中这些关键词：
  - `已在中书省 / 转交中书省 / 中书省起草` → `Zhongshu`
  - `已在门下省 / 转交门下省 / 门下省审议` → `Menxia`
  - `已在尚书省 / 转交尚书省 / 尚书省派发` → `Assigned`

而 `data/tasks_runtime_view.json` 里这条任务当前现场内容也正好印证了这一点：
- `sessionKey = agent:zhongshu:edict-dispatch`
- `taskId = bbbf369f-959b-484e-890d-9c28d56b748a`
- `state = Menxia`
- `org = 门下省`
- `activity` 里多次出现 assistant 文本：
  - `已接旨`
  - `看板状态：Menxia`
  - `状态更新: Zhongshu -> Menxia`
  - `当前仍卡在门下审议链路故障`

因此：

> **runtime_view 里的 `Menxia`，并不是 backend 主任务实体真实推进到了 Menxia，而是 session transcript 中有足够强的文本信号，被 runtime 同步脚本语义推断成 Menxia。**

这也解释了为什么它能比 backend“看起来更先进”：
- 它读的是 agent 会话文本世界；
- backend 读的是结构化任务状态世界；
- 两者没有自动收敛。

### 3. 这条桥为什么天然不会回写 backend：脚本设计目标就不是反写
`sync_from_openclaw_runtime.py` 当前主写动作只有：
- `atomic_json_write(RUNTIME_VIEW, tasks)`
- `atomic_json_write(ARCHIVE_FILE, archive)`
- `write_status(...)`

没有：
- HTTP 请求 backend `/api/tasks/{id}/transition`
- backend `/api/tasks/{id}/scheduler`
- DB 直接写入
- 事件总线 publish `task.state.*`

所以这条链当前的产品语义是：

> **“把 OpenClaw runtime sessions 观察成一层治理侧车视图”**

而不是：

> **“把 runtime 观察结果回灌成 backend 主状态”**

换句话说：

> **今天看到 runtime_view 比 backend 新，不是它‘漏了一步没写回’，而是它从一开始就不是拿来写回 backend 的。**

### 4. 这也让根因链再清楚一层：当前系统其实并行维护了两套状态世界
截至这一轮，已经可以非常明确地区分：

#### 4.1 backend 主状态世界
- 来源：`TaskService.transition_state()` / `review_action()` / orchestrator 停滞处理
- 载体：DB task entity
- 对外：`/api/tasks`、`/api/tasks/live-status`
- 当前问题：这条任务还停在 `Zhongshu + scheduler={}`

#### 4.2 runtime 会话观察世界
- 来源：OpenClaw session transcript 文本
- 推断器：`sync_from_openclaw_runtime.py`
- 载体：`tasks_runtime_view.json`
- 当前状态：这条任务被语义推断到 `Menxia`

这两套世界之间目前缺的不是“小同步 bug”，而是：

> **根本没有“观测到 runtime 推进 → 结构化确认 → 写回 backend 主状态”的桥。**

### 5. 所以现在终于能解释“为什么会出现 runtime 看起来更对，但系统主链仍重复派发”
因为当前主链实际依赖的是：
- backend 主任务实体
- backend export 回流到 tasks_source
- dashboard scan 基于 source + `_scheduler`

而不是 runtime_view。

runtime_view 只是：
- 一层更接近会话现场的侧车观察面板；
- 能给人看出“其实会话已经到 Menxia 了”；
- 但它对 backend 主状态、scheduler 和记忆没有强制约束力。

因此：

> **runtime_view 就算比 backend 更接近现场，也拦不住 dashboard 继续根据 backend 旧态重复派发。**

### 6. 这轮之后，对“缺桥”的定义可以再精确一点
前面我已经把问题收紧成：
- 缺少 `agent.output -> backend state machine` 的消费链。

这轮继续查后，可以再精确成：

> **当前不是简单缺一个事件消费者，而是整个 runtime sidecar 方案本身只负责“观察和推断”，从设计上就没有承担“主状态反写”的职责。因此 backend 与 runtime_view 的分叉不是偶发现象，而是当前架构职责边界天然造成的结果。**

### 7. 当前最准确的主结论
截至这一轮，最准确的表述应更新为：

> **`tasks_runtime_view.json` 里的 `Menxia` 不是 backend 主任务状态，而是 `sync_from_openclaw_runtime.py` 根据 OpenClaw transcript 文本（如“状态更新: Zhongshu -> Menxia”“当前仍卡在门下审议”）做出的语义推断；该脚本只写 runtime_view，不反写 backend。因此当前系统天然并行存在“会话观察真相”和“backend 主状态真相”两套世界，而 dashboard 重复派发依然由后者主导。**

### 8. 下一步若继续查，已经非常具体
如果继续往下抠，后续应明确分成两类选择题：

1. **架构选择题**
   - runtime_view 以后是否要继续只做侧车观察层；
   - 还是要新增“观察结果 -> 结构化状态回写”的正式桥。

2. **防误触选择题**
   - 在桥没补之前，dashboard 是否应把 runtime_view 中明确已 `Menxia/Assigned` 的同 taskId 任务视为重复派发抑制信号；
   - 否则 backend 旧态会持续压过 runtime 侧更接近现场的事实。

一句话收口：

> **现在已经基本看清：runtime_view 的 `Menxia` 是“看出来的”，backend 的 `Zhongshu` 是“写进去的”；前者不会自动改后者，所以重复派发不是偶然，而是这套双真相架构在未加桥接与抑制时的自然结果。**


---

## 2026-05-05 继续下钻：双真相基本属于阶段性架构设计结果，现成 guard 也没命中这条任务

这一轮继续按“两条分岔”往下查：
1. **runtime_view 只做侧车观察，是不是设计使然；**
2. **现网有没有现成抑制点本该拦住重复派发，却没有命中。**

现在结论已经可以再收紧一层。

### 1. `tasks_runtime_view.json` 作为只读/侧车层，基本可以判定是阶段性设计结果，不是临时失手
本轮继续核对文档与收口稿，几处现场证据高度一致：

#### 1.1 `docs/ARCHITECTURE.md` 已把三层数据分离写成正式分层
文档明确列出：
- `tasks_runtime_view.json` → runtime 层 / 当前运行态视图
- `tasks_governance_samples.json` → governance 层 / 治理验收样本
- `tasks_jjc_archive.json` → archive 层 / 历史归档

并在主线链路里写明：
- `sync_from_openclaw_runtime.py` 拉取运行态证据
- `rebuild_task_views.py` 重建聚合视图

这说明 runtime_view 从一开始就被定位成：

> **一层“运行态视图 / 观察视图”，而不是 backend 主状态表。**

#### 1.2 `docs/closeout.md` 也明确写过 Phase 1 改造目标
closeout 里已明确记录：
- `sync_from_openclaw_runtime.py` 改为单独输出 `data/tasks_runtime_view.json`
- `sync_governance_samples.py` 单独维护治理样本
- `rebuild_task_views.py` 再聚合回前端兼容出口 `tasks_source.json`

这个口径本质上就是：

> **先把 runtime / governance / archive 三层拆开，再聚合；不是让 runtime 直接回写 backend 主表。**

#### 1.3 backend cutover 方案也写过：JSON 只剩兼容导出 / 只读过渡用途
`docs/plans/2026-04-26-backend-mainline-cutover.md` 已写明阶段目标：
- backend 成为主写链
- JSON 仅剩兼容导出 / 只读过渡用途（若仍保留）

所以当前 runtime_view 不反写 backend，并不是“代码忘了补一个 POST”；更接近事实的说法是：

> **现阶段架构本来就把 runtime_view 设计成侧车观察层，把 backend 主任务实体设计成结构化主写层。**

也就是说，今天看到的“双真相”，至少在职责边界上并非完全意外，而是：

> **阶段性架构故意分层，但后续没有把“侧车观察结果何时/如何提升为主状态”这一步补齐。**

### 2. 现成 guard 确实存在，但它防的是“门下已有明确准奏/封驳后的重复送审”，并不防当前这条 `Zhongshu` 旧态重派
本轮继续抠 `dashboard/server.py`，已经确认现场确实有专门 guard：
- `_task_has_menxia_verdict(task)`
- `_suppress_menxia_repeat_review(task_id, trigger=...)`

它会在两处命中：
1. `handle_scheduler_scan()` 中，如果：
   - `state == 'Menxia'`
   - 且 `_task_has_menxia_verdict(task)` 为真
   就把这轮巡检重试 suppress 掉；
2. `dispatch_for_state()` 中，如果：
   - 目标 agent 是 `menxia`
   - 且 `_task_has_menxia_verdict(task)` 为真
   就直接跳过自动派发。

#### 2.1 这个 guard 的判定条件很具体
`_task_has_menxia_verdict()` 不是泛看 runtime_view 是否到了 Menxia，而是看：
- `progress_log`
- `flow_log`
- `now`
- `block`
- `output`
- `_scheduler.lastDispatchError/stallReason`
- 以及 `tasks_governance_samples.json` 中同任务的对应文本

是否出现这些 verdict markers：
- `结论：准奏 / 结论：封驳`
- `已准奏 / 已封驳`
- `允许进入尚书省派发`
- `请补齐后再报`
- `审议完成，封驳 / 审议完成，准奏`
- `未附中书省方案正文，无法审议 / 方案正文缺失`

也就是说，这个 guard 防的不是“任务疑似已经在门下省”，而是：

> **任务文本里已经出现了明确、可判定的门下审议结论。**

#### 2.2 当前这条任务为什么没被它拦住：因为 scheduler scan 看到的根本不是 `Menxia` 任务
本轮再次对位现场三层：
- `tasks_source.json`
  - `state = Zhongshu`
  - `sourceLayer = backend_export`
  - `progress_log = []`
  - `flow_log` 只有创建与 `Taizi -> Zhongshu`
- `tasks_runtime_view.json`
  - `state = Menxia`
  - `org = 门下省`
  - 但这是侧车观察层
- `tasks_governance_samples.json`
  - **根本没有这条任务**

所以当前真正驱动 `handle_scheduler_scan()` 的主任务视图里，这条任务满足的是：
- `state == 'Zhongshu'`
- 没有门下 verdict 文本
- `_scheduler = {}`
- `progress_log = []`

那它自然不会命中：
- `state == 'Menxia' and _task_has_menxia_verdict(task)` 这条 suppress 分支

因此更准确的说法是：

> **现网不是“没有重复送审保护”，而是现有保护只对“主任务视图已经进入 Menxia 且已有明确门下结论”的任务生效；而这条任务在主视图里仍停在 Zhongshu，所以 guard 根本没有机会触发。**

### 3. 这也让“为什么系统明明知道 Menxia，却还是继续派 Zhongshu”彻底说通了
到这一轮为止，逻辑已经闭环：

1. runtime_view 里确实“知道”这条任务到了 `Menxia`；
2. 但 runtime_view 是侧车观察层，不是主状态；
3. backend 主状态仍是 `Zhongshu`；
4. export 再把这个 `Zhongshu` 写回 `tasks_source.json`；
5. scheduler scan 只基于主视图判断；
6. 现有 menxia repeat-review guard 又只对 `state == Menxia` 的主视图任务生效；
7. 于是系统虽然“某一层知道 Menxia”，但**真正执行调度的那一层依然只看见 Zhongshu**；
8. 结果就是继续重复派发到 `zhongshu`。

这不是简单的 if 漏写，而是：

> **抑制逻辑被挂在了“正确但更晚的一层状态”上，而调度实际使用的仍是更旧的主视图状态。**

### 4. 当前最准确的新结论
截至这一轮，最准确的表述应更新为：

> **runtime_view 只做侧车观察，基本属于本轮三层分离方案的设计结果；重复派发之所以没被现有 guard 拦住，不是因为 guard 不存在，而是因为它要求主视图任务已进入 `Menxia` 且出现明确审议 verdict，而当前真正驱动 scheduler scan 的主视图仍停在 `Zhongshu + backend_export + progress_log空 + _scheduler空`，因此 guard 根本没有命中机会。**

### 5. 如果继续往下做，后续已经变成明确的架构/策略选择
现在后续不再是“再找一个 bug”，而是明确的选择题：

1. **要不要让 runtime_view 对 scheduler 提供抑制信号**
   - 即便不反写 backend，也允许“同 taskId 的 runtime_view 已到 Menxia/Assigned”时，scan 暂停重派 Zhongshu；
2. **还是坚持只信主状态，但要更快把 backend 主实体推进到 Menxia**
   - 这就要求补正式回写桥，而不是继续让 runtime_view 只做展示；
3. **在桥未补齐前，现有 menxia repeat-review guard 还应增加一层前置抑制**
   - 不再只看 `state == Menxia`，也看 runtime_view 是否已有同 taskId 的更后态。

一句话收口：

> **现在已经能确定：双真相不是偶发现象而是阶段性设计产物；而重复派发没被现有 guard 拦住，也不是 guard 不存在，而是 guard 挂在 Menxia 主状态层，当前 scheduler 实际消费的却仍是 Zhongshu 旧主视图。**


---

## 2026-05-05 再继续下钻：聚合规则本身并不是“旧态必然压新态”，但这条任务根本没进入 governance sample

这一轮专门盯 `rebuild_task_views.py` 和 `sync_governance_samples.py` 的优先级逻辑后，能够把一个重要误判再排掉一层：

> **当前问题不应再简单表述为“聚合策略死保旧主状态”。**

更准确的说法是：

1. 聚合规则本身确实有“谁更新鲜谁优先”的设计；
2. 但 **这条任务根本没有进入 `tasks_governance_samples.json`**；
3. runtime_view 只是侧车；
4. 因此主聚合视图最终只剩 backend_export 的旧主状态可用，runtime 的 Menxia 没有合流入口。

### 1. `rebuild_task_views.py` 的优先级规则本身并不死板
本轮再次核对脚本，`dedupe()` 的合并规则是：
- 先按 `task_key` 去重；
- 比较 `sort_key()`（优先取：
  - `sampleLastSeenAt`
  - `updatedAt`
  - `sampleCapturedAt`
  - `pending_confirm.requested_at`
  - `sourceMeta.updatedAt`
）
- 对 `stateful_fields`（包括 `state/org/updatedAt/now/_scheduler/progress_log/flow_log/block/output`），只有在 **新对象更鲜或相等** 时才覆盖旧值；
- 对字典字段则做 merge。

这说明 rebuild 并不是“永远锁死旧的 backend_export”。如果更晚的治理样本或者 runtime 样本真的进来，并且时间戳更鲜，理论上是可以覆盖掉旧态的。

### 2. 真正的问题：这条任务没进 governance sample，所以聚合时没有第二来源可用
现场 `data/tasks_governance_samples.json` 里搜索这条任务 `bbbf369f-959b-484e-890d-9c28d56b748a`：
- **不存在**

这就意味着：

> **当前聚合只有 backend_export 这一条主来源可吃，runtime 侧并没有通过 governance sample 形成第二来源。**

于是最终结果就是：
- runtime_view 里“看见” Menxia；
- governance sample 没有这条任务；
- backend 主实体还在 Zhongshu；
- rebuild 只能把 backend_export 的旧主状态继续当作主视图来源。

### 3. `sync_governance_samples.py` 的设计，也解释了为什么这条任务没自然入样本
`sync_governance_samples.py` 当前的关键条件是：
- 它会从：
  - `runtime_view`
  - `legacy_tasks_source`
  - `mission_control`
  - `manual_parallel`
  这些 source 里抽取样本；
- 但样本的保留又依赖一组 governance markers /准入条件；
- 没有这些 marker 的纯推进态任务，可能不会被保留为 governance sample。

结合现场现状：
- 这条任务虽然在 runtime_view 里到了 `Menxia`；
- 但它并没有进入 sample 层；
- 于是样本层既无法作为 Menxia 证据，也无法反向影响 rebuild。

所以现在问题的精确表述应再补一句：

> **不是 runtime_view 没看见推进，而是 governance sample 层没有把这条推进态任务沉淀下来；没有 sample，就没有第二来源，rebuild 只能继续依赖 backend_export 旧态。**

### 4. 这也解释了为什么现在 runtime_view 看起来“知道得更多”，但系统主链依旧没变
这条链目前实际上是：

1. `sync_from_openclaw_runtime.py` 语义推断出 Menxia，写到 runtime_view；
2. 但 `sync_governance_samples.py` 没把这条任务保留为 governance sample；
3. `rebuild_task_views.py` 因为缺少第二来源，只能继续吃 backend_export 的主任务旧态；
4. `refresh_live_data.py` 再忠实暴露 `taskSource=backend_api_export`；
5. dashboard scan 继续根据旧主视图重复派发。

所以 runtime_view 的提升没有形成闭环，不是因为它的内容不对，而是：

> **它没有被样本层接住，也就没能成为主聚合链的输入。**

### 5. 当前最准确的结论应再修正一层
此前我们已经收紧到：
- 双真相是阶段性架构产物；
- guard 没命中；
- runtime_view 是侧车。

这一轮再往下收紧，最准确的说法应变成：

> **这条任务之所以仍被重复派发，不是因为聚合规则不会选新，而是因为 runtime_view 的 Menxia 没有进入 governance sample，导致 rebuild 没有第二来源可用；主聚合最终只能继续以 backend_export 旧态为主，所以 dashboard 依然把它当作 Zhongshu 停滞任务。**

### 6. 后续如果要继续查，已非常具体
下一步不该再问“聚合规则是不是坏了”，而要问：

1. **为什么这条真实推进态没有被 `sync_governance_samples.py` 收进样本层；**
2. **是样本准入 marker 太严，还是 session 文本没形成样本；**
3. **如果要让 Menxia 真正影响主链，是补样本准入，还是补正式回写桥，还是两者都要。**

一句话收口：

> **现在可以明确：聚合规则本身并非无脑保旧；真正断在更前一层——这条任务没有进入 governance sample，所以 runtime_view 的 Menxia 没有第二来源承接，主视图自然仍由 backend_export 旧态主导。**
