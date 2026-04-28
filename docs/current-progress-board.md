# current progress board

更新时间：2026-04-28 20:48（北京时间） / system `date`：2026-04-28 20:48:00 CST (+0800)

> 本文件用于把 `docs/closeout.md` 与 `docs/governance-upgrade-map.md` 的主线结论压成一份持续跟进板。
> 目标不是重复全部长文，而是给阿爪/值守链一个**当前到哪了、卡在哪、下一步干什么**的统一入口。
> 另外自 2026-04-28 起，**所有系统改动（配置、服务、热修、回滚、守护脚本、运行态止血）默认都要同步汇总到 `docs/current-progress-board.md`**，避免后续出问题时现场分散、回溯找不到。

---

## 1. 一句话总览

**edict / 三省六部治理升级主线目前处于：工程收口基本完成，backend host-native 已进入生产 dual/export 过渡态并出现真实导出证据；但前台写链 smoke、自然治理样本厚度与回滚验收仍未收口。OpenClaw / taizi 本轮已完成直连 DM 结构性修复与 provider/session 去钉死清理，且在晚间重启窗口后已再次拿到多轮 `received message -> dispatching to agent -> dispatch complete` 真实样本；当前不再是“DM 完全断链”，而是收敛为 **taizi 直聊 session 长跑 + 偶发消息整理脏状态** 的不稳定态；`menxia:main` 为历史噪声项，而 `shangshu:main` 本轮已完成 dashboard 重入止血与定点 session recovery。**

---

## 2. 已汇总确认的主线完成项

### 2.1 治理升级与产品面
- 三省六部治理升级总表已形成：`docs/governance-upgrade-map.md`
- 主线收口文档已形成：`docs/closeout.md`
- 正式审稿稿、分工推进稿均已补到真实路径，不再引用不存在的 `deliverables/...`
- 尚书省显式派部链路已补齐：`Assigned / Next / Doing` 可直接显式派给真实六部
- `PendingConfirm / gate_checks / templateId / templateParams / targetDept` 已做过可逆 probe，能力闭环已验证
- worker stalled 分类、retry / escalate / blocked / autopsy 主链已落地，且已有测试与文档证据
- doctor / safe_update / memory_backup 等运维脚本已落地

### 2.2 数据层与运行态治理
- `tasks_runtime_view.json` / `tasks_governance_samples.json` / `tasks_source.json` 三层分离方案已落地
- runtime 噪音清理与 main session 过滤误伤已修正
- `scripts/guard_openclaw_sessions.py` 已落地，且有定时 guard 在跑
- OpenClaw main session 的 compaction / pruning / reset 参数已按官方口径收紧
- 关键回归测试在主线文档里已有通过证据，主线不再属于“从零开发阶段”

### 2.3 模型配置链路
- `openclaw.json -> apply_model_changes.py -> gateway restart -> sync_agent_config.py -> agent_config.json -> dashboard` 这条链路已拿到真实闭环证据
- 之前 `apply_model_changes.py` 的并发执行、超时误判、fallback 误判等问题已修过
- 旧的 `config.yaml` 口径已被纠正为 **`/root/.openclaw/openclaw.json` 才是当前真实配置源**

---

## 3. 仍未收口的主线缺口

### 3.1 backend host-native 已进入生产过渡态，但还没到最终验收
这块不能再写成“未切入默认值”，但也还不能直接吹成“纯 backend 主链已切完”。

当前已知事实：
- backend 常驻服务健康，`GET /api/tasks` 已返回真实列表
- 生产 `edict-dashboard.service` 已注入 `EDICT_TASK_WRITE_MODE=dual`
- 生产 `edict-loop.service` 已注入 `EDICT_ENABLE_BACKEND_EXPORT=true`
- `data/tasks_backend_export_meta.json` 已存在
- `live_status.json.taskSource` 已切到 `backend_api_export`
- `data/tasks_source.json` 当前已是 backend export 的兼容投影

#### 2026-04-28 15:18（北京时间）真实执行记录：backend host-native 最小 smoke
本轮没有再拿“测试通过”充结果，直接对现网 backend / legacy 路由打了一条最小真实 probe：
- probe legacy id：`PROBE-BE-20260428-151828`
- backend uuid：`cea48d95-fe4d-4f84-a655-4387f0cffec4`
- 标题：`[probe][backend-acceptance] dual-export smoke PROBE-BE-20260428-151828`

本轮**真实已覆盖**：
- `POST /api/tasks`：**201 Created**，现场创建成功；并确认 create 后初始态就是 `Taizi`，不是 `Pending`
- `GET /api/tasks/by-legacy/{legacy_id}`：**200 OK**，确认 legacy id 映射命中 backend 任务
- `PUT /api/tasks/by-legacy/{legacy_id}/todos`：**200 OK**
- `POST /api/tasks/by-legacy/{legacy_id}/progress`：**200 OK**
- `POST /api/tasks/by-legacy/{legacy_id}/transition`：**Taizi -> Zhongshu -> Menxia** 真实成功
- `POST /api/tasks/{uuid}/dispatch?agent=gongbu`：**200 OK**，backend 已受理 dispatch request
- 导出面证据仍在：`tasks_backend_export_meta.json` 存在，`live_status.json.taskSource=backend_api_export`

本轮**真实未覆盖 / 未通过**：
- 前台 dashboard 写入口已补到登录态真实 smoke：匿名直打 `POST /api/create-task` 仍会返回 **401 未登录或会话已过期**，但带有效 `edict_token` 后，`POST /api/auth/login`、`POST /api/create-task`、`POST /api/task-todos`、`POST /api/advance-state` 已拿到真实现网证据；其中新建任务 `JJC-20260428-001` 已成功创建，随后又通过真实 UUID `a38d3eab-415d-4e08-8109-e8f84ca7fce6` 完成 `Taizi -> Zhongshu` 推进
- legacy `review-action`：**已在重启 backend API 后恢复路由并完成真实 smoke**；对 `PROBE-BE-20260428-151828` 现场 `POST /api/tasks/by-legacy/{legacy_id}/review-action` 返回 **200 OK**，任务状态从 `Menxia` 准奏推进到 `Assigned`
- legacy `dispatch-target`：**已在重启 backend API 后恢复路由并完成真实 smoke**；对 `PROBE-BACKEND-DIRECT-001` 现场 `POST /api/tasks/by-legacy/{legacy_id}/dispatch-target` 返回 **200 OK**，`assignee_org` 已真实改写为 `工部`
- 三面一致性本轮已补齐：`/api/tasks`、`data/tasks_source.json`、`live_status.json.taskSourceMeta` 当前都已追平到 `count=2`，且 `PROBE-BE-20260428-151828` / `PROBE-BACKEND-DIRECT-001` 的 `state`、`assignee_org`、`updatedAt` 已能跨三面对应；因此“导出未追平”不再是当前阻塞

结论：
- **backend 主写 / 兼容导出过渡态已经进入生产默认值**
- **现网已不再是“锁在 JSON 主路”的旧状态**
- **backend 原生 create / legacy get/todos/progress/部分 transition / backend dispatch 已拿到真实现网证据**
- **legacy review-action / dispatch-target 已在 backend 重启后恢复并拿到真实现网证据，三面一致性与 export 刷新也已追平，前台登录态写链也已补到关键闭环；但仍缺前台 progress 入口口径澄清与更多自然业务样本，当前阶段仍然只能叫“过渡态验收中”，不能叫“纯 backend 主链切换完成”**
- **当前看到的 backend 样本仍薄，而且主要还是 probe 证据；自然样本厚度仍需继续补**

关键坑点：
- 不能再按 `Pending -> Taizi` 的老预期写 smoke，现网 backend create 后初始态已直接是 `Taizi`
- 不能把匿名 dashboard POST 当成前台写链通过证据；这条链路有认证门槛，必须先登录拿 `edict_token`
- 不能再把 `/api/task-progress` 当成前台写入口验收项；当前 dashboard 服务端并不存在这条接口，真实可写入口至少已确认 `create-task`、`task-todos`、`advance-state`，且其中后两类状态推进接口吃的是**真实 UUID**，不是 legacy id
- 本轮已确认 `review-action` / `dispatch-target` 的前序 404 根因是 backend API 长时间未重启，未吃到 2026-04-27 的 legacy 路由改动；重启后 openapi 与真实 smoke 已恢复

### 3.2 自然治理样本仍偏薄
- 能力已通过可逆 probe 与测试验证
- 但自然运行样本仍不厚，不能把“能力存在”硬说成“线上已充分自然验证”

---

## 4. 最新运行态专题：OpenClaw / taizi / windhub 阻塞

### 4.1 旧阻塞已基本止血
本轮排查后，下面两类旧问题已不再是当前主阻塞：
- `custom-ai-dcvx-cn/gpt-5.4` 本地鉴权缺口
- `faker/gpt-5.4` 持续 401 / 503 脏错误

现场依据（已在上轮排查中确认）：
- taizi 主会话、DM 会话、cron 会话都已切到 `windhub / gpt-5.4`
- 热加载后未再看到新的 `No API key found for provider "custom-ai-dcvx-cn"`
- 热加载后未再看到新的 faker token invalidated / account deactivated / auth_unavailable 脏错误

### 4.2 新的实质阻塞
**当前真正卡住的是：taizi 直连 DM session 持续长跑、其 `.jsonl.lock` 仍由 live gateway PID 257506 持有且未彻底释放；与此同时，虽然晚间窗口已再次拿到多轮 `dispatch complete`，但会话层仍存在长持锁与偶发 `Removed orphaned user message ...` 脏状态，`menxia:main` 的历史 lane wait / self-lock 噪声仍是并行背景项。**

### 4.2.1 2026-04-28 晚间 `menxia:main` 重复送审止血记录（原因 / 过程 / 结果）
#### 原因
- backend probe 任务 `cea48d95-fe4d-4f84-a655-4387f0cffec4`（`[probe][backend-acceptance] dual-export smoke PROBE-BE-20260428-151828`）在 `tasks_source.json` 主任务镜像中一直停留在 `state=Menxia`、`_scheduler={}` 的初始送审态。
- 但 `tasks_governance_samples.json` 与 menxia 实际 transcript 已经多次给出正式结论：**❌ 封驳**，理由是“当前送审内容仅含任务ID与旨意，未附中书省方案正文；请补齐后再报”。
- 旧版 dashboard guard 只看 `tasks_source.json` 主任务字段，没吸收 governance sample 里的 verdict，于是 `dispatch_for_state(..., 'Menxia')` / scheduler retry 会继续把同一审议请求反复送进 `agent:menxia:main`。
- 直接后果是：`agent:menxia:main` 旧主会话 `12583d5f-bb7b-4457-8433-fe918e7359c2` 长时间 `status=running`，并在 `/tmp/openclaw/openclaw-2026-04-28.log` 中持续出现 `session file locked`、`lane wait exceeded` 与重复封驳回复。

#### 过程
- 已先给 `dashboard/server.py` 补第二刀 guard：`_task_has_menxia_verdict(task)` 不再只看 `tasks_source.json`，同时回读 `tasks_governance_samples.json`，识别 `结论：封驳 / 准奏 / 请补齐后再报 / 方案正文缺失` 等 marker。
- 已补 focused test，验证“主任务无 verdict、仅 governance sample 有 verdict”时也会抑制 menxia 重投；`python3 -m pytest -q tests/test_server.py -k 'menxia_repeat_review or menxia_task_with_existing_verdict or sample_guard'` 通过（2 passed）。
- 已重启 `edict-dashboard.service`，确认新 PID 生效，切换到新 guard 运行态。
- 随后确认旧 `menxia` 锁文件已消失，但 `sessions.json` 里旧主会话仍残留 `status=running` 且 transcript 不再增长，判定为**假 running 残留**而非持续执行。
- 已先备份 `/root/.openclaw/agents/menxia/sessions/` 关键现场到：`/root/.openclaw/backups/20260428-191831-menxia-main-rotate`
- 已定向旋转 `agent:menxia:main`：
  - 旧：`12583d5f-bb7b-4457-8433-fe918e7359c2`
  - 新：`649f583a-4369-4ada-a9fa-9cc9b2315e60`
- 已清空该主会话的脏运行态字段，并重启 `systemctl --user restart openclaw-gateway`，新 gateway PID 为 `257506`。

#### 结果
- **运行态止血已落地**：重启后新 `agent:menxia:main` transcript 文件 `649f583a-4369-4ada-a9fa-9cc9b2315e60.jsonl` 已创建，但 8 秒复查保持 `0` 字节、无 `.lock`、`updatedAt` 不再跳，说明没有立刻再次自锁。
- **dashboard 重投源已切断**：旧 menxia 重复封驳的最后一条样本时间为北京时间 `19:04:08`；而 `edict-dashboard.service` 重启时间为 `19:04:14`。重启后到当前观测窗口，未再拿到新的 `cea48d95-fe4d-4f84-a655-4387f0cffec4 -> menxia` 重投证据。
- **OpenClaw gateway 已切到新进程**：`openclaw-gateway.service` 当前 live PID 为 `257506`，启动时间北京时间 `19:19:07`。
- **主任务镜像已补追平**：已在 live dashboard 载入新逻辑后，对 `cea48d95-fe4d-4f84-a655-4387f0cffec4` 触发一次 `manual-reality-sync` 级 guard 投影；当前 `data/tasks_source.json` 已同步写入：`now=门下省已封驳，等待中书省补正文后再报`、`block=门下省封驳：当前送审内容未附中书省方案正文，请补齐后再报`、`_scheduler.lastDispatchStatus=suppressed-repeat-review-guard`，并补了一条 `menxia-guard` progress_log 与 skip flow_log。至此，“运行态止血”与“主任务镜像追平”两层都已打通。

最新现场结论：
- Feishu P2P 入会漏处理问题当前不是主因；P2P 入站、received message、dispatching to agent、dispatch complete 已出现新闭环样本
- taizi 执行侧持续出现 `lane wait exceeded`
- 已见 windhub 运行态真实报错：
  - `provider=windhub error=400 Bad Request`
  - 后续又出现连续 timeout
- 但本轮进一步收紧后，已确认 timeout 里夹着更硬的会话级阻塞：
  - 同一 session `cabd269b-10c1-4812-903e-f64432592dde`
  - 同一锁文件 `cabd269b-10c1-4812-903e-f64432592dde.jsonl.lock`
  - 日志反复出现 `lane task error: lane=main ... session file locked`
  - 以及 `lane task error: lane=session:agent:taizi:main ... session file locked`
  - 还会被表层折算成 `model_fallback_decision ... reason=timeout`
- 这说明：
  - 旧的 custom/faker 问题大体已切走
  - **windhub 不稳仍在，但当前更硬的卡点已经包含 taizi 主会话 `.jsonl.lock` 竞争**
  - 当前阻塞点属于“执行/回复层不稳定 + 会话写入链互锁”，不是单纯消息入口问题

### 4.2.2 2026-04-28 晚间 `shangshu:main` 重入止血 + 定点 recovery 记录（原因 / 过程 / 结果）
#### 原因
- `dashboard/server.py::dispatch_for_state()` 旧逻辑会把 `Assigned / Review` 任务直接 `openclaw agent --agent shangshu ...` 灌进共享 `agent:shangshu:main`。
- 与 `taizi` 已有 main-session guard 不同，`shangshu` 原本没有同级保护；同时 scheduler retry 与 startup recovery 也会重复调用 `dispatch_for_state()`，导致共享主会话持续被重入。
- 现场锁文件 `/root/.openclaw/agents/shangshu/sessions/74b36d4d-6a8c-4ab9-a9da-6f6fcbcb0c75.jsonl.lock` 明确由 live `openclaw-gateway` PID `257506` 持有，说明不是孤儿锁，而是 live gateway 自锁。

#### 过程
- 已先备份 `dashboard/server.py` 到 `/root/.hermes/backups/edict-dashboard/`。
- 已在 `dispatch_for_state()` 中为 `shangshu` 补上与 `taizi` 同级的 `main-session guard`，让 dashboard 不再直接唤醒/派发 `shangshu main`。
- 已在 `_startup_recover_queued_dispatches()` 中对 `queued -> shangshu` 增加 suppress，避免服务重启后二次把 queued 任务重新灌入 `shangshu main`。
- 已重启 `edict-dashboard.service`，新 PID `1084297`，启动时间北京时间 `20:43:42`，确认运行态已吃到新代码。
- 随后对 `agent:shangshu:main` 做定点 session recovery：
  - 备份目录：`/root/.openclaw/backups/shangshu-main-recovery-20260428-204633/`
  - 旧主会话：`74b36d4d-6a8c-4ab9-a9da-6f6fcbcb0c75`
  - 新主会话：`12d72ced-5f3a-4bb9-8252-2f522d960dbd`
- 已清空新主会话的 `status/modelProvider/model/contextTokens/systemPromptReport.*` 等脏运行态字段，并重启 `systemctl --user restart openclaw-gateway`。
- gateway 重启后新 live PID 为 `1118485`，启动时间北京时间 `20:46:57`。

#### 结果
- **旧 `shangshu main` 锁已实际释放**：旧锁文件 `74b36d4d-6a8c-4ab9-a9da-6f6fcbcb0c75.jsonl.lock` 已不存在。
- **新 `agent:shangshu:main` 映射已生效**：`sessions.json` 当前已指向 `12d72ced-5f3a-4bb9-8252-2f522d960dbd`。
- **dashboard 侧重入源已被切断**：带认证 smoke 后，`cea48d95-fe4d-4f84-a655-4387f0cffec4` 的 `_scheduler.lastDispatchStatus` 已变为 `suppressed-main-session-guard`，`lastDispatchError=shangshu main 会话保护：dashboard 不再直接唤醒/派发 shangshu main`。
- `journalctl -u edict-dashboard.service` 已出现多轮明确现场证据：`自动派发跳过: shangshu main 会话保护已生效，避免与 gateway 主会话重入冲突`。
- **post-restart 新窗口未再看到旧 `shangshu` 锁 session id 复发**：`/tmp/openclaw/openclaw-2026-04-28.log` 在 `12:46:57Z` 之后未再出现旧 session id `74b36d4d-6a8c-4ab9-a9da-6f6fcbcb0c75`，也未再出现 `session:agent:shangshu:main` 的新 lock/failover 样本。
- 当前新 `12d72ced-5f3a-4bb9-8252-2f522d960dbd.jsonl` 仍为 `0` 字节、无 `.lock`，说明 recovery 后没有立刻再次自锁。

### 4.3 当前定性
- **消息进得来，而且 completion 也仍在继续出现**
- **当前不是“DM 完全断链”，而是 taizi 直聊 session 进入长跑/长持锁的不稳定态**
- **主问题已收敛到 live gateway 持有 direct session lock、会话迟迟不收口，以及偶发消息整理脏状态**

### 4.4 2026-04-28 taizi 定向修复记录（原因 / 过程 / 结果）
#### 原因
- 当前用户直连 DM 会话 `agent:taizi:feishu:direct:ou_ed2187f2ad27e0b7876913371e72c06a` 复用了坏状态 session `64bd724b-19f1-488c-ba60-270268fee672`
- 该 session 在 `sessions.json` 中带着过期的 `contextTokens=131072`，但 live 默认模型已是 `windhub/gpt-5.4`，当前窗口配置为 `200000`；属于 `stale_context_window_metadata`
- 同一会话在 14:12 先出现工具层错误：`write failed: Missing required parameter: path alias`
- 随后在 14:22 出现执行层真实失败：
  - `embedded_run_agent_end ... provider=windhub ... HTTP 524`
  - `embedded_run_failover_decision ... decision=surface_error`
- 对应 session transcript 最终落出 `assistant stopReason=error` 且 `content=[]` 的空回复记录，说明问题不只是入口，而是“坏会话复用 + 上游执行失败”叠加

#### 过程
- 已核实 edict live code 中 `dashboard/server.py` 对 `taizi` 的 `wake_agent()` 与 `dispatch_for_state()` 都已有 `taizi main 会话保护`，因此本轮不动 edict 任务数据、不动 dashboard 逻辑
- 已用 `scripts/guard_openclaw_sessions.py --all-sessions` 做 dry-run，确认 taizi 当前 DM 会话与 taizi main 都命中 `stale_context_window_metadata`
- 为避免误伤其他 agent，本轮未直接 `--apply --all-sessions`，而是只对当前用户直连 DM session 做定向旋转
- 已先备份：`/root/.openclaw/backups/session-fix-20260428-143546`
- 已将该 session key 从旧会话旋转到新会话：
  - 旧：`64bd724b-19f1-488c-ba60-270268fee672`
  - 新：`c187467b-89e3-481e-acd8-61ff0b58f39a`
- 新会话文件已创建，且新映射中的 `status/modelProvider/model/contextTokens/systemPromptReport` 等脏状态已清空

#### 结果
- **磁盘层修复已完成**：`sessions.json` 当前已指向新 DM session，旧坏 session 不再是默认映射
- **edict 主线未被改动**：本轮没有改任务数据、没有改 dashboard 调度逻辑、没有动 backend dual/export 现场
- 随后已执行 `systemctl --user restart openclaw-gateway`，live gateway 已切到新进程 `PID 1970076`，启动时间 `2026-04-28 14:50:44 CST`
- 旧坏 DM session `64bd724b-19f1-488c-ba60-270268fee672` 的 `.jsonl.lock` 已释放，说明旧进程占锁已清掉
- 新 DM session `c187467b-89e3-481e-acd8-61ff0b58f39a` 已开始真实写入，session 文件大小已从 `0` 增长到 `3247`，说明不只是磁盘映射切换，而是运行态已接管

#### 验收证据（重启后真实样本）
- `14:54:16`：`p2p chat entered`
- `14:54:19`：`received message from ou_ed2187f2ad27e0b7876913371e72c06a`
- `14:54:19`：`dispatching to agent (session=agent:taizi:feishu:direct:ou_ed2187f2ad27e0b7876913371e72c06a)`
- `14:55:04`：`dispatch complete (queuedFinal=true, replies=1)`

结论：本次 taizi 修复**曾**拿到重启后真实 DM 闭环证据，但该结论现在不能继续按“已恢复、只需监测”沿用。15:10 之后现场再次变坏，而且到 16:17 截面已可确认成“长时间卡住但偶发继续执行”的特征：当前用户直连 DM 会话 `agent:taizi:feishu:direct:ou_ed2187f2ad27e0b7876913371e72c06a` 仍指向 `c187467b-89e3-481e-acd8-61ff0b58f39a`，其 `status=running`、`contextTokens=131072` 到 16:17 仍未变化，对应 transcript `.jsonl.lock` 仍由**当前 live gateway PID 1970076** 持有且未释放，lock 文件时间仍是 15:10:41；进一步看 `/proc/1970076/fd`，当前能稳定确认的 live 持锁目标就是这条 taizi direct session lock，本轮未发现同 PID 此刻还同时打开多条 `.jsonl.lock` fd。更关键的是，拆开该 direct transcript 后已能坐实：**15:10:36 那次 `received message` / `dispatching to agent` 之后，这条 direct session 并不是没跑，而是一直卡在同一轮超长 assistant 执行里**——15:13 起连续发起 `memory_search`、`read`、`exec`、`write`、`edit` 等工具调用，15:31:15 首次撞上 `write -> Missing required parameter: path alias`，15:40:04 虽成功把 `review-correction-notes.md` 写入磁盘，但 15:43、15:45、15:49、15:53、16:01、16:12、16:17 仍继续跑后续工具并再次反复踩 `path alias` / `oldText alias` 参数坑；transcript 到 16:17 仍持续增长，却始终没有新的 `dispatch complete`。这也说明先前看到的 `p2p chat entered -> received message` 断层**不是 channel/session 解析层卡住**：从当日日志全量复核看，15:10 之后全局只出现过这一条 `received message`，而后续 15:11、15:14、15:18、15:24、15:50、16:12 的新增样本都只有 `p2p chat entered`，没有新的 message.receive 事件，因而更像“用户继续进入/打开 P2P 会话但没有新的消息事件”而不是“新消息在 channel 层丢了”。再往后，15:34:06 已出现新的 `embedded run timeout` + `embedded run failover decision ... reason=timeout`，到 16:09:04/16:10:33 又继续出现新的 `session file locked` 与新的 `embedded run timeout` / `embedded run failover decision`；其中最新 self-lock 热点日志落在 `agent:menxia:main`，但从当前 fd/lock 实查更像是**同一 gateway 进程内部阶段性打到 menxia 主会话报错**，而不是“现在手里稳定同时占着多把 menxia 锁”。因此当前最准确口径应改为：**真正的主 blocker 不是 Feishu channel ingress，而是 taizi 这条 direct session 被单轮超长执行 + 工具参数错误拖成持续 running / 持锁不释放 / 无新 dispatch complete 的脏会话；同时下游六部执行链也继续出现 live self-lock 与 timeout。** 本轮已按最小爆破面直接落修：北京时间 16:32 先备份 `/root/.openclaw/agents/taizi/sessions/sessions.json`、旧 transcript `c187467b-89e3-481e-acd8-61ff0b58f39a.jsonl` 与旧 `.lock` 到 `/root/.openclaw/backups/direct-session-rotate-20260428-163257/`，随后只旋转 `agent:taizi:feishu:direct:ou_ed2187f2ad27e0b7876913371e72c06a` 这一条 direct session 到新 `sessionId=3afd9434-7539-462e-96c4-c41903c976d9`，清掉 `status/startedAt/endedAt/contextTokens/modelProvider/model/systemPromptReport` 等脏运行态并创建新空 transcript；16:33 已执行 `systemctl --user restart openclaw-gateway`，服务重新拉起。重启后的结构性验收已通过：旧 lock `c187467b-89e3-481e-acd8-61ff0b58f39a.jsonl.lock` 已释放、`sessions.json` 已切到新 session、新 transcript 文件已存在且当前无新 lock。**但截至本次检查，新 direct session 还没拿到新的 `received message / dispatching / dispatch complete` 真实样本，所以当前状态是“结构修复已落地，等待重启后真实 DM 证明”，还不能直接宣告彻底恢复。** 后续优先动作已从“继续猜 channel 层”切换为：盯重启后的第一条用户直连消息是否进入新 session，并确认 `dispatch complete` 是否重新出现；同时继续盯 `menxia:main` 的独立 self-lock/timeout 噪声，不要再从 edict 主线功能缺口或 channel 解析层方向误判起手。

---

## 5. 给阿爪继续跟的优先级

### P0：先盯运行阻塞，不要跑偏
1. 继续盯 `windhub/gpt-5.4` 的真实运行态错误
   - 是否继续 400
   - 是否继续 timeout
   - 是否只有部分请求形态失败
2. 继续盯 `lane wait exceeded` 与主会话占锁热点
   - 重点先看 `lane=session:agent:menxia:main` 是否继续放大
   - `queueAhead` 是否持续非零
   - 是否存在单次失败把整条 lane 卡死
3. 继续盯 Feishu DM 真闭环
   - `received message`
   - `dispatching to agent`
   - `dispatch complete`
   三段都要看，不能只看入站

### P1：backend cutover 主线进入过渡态验收
1. 确认 `dual + backend export` 在连续刷新周期内稳定
2. 补前台关键写入口 smoke：create-task / progress / todos / review/approve / dispatch
3. 三面一致性当前已追平，后续改为持续抽查 backend `/api/tasks`、`data/tasks_source.json`、`live_status.json.taskSource/taskSourceMeta` 是否继续一致
4. 做 systemd 回滚演练：dashboard `dual -> json`、loop 去掉 backend export
5. 只有在 dual/export 稳定后，才评估 workspace 默认入口是否切到 `EDICT_KANBAN_ENTRY_MODE=auto/api`

### P1：自然治理样本继续补厚
- 持续观察 `pending_confirm / gate_checks / review_round / template* / autopsy`
- 区分“真实自然样本增长”与“临时 probe 验证”
- 不要再把 probe 成功误报成线上自然样本充分

---

## 6. 当前建议口径

对内统一按下面口径：
- **主线当前不是没做完，而是已进入收口阶段**
- **backend host-native 已切入生产 dual/export 过渡态，但还没完成最终验收**
- **custom/faker 旧阻塞大体止血，当前主阻塞已收敛到 taizi 直连 DM session 长跑、live gateway 持有 direct session lock 未释放，以及偶发消息整理脏状态；`menxia:main` 的 self-lock / lane wait 噪声仍需并行盯防**
- **现在要盯的是 taizi 直聊 session 何时收口、后续 `dispatch complete` 是否继续稳定出现、以及 `menxia:main` 是否再次放大，不要再把主要矛头放回 custom/faker**

---

## 7. 2026-04-28 17:08 后续清理：agent 本地 provider 固定层 + session 固定模型元数据批量去钉

### 本轮目的
- 用户要求不要只修 taizi，要把其他 agent 一并清干净
- 目标不是只看 taizi，而是让各 agent 尽量重新跟随 `/root/.openclaw/openclaw.json` 中 `agents.defaults.model.primary`
- 同时清掉会继续把运行态钉死的 session 级 `modelProvider/model/contextTokens` 残留

### 已执行动作
1. 先做批量盘点
   - 几乎所有 agent 本地 `agent/models.json` 都仍残留历史 provider：`custom-ai-dcvx-cn`、`faker`
   - 当前真正带着脏 session 固定元数据的主要是 `taizi`、`menxia`、`zhongshu`
2. 已备份到：
   - `/root/.openclaw/backups/provider-follow-cleanup-20260428-170752/`
3. 已批量清理各 agent 本地 `agent/models.json`
   - 删除历史 provider：`custom-ai-dcvx-cn`、`faker`
   - 保留 `windhub` 及其他仍需 provider
4. 已清理脏 session 固定元数据
   - 清空 `modelProvider`
   - 清空 `model`
   - 清空 `contextTokens`
   - 清空 `systemPromptReport.provider/model/contextTokens`
5. 已同步修正全局默认 context 窗口
   - `/root/.openclaw/openclaw.json`
   - `agents.defaults.contextTokens: 131072 -> 200000`
6. 已执行运行态重载
   - `systemctl --user restart openclaw-gateway`
   - 新进程：`PID 3235093`
   - 新启动时间：`2026-04-28 17:08:12 CST`

### 当前已确认结果
- `taizi / menxia / zhongshu / shangshu / main` 等 agent 本地 `models.json` 中，历史 `custom-ai-dcvx-cn` 已清掉
- `taizi / menxia / zhongshu / ...` 的 `sessions.json` 中，旧的固定 `modelProvider/model/contextTokens/systemPromptReport.*` 已清空
- 全局默认已明确为：
  - `agents.defaults.model.primary = windhub/gpt-5.4`
  - `agents.defaults.contextTokens = 200000`

### 仍需继续盯的点
- 重启后日志里暂未再次出现新的 `custom-ai-dcvx-cn` / `faker/gpt-5.4` 明确命中，但执行层错误噪声还在持续，需要继续盯真实 DM 闭环
- 本轮“去固定层/去 session 钉死态”已经落完，但**这不等于 taizi 交互链已自动恢复**；还需要继续验证：
  - `p2p chat entered`
  - `received message`
  - `dispatching to agent`
  - `dispatch complete`
- 若新窗口里仍无 `dispatch complete`，则主阻塞已从“provider 固定/旧 session 钉死”进一步收敛到执行链本身，而不是模型跟随机制

### 本轮判断
- 这次处理已经把“agent 本地固定 provider 层 + session 固定模型元数据”这条老钉子系统性拔掉了
- 后续若再切全局 `defaults.model.primary`，各 agent 不应再继续被 `custom-ai-dcvx-cn` / `faker` 这类历史本地层拖偏
- 但 taizi 当前线上是否真正恢复，仍要看重启后的**真实消息闭环样本**，不能把“配置已清干净”误报成“链路已恢复”

### 重启后补充实锤（17:17 以后）
- `taizi` 直聊 session `agent:taizi:feishu:direct:ou_ed2187f2ad27e0b7876913371e72c06a`
  - `modelProvider = null`
  - `model = null`
  - `contextTokens = null`
  - 说明 session 固定模型字段已被清空，后续运行将回落跟随全局 default，而不是继续被旧 session 元数据钉死
- 重启后真实日志已再次出现：
  - `p2p chat entered`
  - `received message`
  - `dispatching to agent (session=agent:taizi:feishu:direct:...)`
- 但**仍未看到新的 `dispatch complete`**，说明 taizi Feishu 直聊主链仍卡在执行/回写后半段，不是 ingress 入口问题
- `menxia` 主会话 `agent:menxia:main` 当前已重建为：
  - `modelProvider = windhub`
  - `model = gpt-5.4`
  - `contextTokens = 200000`
  - 说明模型配置层本身已跟上新全局 default
- 当前 live gateway `PID 3235093` 自己持有：
  - `/root/.openclaw/agents/menxia/sessions/12583d5f-bb7b-4457-8433-fe918e7359c2.jsonl.lock`
- 因此同时日志继续出现：
  - `lane=session:agent:menxia:main`
  - `session file locked`
  - `lane wait exceeded`
- 综合判断：当前新主阻塞已进一步收敛为 **gateway 内部在 `menxia` 主会话上的长跑/重入占锁**，而不是 `custom/faker` 历史 provider 漂移

- **现在要盯的是 windhub 执行链 / lane wait / menxia 主会话锁互撞，不要再把主要矛头放回 custom/faker**

---

## 8. 下次接手先读什么
1. 本文件：`docs/current-progress-board.md`
2. 详细主线结论：`docs/closeout.md`
3. 详细治理映射：`docs/governance-upgrade-map.md`

---

## 9. 额外复核结论
- `docs/current-progress-board.md` 已作为阿爪/值守链继续接手的短版总入口落地
- `docs/review-correction-notes.md` 已落地，当前用于记录：哪些口径已回正、哪些误报后续不能再犯、哪些问题仍需继续盯办
- 后续若再出现“backend 还没切进去”或“taizi 还没恢复”这类旧表述，优先先复核这两份文件当前内容，不要直接沿用旧轮结论
