# edict closeout

> 快速接手先看：`docs/current-progress-board.md`。
> 本文件保留完整收口证据与长版结论；`current-progress-board.md` 负责持续跟进板与最新阻塞摘要。

更新时间：2026-04-30 05:45（北京时间） / 现场复核时间：2026-04-30 05:45（北京时间） / system `date`：2026-04-30 05:45:28 CST (+0800) / 本轮已完成最小面 systemd 回滚演练并回切

## 1. 当前主线状态

### 1.0 最终定性（本轮收口结论）
- **主线当前可定性为：工程收口基本完成；能力闭环已基本坐实，backend host-native 已进入生产 dual/export 过渡态并出现真实导出证据；前台关键写链 smoke 与 systemd 回滚演练已补齐实操证据，当前尾项转为继续观察 dual/export 稳定性、自然样本厚度与最终验收。**
- 本轮已补单独完成度清单：`docs/edict-completion-status-20260426.md`，用于区分“主线基本收口”与“整个路线图未全完”两种问题。
- 已经确认收口的部分包括：
  - 前端/后端主链与 12 面板现实口径已对齐
  - 正式审稿稿 / 分工推进稿已补落盘
  - `PendingConfirm / gate_checks / templateId/templateParams/targetDept` 已做过可逆 probe，链路可用
  - 尚书省显式派部链路已补齐：`Assigned/Next/Doing` 可在看板内直接派到真实六部，不再只靠“推进下一步”隐式猜路由
  - 模型配置真实来源与应用链路已核清，不再误写成 `config.yaml`
  - backend cutover 的 feature flag、入口壳与兼容导出链已落地，且已有独立实施稿 `docs/plans/2026-04-28-backend-cutover-minimal-rollout.md`
- 当前真正仍未收口的部分有两类：
  - **backend host-native 已进入生产 dual/export 过渡态，但仍未完成最终验收**：现网 `edict-dashboard.service` 已注入 `EDICT_TASK_WRITE_MODE=dual`、`edict-loop.service` 已注入 `EDICT_ENABLE_BACKEND_EXPORT=true`，`live_status.json.taskSource` 已切到 `backend_api_export`；当前 backend 样本仍薄，且虽已补到登录态前台关键写链 smoke（`POST /api/auth/login`、`/api/create-task`、`/api/task-todos`、`/api/advance-state`、`/api/review-action`、`/api/dispatch-task` 已有真实现网证据），同时也已确认 `scripts/safe_update.sh` + `tests/test_safe_update_script.py` 已覆盖备份/确认令牌/rollback 入口骨架；此外本轮已按最小风险边界真实执行一轮 systemd 回滚演练并完成回切，已拿到 dashboard `dual -> json`、loop 去掉 backend export、再恢复 `dual/export` 的现场实操证据，相关备份/doctor/HTTP/数据截面已留存在 `/root/.hermes/backups/rollback-drill-20260430-053642/`，所以当前尾项已不再是“缺回滚演练实操证据”，而是继续观察 dual/export 稳定性与自然样本厚度，之后再做最终验收判断。
  - **生产运行态尚未出现充分的自然治理样本**，因此不能把“能力已实现”直接表述成“线上已有充分自然验证”

### 1.1 已确认落地
- React 看板已作为当前运行态前端入口；`dashboard/server.py` 实际提供 `dashboard/dist/` 构建产物，README/截图说明已同步到该现实。
- 北京时间 2026-04-28 04:46 再次直抓 `http://127.0.0.1:7892/` 当前服务出的真实 bundle，命中：`待批专面板`、`急递铺 / 国史馆`、`朝堂议政`、`走势总览`、`能臣`、`需训练`、`显式派给六部`；当前 JS 路径为 `/assets/index-D01zPxfi.js`。
- 看板当前按 12 个功能面板口径维护，README / ROADMAP 已写明 `待批专面板 / 急递铺 / 国史馆` 已进入真实运行态口径。
- `急递铺`、`国史馆`、`待批专面板` 的 README / ROADMAP 现实同步已完成，当前文档口径与代码口径基本一致。
- 模型配置面板当前并不是直接读取某个 `config.yaml`；它读取 `data/agent_config.json`，其中 `knownModels` / `defaultModel` 由 `scripts/sync_agent_config.py` 从 `/root/.openclaw/openclaw.json` 同步生成。
- `docs/JJC-20260416-001-sansheng-governance-executable-review.md` 与 `docs/JJC-20260416-001-task-division-plan.txt` 已补落盘，原先 `deliverables/...` 缺失问题已收口。
- 已完成一轮**可逆运行 probe**：临时注入 `PendingConfirm` / `gate_checks` / `templateId` 样本，验证 `approve -> Done`、`reject -> Zhongshu(review_round=1)` 与 template 字段保留后，已继续追修治理样本聚合中的 stale 字段残留；现场曾遗留临时样本 `PROBE-GOV-20260426`，本轮已确认从 `tasks_governance_samples.json` / `tasks_source.json` / `live_status.json` 全部清除。
- 本轮还补修并跑通了模型配置链路的三层真实根因：
  - `scripts/apply_model_changes.py::_agent_effective_model()` 过去会把“唯一 fallback”误判成 agent 当前有效模型，导致“切到 fallback 模型”被当成 no-op
  - 同脚本过去会先原地改 `cfg`，再计算 `old_text`，导致真实变更被误判为 `writeSkipped`
  - 生产现场还存在**并发执行 + 外层超时不一致**：`dashboard/server.py` 与 `scripts/run_loop.sh` 都可能触发 `apply_model_changes.py`，其中 loop 每 15 秒轮询且原先对该脚本只有 30 秒超时，曾实测把真实成功中的重启误打成 timeout/rollback，并让第二个执行者覆盖 `last_model_change_result.json`
  - 现已新增 `tests/test_apply_model_changes_regression.py`，并与 `tests/test_sync_agent_config.py::test_apply_model_changes_persists_agent_model_and_records_result` 一起实跑通过（合计 `4 passed`）
  - 另外已把 `apply_model_changes.py` 增补单实例锁、把内部 gateway restart timeout 提到 `60s`，并同步把 `dashboard/server.py` 的 apply 超时提到 `75s`、`scripts/run_loop.sh` 对 `apply_model_changes.py` 的单脚本超时提到 `75s`
- 北京时间 2026-04-26 18:20–18:21 已完成一轮**真实运行态双向 model change probe**（`taizi`）：
  - `faker/gpt-5.4 -> longcat/LongCat-Flash-Chat`：`openclaw.json` 中 `taizi.model` 已真实写入 fallback，`data/agent_config.json` 同步反映 fallback，`last_model_change_result.json` 记录 `gatewayRestarted=true / rolledBack=false`，Gateway PID 从 `3349443 -> 3386759`
  - `longcat/LongCat-Flash-Chat -> faker/gpt-5.4`：`openclaw.json` 中 `taizi.model` 已按预期移除并回落默认主模型，`data/agent_config.json` 同步回到 `faker/gpt-5.4`，`last_model_change_result.json` 记录 `gatewayRestarted=true / rolledBack=false`，Gateway PID 再次切到 `3389274`
  - 说明“pending 变更 → apply_model_changes.py → gateway restart → sync_agent_config.py → 面板消费数据”这条链路现在已拿到真实闭环证据，不再只是源码/单测口径
- 为让修复真正进入运行态，北京时间 2026-04-26 18:21 已重启 `edict-dashboard.service` 与 `edict-loop.service`；当前两者均为 `active`，新 PID 分别为 `3393100 / 3393103`
- 本轮已开始落地“自然治理样本补厚”的 Phase 1 数据分层：
  - `scripts/sync_from_openclaw_runtime.py` 改为单独输出 `data/tasks_runtime_view.json`
  - 新增 `scripts/sync_governance_samples.py`，把命中 `pending_confirm / gate_checks / review_round / template* / autopsy / notifications` 的任务沉淀到 `data/tasks_governance_samples.json`
  - 新增 `scripts/rebuild_task_views.py`，把 runtime / governance samples / JJC archive 聚合回前端兼容出口 `data/tasks_source.json`
  - `scripts/refresh_live_data.py` 已补 `taskLayers.runtimeCount / governanceSampleCount / jjcArchiveCount`
  - `scripts/run_loop.sh` 与 `install.sh` 首次同步链路已接入新脚本顺序
- 本轮新增/补跑测试并已实跑通过：`tests/test_sync_governance_samples.py`、`tests/test_rebuild_task_views.py`、`tests/test_refresh_live_data_layers.py`、`tests/test_server.py`、`tests/test_sync_from_openclaw_runtime.py`、`tests/test_guard_openclaw_sessions.py`；本次 2026-04-28 04:46 reality-sync 复核又再次实跑通过，当前合并相关链路回归为 **56 passed**。
- 本轮又补齐了尚书省显式派部产品链路：
  - `dashboard/server.py` 新增 `POST /api/dispatch-task`
  - `edict/frontend/src/components/TaskModal.tsx` 新增“🎯 显式派给六部”按钮
  - 已实跑 `python3 -m pytest tests/test_server.py tests/test_kanban.py -q`，结果 `39 passed`
  - 已实跑 `npm run build`，当前运行中 7892 端口实测服务新 bundle `/assets/index-BqspGD4Y.js`，其中已命中 `显式派给六部` 文案
- 本轮又把 runtime 残留问题继续收口到更贴近现场的一层：
  - 先前 `tasks_source.json` / `tasks_runtime_view.json` 中残留的 4 条 `OC-*` 都不是正式执行任务，而是 main session 噪音：`taizi` 只有 `HEARTBEAT_OK`，`zhongshu` 只有 `OK`，`shangshu / menxia` 则是 `sessions.json` 指向了不存在的 transcript 文件
  - 已给 `scripts/guard_openclaw_sessions.py` 补上 `missing_transcript_file` 检测，并修正 `rotate_entry()` 在轮转后真实创建空 transcript 占位文件，避免 cron 每 30 分钟重复轮转同一坏指针
  - 已给 `scripts/sync_from_openclaw_runtime.py` 补 runtime 过滤收口：对 `agent:*:main` 会话，若 transcript 缺失、activity 为空、或只有 `OK / HEARTBEAT_OK` 这类 bootstrap/heartbeat 回声，则不再进入前台 runtime 视图；只有存在真实 activity 的 main session 才保留
  - 对应回归已补并实跑通过：`pytest -q tests/test_guard_openclaw_sessions.py` -> `3 passed`，`pytest -q tests/test_sync_from_openclaw_runtime.py` -> `9 passed`
  - 北京时间 2026-04-26 18:46 左右再次执行 `python3 scripts/guard_openclaw_sessions.py --apply` 后，最新 dry-run 已为 `totalIssues=0`；随后重刷 `sync_officials_stats.py -> sync_from_openclaw_runtime.py -> rebuild_task_views.py -> refresh_live_data.py`，现场三层统计已收口为：`tasks_runtime_view.json=0`、`tasks_governance_samples.json=1`、`tasks_source.json=10(无 OC-*)`、`live_status.taskLayers.runtimeCount=0`
  - 因此当前六部不起的现场根因，已不能再归咎于 runtime 看板残留；现阶段运行面已经干净，主线缺口重新收敛回“自然治理样本仍薄，尚需继续补厚”
- 本轮又补了一次 **scheduler 内部巡检实测**（北京时间 2026-04-26 14:44 左右）：从上游 `tasks_governance_samples.json` 注入可逆 probe，经 `scripts/rebuild_task_views.py` 聚合后，已在 `edict-dashboard.service` 日志中实测命中 `PROBE-GOV-SCHED-HERMES-20260426T064303Z`，同秒出现 `🔍 定时巡检：1 个动作`；样本 `_scheduler.retryCount` 从 `0 -> 1`、`lastDispatchTrigger=taizi-scan-retry`、`flow_log` 追加 `停滞717秒，触发自动重试第1次`，随后已从 `tasks_governance_samples.json` / `tasks_source.json` 清理，无现场残留。
- 本轮又完成一轮 **OpenClaw 官方参数与 main session 自愈加固**：按 `docs.openclaw.ai` 的 `session-management-compaction / memory / configuration-reference` 口径，把 `/root/.openclaw/openclaw.json` 调整为 `agents.defaults.contextTokens=131072`、`compaction.reserveTokensFloor=24000`、`compaction.reserveTokens=24000`、`compaction.keepRecentTokens=50000`、`compaction.memoryFlush.softThresholdTokens=6000`、`contextPruning.mode=cache-ttl(ttl=1h)`、`session.reset={mode:daily, atHour:4, idleMinutes:240}`。
- 同轮核到：OpenClaw `2026.3.28` 运行时代码里已存在 `resetSessionAfterCompactionFailure` 自动 reset helper，但现场 `menxia / shangshu / zhongshu` 三条 main session 曾先后出现 `sessionId != sessionFile` 脏指针、缺 transcript 指针或旧 transcript context overflow；现已通过 `scripts/guard_openclaw_sessions.py --apply` 做了可逆轮转，最新 dry-run 为 `totalIssues=0`。
- 已新增 `scripts/guard_openclaw_sessions.py` 与 `tests/test_guard_openclaw_sessions.py`，并扩展到可检测 `missing_transcript_file`、轮转时自动创建空 transcript 占位；当前对应回归为 `3 passed`。
- 已新增本机守护定时：Hermes cron `217551f91436 / openclaw-session-guard`，每 30 分钟执行 `python3 /root/.openclaw/workspace/edict/scripts/guard_openclaw_sessions.py --apply`，用于后续自动轮转再次出现的坏 main session。
- 用户随后已明确批准重启；北京时间 2026-04-26 16:47 已执行 `systemctl --user restart openclaw-gateway`，新 PID 为 `2637539`，`openclaw gateway status` 已返回 `RPC probe: ok / Listening: 127.0.0.1:18789 / Runtime: running`。
- 重启后又对 `agent:zhongshu:main` 做了一次最小实测：执行 `openclaw agent --agent zhongshu --message '健康检查：只回复 OK；不要调用工具；不要对外发送。' --json`，session `3fd24268-59c9-4256-8eca-6f8a1b730259` 已真实写回 `contextTokens=131072`、`modelProvider=faker`、`model=gpt-5.4`、`status=done`，assistant 返回 `OK`；说明新参数已在真实 main session 生效，不再沿用旧的 `200000` 上下文预算。
- 重启后再次执行 `python3 scripts/guard_openclaw_sessions.py`，最新 dry-run 仍为 `totalIssues=0`。

### 1.2 本轮模型配置核实结论
- 当前 OpenClaw 主配置文件：`/root/.openclaw/openclaw.json`
- 当前默认主模型：`faker/gpt-5.4`
- 当前默认回退模型：`longcat/LongCat-Flash-Chat`
- 当前已显式补齐：`agents.defaults.contextTokens = 131072`
- 当前 `agents.defaults.models` 已登记：
  - `longcat/LongCat-Flash-Chat`
  - `faker/gpt-5.4`
- 当前 `models.providers` 已配置 provider：
  - `longcat`
  - `faker`
- `scripts/sync_agent_config.py` 会：
  - 内置一批 `KNOWN_MODELS`
  - 再把 `openclaw.json` 里的 `defaults.model`、`defaults.models`、各 agent model、各 provider models` 合并进 `knownModels`
  - `agent_config.json` 中每个 agent 的当前 `model` 取自 `agents.list[*].model`，若该 agent 未单独覆写，则回落到 `agents.defaults.model.primary`
- `edict/frontend/src/components/ModelConfig.tsx` 优先读取 `agentConfig.knownModels`；只有接口没给值时才退回前端硬编码 `FALLBACK_MODELS`
- `dashboard/server.py::POST /api/set-model` 会把变更写入 `data/pending_model_changes.json`，异步执行 `scripts/apply_model_changes.py`，随后再跑 `scripts/sync_agent_config.py`
- `scripts/apply_model_changes.py` 会：
  - 备份 `/root/.openclaw/openclaw.json`
  - 把目标 agent 的 `model` 写入 `agents.list[*].model`（若设置值等于默认主模型，则删除该字段以回落默认）
  - 执行 `openclaw gateway restart`
  - 记录 `data/last_model_change_result.json` 与 `data/model_change_log.json`

### 1.3 当前实际数据快照
- 当前快照：
  - `/root/.openclaw/openclaw.json` 中 `agents.defaults.model.primary = faker/gpt-5.4`
  - `agents.defaults.model.fallbacks = [longcat/LongCat-Flash-Chat]`
  - `agents.defaults.contextTokens = 131072`
  - `taizi / zhongshu / menxia / shangshu` 等核心 agent 当前默认仍未单独写 `model` 字段，因此实际继承默认主模型
- 本轮已做过两段真实链路验证，并最终补齐稳定运行证据：
  - 早先第一次直接双连打 probe 时，曾出现一次“日志显示 `taizi: longcat/LongCat-Flash-Chat → faker/gpt-5.4`，但 `last_model_change_result.json` 与现场状态互相打架”的假象
  - 复盘后确认那不是模型写回逻辑本身又坏了，而是 **`scripts/run_loop.sh` 也会每 15 秒兜底触发一次 `apply_model_changes.py`**，再叠加 loop / server 对该脚本原先都只给 `30s` 外层超时，导致并发执行者可能覆盖 `last_model_change_result.json`，还会把真实进行中的 gateway restart 误判成 timeout/rollback
- 针对这个生产根因，本轮已补：
  - `apply_model_changes.py` 单实例锁，避免 loop / server / 手工执行并发重入
  - `apply_model_changes.py` 内部 `openclaw gateway restart` timeout：`30s -> 60s`
  - `dashboard/server.py` 对 `apply_model_changes.py` 的外层 timeout：`30s -> 75s`
  - `scripts/run_loop.sh` 对 `apply_model_changes.py` 的单脚本 timeout：`30s -> 75s`
  - 随后已重启 `edict-dashboard.service` 与 `edict-loop.service` 让修复生效
- 北京时间 2026-04-26 18:20–18:21 又完成一轮**干净的真实双向 probe**（`taizi`）：
  - `faker/gpt-5.4 -> longcat/LongCat-Flash-Chat`
    - `apply_model_changes.py` 日志：`gateway restart rc=0`
    - `openclaw.json` 中 `taizi.model = longcat/LongCat-Flash-Chat`
    - `data/agent_config.json` 中 `taizi.model = longcat/LongCat-Flash-Chat`
    - `last_model_change_result.json`: `gatewayRestarted = true`、`rolledBack = false`
    - Gateway PID：`3349443 -> 3386759`
  - `longcat/LongCat-Flash-Chat -> faker/gpt-5.4`
    - `apply_model_changes.py` 日志：`gateway restart rc=0`
    - `openclaw.json` 中 `taizi.model` 已删除，按预期回落默认主模型 `faker/gpt-5.4`
    - `data/agent_config.json` 中 `taizi.model = faker/gpt-5.4`
    - `last_model_change_result.json`: `gatewayRestarted = true`、`rolledBack = false`
    - Gateway PID：`3386759 -> 3389274`
- 结论现已更新为：**“写 pending -> apply_model_changes.py -> gateway restart -> sync_agent_config.py -> 面板消费数据” 这条模型配置链路已拿到真实运行态闭环证据。**
- 因此当前更准确的判断是：
  - “应用后会触发 gateway restart” 已不再只是 UI 口径，而是有真实 PID 变更证据
  - “每个 Agent 独立切换后会稳定持久写入并在面板反映” 对 `taizi` 这条实测链路已成立
  - 剩余注意点主要转为：前台 `/api/set-model` 仍受 dashboard 登录态保护，若未来要补“前台点按钮”的 end-to-end 截图/录屏证据，需要带认证再实测

## 2. 关键文件定位
- 看板后端接口：`dashboard/server.py`
  - `GET /api/agent-config`
  - `POST /api/set-model`
- 模型配置前端：`edict/frontend/src/components/ModelConfig.tsx`
- 同步逻辑：`scripts/sync_agent_config.py`
- 应用模型变更：`scripts/apply_model_changes.py`
- 运行时主配置：`/root/.openclaw/openclaw.json`
- 面板消费数据：`data/agent_config.json`

## 3. 关于“是否可沿用当前 config.yaml”的明确结论
- **结论：不能表述为“沿用当前 config.yaml”。**
- 原因：edict 模型配置链路当前实际不依赖 repo 内某个 `config.yaml`；它依赖的是 `/root/.openclaw/openclaw.json -> scripts/sync_agent_config.py -> data/agent_config.json -> React ModelConfig`。
- 若后续文档要写准：
  - 应写“沿用当前 OpenClaw 运行配置（`/root/.openclaw/openclaw.json`）”
  - 不应写成“沿用当前 config.yaml”

## 4. 待继续推进事项
1. 持续观察 `tasks_source.json` 的自然样本增长，重点盯：`pending_confirm`、`gate_checks`、`review_round`、`templateId/templateParams/targetDept`。
   - 截至 2026-04-26 05:04（北京时间）当前观测：刷新循环持续健康运行，`/tmp/sansheng_liubu_refresh.log` 连续显示 `sync_runtime synced 32 tasks`、`refresh updated live_status.json (32 tasks)`，但 `tasks_source.json` 仍固定为 32 条 `Done` 任务，相关治理字段自然样本仍为 0。
   - 这说明当前缺口不是“刷新没跑”，而是“上游运行态尚未产生新的治理类任务样本”。
2. 已确认当前自然样本缺失的源码级原因链（旧链路）：
   - `scripts/sync_from_openclaw_runtime.py` 每轮都会重写 `data/tasks_source.json`
   - 它先从 `~/.openclaw/agents/*/sessions/sessions.json` 映射 runtime 会话，再按 `should_keep_runtime_task()` 过滤，只保留活跃/异常 runtime 会话
   - 随后又会把 `tasks_source.json` 中**已有的全部 `JJC-*` 旨意任务无条件并回去**
   - 当前现场实测 `tasks_source.json` 为 `JJC=32 / OTHER=0 / Done=32`，说明现有任务源基本被历史旨意任务占满；runtime 会话虽然存在，但并未沉淀出带治理字段的新任务样本
   - 因而当前问题应定性为：**任务源结构与过滤策略导致自然治理样本未进入当前看板数据面**，不是治理字段代码不存在，也不是刷新循环中断
3. 本轮 Phase 1 已完成的改造：
   - `scripts/sync_from_openclaw_runtime.py` 改为单独输出 `data/tasks_runtime_view.json`
   - 新增 `scripts/sync_governance_samples.py`，从 runtime / legacy `tasks_source.json` / `mission_control_tasks.json` / `manual_parallel_tasks.json` 抽取治理样本，写入 `data/tasks_governance_samples.json`
   - 新增 `scripts/rebuild_task_views.py`，聚合 `tasks_runtime_view.json`、`tasks_governance_samples.json`、`tasks_jjc_archive.json` 回写前端兼容出口 `data/tasks_source.json`
   - `scripts/refresh_live_data.py` 已补 `taskLayers` 统计，供前端和排查时直接看到三层数量
   - `scripts/run_loop.sh` 与 `install.sh` 已接入新链路
   - 对应测试已补并实跑通过：`27 passed`
4. 下一轮优先继续盯真实运行态，而不是重复争论结构：
   - runtime 会话为什么没有稳定生成可保留的 `Doing/Review/Blocked` 治理任务
   - 哪些治理任务应直接写入 `tasks_governance_samples.json`，而不是只靠 session 映射碰运气
   - `should_keep_runtime_task()` 的过滤误伤已在本轮修掉：过去真实 `agent:*:main` 会话一旦超过 60 分钟进入 `Next`，就会被当成普通冷却任务筛掉；现已明确保留 24h 窗口内的 main session，并补回归测试
   - 截至 2026-04-26 18:46（北京时间）现场三层统计已更新为 `runtimeCount=0 / governanceSampleCount=1 / jjcArchiveCount=32`；`tasks_runtime_view.json` 与 `tasks_source.json` 中均已无 `OC-*` 残留，这说明当前 runtime 噪音问题已收口，后续重点应转回上游自然治理样本的生成与沉淀，而不是继续纠缠前台 runtime 条目为什么没消失
   - 后续若要继续扩大 runtime / 治理样本，方向应转为核查：为什么当前真实运行态没有继续沉淀出可保留的 main session activity，以及哪些治理节点应直接产出样本而不是只靠 session 映射碰运气
5. 持续扫描 README / ROADMAP / docs / deliverables 中仍把模型配置写成 `config.yaml` 来源、或仍写成“约5秒生效”的旧表述，并改成 `openclaw.json -> agent_config.json` 的真实链路与“通常约10秒，以运行态为准”的口径。
6. 后续若用户明确要求补“前台点按钮”的 end-to-end 证据，再进入：
   - 带 dashboard 登录态实测 `/api/set-model`
   - 核对前台状态提示、`last_model_change_result.json`、`/root/.openclaw/openclaw.json` 与 `data/agent_config.json`
   - 当前后端 apply/restart/sync/persistence 链路已完成 runtime 复核，这一步不再属于阻塞尾项
7. backend host-native 生产化虽已落地，但**当前更准确阶段是“生产 dual/export 过渡态已进入默认值，仍待最终验收”**，还不能直接称为“纯 backend 主链切换完成”。
   - 北京时间 2026-04-28 04:46 之后的新现场已回正：backend 常驻链健康，`edict-dashboard.service` 已注入 `EDICT_TASK_WRITE_MODE=dual`，`edict-loop.service` 已注入 `EDICT_ENABLE_BACKEND_EXPORT=true`。
   - 当前 `GET http://127.0.0.1:18000/api/tasks` 已返回非空样本（当前已见 `count=1`），`data/tasks_backend_export_meta.json` 已存在，`data/live_status.json.taskSource` 已切到 `backend_api_export`。
   - 这说明现网已不再是“锁在 JSON 主路”的旧状态，而是 backend 主写 / 兼容导出并存的生产过渡态。
   - 仍不能直接宣称“backend cutover 全部完成”的原因，不是默认值没切进去，而是：
     - backend 自然样本仍薄，当前仍以 probe/兼容导出证据为主；
     - 前台关键写入口 smoke 还没收口；
     - systemd 回滚演练还没收口；
     - workspace 默认入口是否切到 `EDICT_KANBAN_ENTRY_MODE=auto/api` 仍需放在 dual/export 稳定之后评估。
  - 已落地的前置工作包括：
    - `scripts/kanban_update_legacy.py` 已创建；
    - `edict/scripts/kanban_update_edict.py` 的 fallback 已改成优先 legacy；
    - 根 `scripts/kanban_update.py` 已完成入口壳改造：默认仍走 legacy，不改现网行为，但已支持通过 `EDICT_KANBAN_ENTRY_MODE=api/auto/json` 转发到 wrapper；
    - 已新增 `scripts/export_backend_tasks_to_legacy_json.py`，可把 backend `/api/tasks` 兼容导出成 `data/tasks_source.json`，并写 `data/tasks_backend_export_meta.json` 标记来源；`scripts/refresh_live_data.py` 也已支持把该来源透传为 `live_status.json.taskSource/taskSourceMeta`；
    - 导出脚本默认带空结果保护：backend 返回 0 任务时不会覆盖现有前台兼容出口，只有显式设置 `EDICT_BACKEND_EXPORT_ALLOW_EMPTY=true` 才允许导出空结果。
  - 相关回归已补并跑通：入口壳 / fallback / export / refresh layer / flag wiring 等链路测试目前均已具备；本次 2026-04-28 04:46 复核补跑后，相关测试合计已达 `56 passed`。
  - 本轮已补一份更贴现网默认值的实施稿：`docs/plans/2026-04-28-backend-cutover-minimal-rollout.md`。
  - 当前更准确的下一步顺序应是：
   1. 持续核对 **dual + backend export** 在连续刷新周期内是否稳定；
   2. 前台关键写入口 smoke 已补到登录态真实闭环；后续改为持续抽查 create/todos/review/dispatch 在生产过渡态下是否继续稳定，并避免再把不存在的 `/api/task-progress` 误列为验收项；
   3. systemd 回滚演练已完成一轮真实 systemd 实操并已回切；当前已确认脚本/令牌门槛/服务单元现状都在，且已拿到 `dual -> json`、loop 去掉 backend export、再恢复 `dual/export` 的现场证据。后续重点从“有没有演练过”切换为“loop 回退窗口内兼容导出口径刷新是否足够及时”；现场执行稿仍见：`docs/plans/2026-04-30-systemd-rollback-drill-runbook.md`；
   4. 只有在 dual/export 稳定后，才评估 workspace 默认入口是否切到 `EDICT_KANBAN_ENTRY_MODE=auto/api`。

## 5. 下一次中断后建议入口
- 先读本文件
- 再读：`docs/governance-upgrade-map.md`
- 再执行 reality sync 扫描关键词：
  - `config.yaml`
  - `openclaw.json`
  - `agent_config.json`
  - `LongCat`
  - `gpt-5.4`
  - `待批专面板`
  - `急递铺`
  - `国史馆`
