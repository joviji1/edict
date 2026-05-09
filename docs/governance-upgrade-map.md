# 三省六部治理升级映射总表

> 快速接手先看：`docs/current-progress-board.md`。
> 适用任务：`JJC-20260416-001`
> 
> 目标：把“三省六部治理升级”从审稿稿压成可执行索引表，明确 **改哪里、为什么改、谁负责、怎么验收、优先级是什么**。
> 本文件保留治理映射全表；`current-progress-board.md` 负责持续跟进板与最新阻塞摘要。

---

## 1. 总体结论

本次升级不是重写 edict，而是在保留现有 **看板 / 状态机 / OpenClaw 多 Agent 落地** 基础上，补齐以下四类能力：

1. **制度治理补齐**：完整性 gate、审核 gate、派发 gate、SLA、超时分类、升级链。
2. **可运行运维补齐**：doctor、safe update、memory backup、systemd/日志巡检。
3. **失败治理补齐**：从“红灯提示”升级为“事件 → 督办 → 升级 → 验尸 → 记忆”的固定流程。
4. **索引与审计补齐**：把方案、模块、文件、职责、验收方式收口到统一总表。

---

## 2. 核心治理映射表

| 目标能力 | 来源体系 | edict 当前落点 | 当前状态 | 目标改造 | 负责人 | 优先级 | 验收方式 |
|---|---|---|---|---|---|---|---|
| 前台唯一入口（太子） | 阿爪治理 | `agents/taizi/`、消息入口链路 | 已有基础 | 固化“前台只接旨/回奏，不绕过台账”规则 | 太子 / 中书省 | P0 | 任意新任务都生成 task_id，并可追溯 flow |
| 中书完整性 gate | tiangong prompt stack | `agents/GLOBAL.md`、`agents/zhongshu/SOUL.md` | 已写入结构化规则 | 固化目标/边界/验收/SLA/责任部门/风险/回报格式 | 中书省 | P0 | 任意方案稿缺字段即不能进入门下 |
| 门下审核 gate | 三省制度 | `agents/menxia/SOUL.md`、`agents/groups/sansheng.md` | 已写入统一模板 | 固化 pass/reject/needs_info/split_required/risk_high 与整改条件 | 门下省 | P0 | 所有审核结论可归类并带整改/重审条件 |
| 尚书派发 gate | 三省制度 | `agents/shangshu/SOUL.md`、`agents/groups/sansheng.md`、`dashboard/server.py`、`edict/frontend/src/components/TaskModal.tsx` | owner/ETA/证据规则 + 显式派部入口已落地 | 固化 owner / ETA / 验收证据 / 升级路径，并允许在看板内直接显式派到六部 | 尚书省 | P0 | P0 任务无“无主项”，且 `Assigned/Next/Doing` 可显式落到真实六部 |
| 六层上下文收口 | tiangong context stack | `agents/GLOBAL.md`、各 SOUL | 部分存在 | 统一要求输出：结论、证据、下一步、是否需升级/验尸 | 中书省 / 门下省 | P0 | 任一关键节点输出可直接审计 |
| stalled 检测与自动重试 | edict 现有机制 | `edict/backend/app/workers/orchestrator_worker.py`、`dashboard/server.py` | 已有基础 | 保持现有重试/升级链，补原因分类和闭环 | 兵部 | P0 | 超时任务会触发 retry / escalation / blocked |
| stalled 分类 | tiangong 治理经验 | `orchestrator_worker.py`、`kanban_update.py autopsy`、`dashboard/server.py` | P0 已落地基础分类 | 保持 `no_heartbeat / dispatch_failed / provider_timeout / tool_error / permission_denied / waiting_dependency / loop_risk / unknown` 等分类并继续细化 | 兵部 / 刑部 | P0 | 任意 blocked/stalled 都有明确分类或 unknown 强制验尸 |
| 分身督办链 | tiangong / 阿爪后台督办 | `dashboard/server.py`、worker 流程 | 部分存在 | 后台 worker 负责催办/升级/留痕，不私改状态 | 尚书省 / 兵部 | P0 | 所有催办/升级动作写入 flow / audit |
| 验尸 autopsy | tiangong autopsy | `scripts/kanban_update.py autopsy`、`dashboard/server.py`、worker blocked 触发 | 已落地并有测试 | 对多次超时/失败任务生成 autopsy 草稿和模板 | 兵部 / 刑部 | P0 | Blocked 任务可产出根因报告 |
| 记忆提取 | tiangong memory | `data/agent_memory`、`data/task_memory` | 有数据，无固定机制 | Done/Blocked 后提取经验，形成复盘资产 | 吏部 / 中书省 | P1 | 典型任务可复盘并追踪经验 |
| 运维诊断 doctor | danghuangshang | `scripts/doctor_edict.sh` | 已落地 | 持续维护统一巡检 | 工部 | P0 | 一条命令输出关键服务健康信息 |
| 安全升级 safe update | danghuangshang | `scripts/safe_update.sh` | 已落地保守版 | 升级前自动备份与检查，真实重启/迁移仍需确认 | 工部 | P1 | 升级前后都有可追溯备份 |
| 记忆资产备份 | danghuangshang | `scripts/memory_backup.sh` | 已落地 | 默认备份到 `/root/.openclaw/backups`，避免 workspace 内递归 | 工部 | P1 | 关键 memory/task 数据可回滚 |
| 看板 stalled / autopsy 可观测性 | edict dashboard | `dashboard/server.py`、`edict/frontend/src/components/TaskModal.tsx` | P0 已补 autopsy 与 gate 展示/接口 | 持续增强超时分类摘要和命令面板 | 礼部 / 兵部 | P1 | 看板能区分“停滞原因/是否已升级/是否已验尸” |

---

## 3. 文件级索引

### 3.1 edict 关键目录

| 路径 | 用途 | 本次改造关注点 |
|---|---|---|
| `agents/` | 各部 SOUL、协作规则 | gate、输出格式、职责边界 |
| `docs/` | 架构与治理文档 | 补治理升级总表、超时治理章节 |
| `dashboard/` | 看板服务与展示层 | stalled / 升级 / autopsy 可观测性 |
| `scripts/` | 运行脚本、看板 CLI、同步逻辑 | doctor / backup / safe update / kanban 命令 |
| `edict/backend/app/workers/` | 编排 worker | stalled 分类、升级链、autopsy 触发 |
| `edict/backend/app/services/` | event bus / service 层 | 事件定义与回调逻辑 |
| `tests/` | 自动测试 | gate 与超时治理回归测试 |
| `data/` | tasks、memory、sync 数据 | 备份与恢复、记忆提取 |
| `install.sh` / `start.sh` / `edict.sh` | 安装与启动入口 | 统一职责边界与诊断/恢复入口 |

### 3.2 tiangong 关键参考模块

| 路径/能力 | 可借鉴点 | edict 落点 |
|---|---|---|
| prompt stack / context stack | 六层上下文、输出结构化 | `agents/GLOBAL.md`、各 SOUL |
| autopsy | 失败根因固定化 | `orchestrator_worker.py` + `scripts/` + `docs/` |
| regime/config 模板 | 制度热切换与模板化 | `docs/` / `config` 规划层 |
| REPL / command panel | 看板命令面板化 | `dashboard/` / `scripts/kanban_update.py` |

### 3.3 danghuangshang 关键参考能力

| 能力 | 价值 | edict 落点 |
|---|---|---|
| doctor | 一键诊断 | `scripts/doctor_edict.sh` |
| safe-update | 安全升级 | `scripts/safe_update.sh` |
| memory-backup | 记忆资产保护 | `scripts/memory_backup.sh` |
| install / config 容错 | 降低部署失误 | `install.sh` / `edict.sh` |

---

## 4. P0 / P1 / P2 执行顺序

### P0：先收死“不会再丢、不会再误判”

1. 新增本文件 `docs/governance-upgrade-map.md`。
2. 在 `docs/task-dispatch-architecture.md` 补“超时治理与验尸”章节。
3. 在 `agents/GLOBAL.md` 补完整性 gate 与统一输出口径。
4. 新增 `scripts/doctor_edict.sh`。
5. 为 stalled / blocked 引入原因分类字段与模板。
6. 明确 flow / audit 中的催办、升级、验尸留痕要求。

### P1：把治理变成可运行机制

| 序号 | P1 项 | 当前证据 | 当前状态 | 真实缺口 | 建议归属 |
|---|---|---|---|---|
| 1 | `scripts/memory_backup.sh` | 文件已存在：`scripts/memory_backup.sh`；已改为默认备份到 `/root/.openclaw/backups`，避免 workspace 内递归复制自身 | 已落地，需保持回归验证 | 后续只需定期跑通备份与恢复提示；不是当前主阻塞 | 工部 |
| 2 | `scripts/safe_update.sh` | 文件已存在：`scripts/safe_update.sh`；现已升级为分阶段流水线：`plan / prepare / test / apply / restart / rollback`，并要求 `restart/rollback` 使用显式确认令牌 | 已落地增强版 | 后续可继续补 git pull / 依赖安装 / DB migration 的环境特定实现；但已做到“不确认不重启、不确认不回滚” | 工部 |
| 3 | worker stalled 分类、升级链、autopsy 触发 | `edict/backend/app/workers/orchestrator_worker.py`、`tests/test_orchestrator_stalled.py`、`tests/test_kanban_autopsy.py` 均已存在；真实任务已有 `autopsy.path/reason/generatedAt` 与 `_scheduler.stallReason` | 主链已基本落地 | 文档状态仍落后于代码；需要继续验证运行时 worker 是否加载最新代码，并把验收口径写回总表 | 兵部 / 刑部 |
| 4 | dashboard stalled/autopsy 可观测性 | `dashboard/server.py` / `edict/frontend/src/components/TaskModal.tsx` 已有 stalled、retry、escalation、autopsy、gate 展示与接口 | P0 已落地 | P1 继续增强命令面板和更细摘要 | 礼部 / 兵部 |
| 5 | 超时治理与 gate 回归测试 | stalled/autopsy/PendingConfirm/server 测试已存在；GLOBAL/SOUL/groups 已补规则 | P0 已落地 | P1 可继续补更严格的文档 lint / gate 自动检查 | 中书省 / 门下省 / 尚书省 |

P1 当前判断：**不是从零开始，而是进入收口阶段**。优先处理“状态表落后真实实现”和“dashboard/gate 可观测与回归测试不足”。

### P2：再做制度演化与高级能力

| 序号 | P2 项 | 当前证据 | 当前状态 | 真实缺口 | 建议归属 |
|---|---|---|---|---|---|
| 1 | `/autopsy`、`/replay`、`/debate` 等看板命令面板化 | `scripts/kanban_update.py` 已有 autopsy CLI 基础；dashboard 未见完整命令面板入口 | 未完整落地 | 需要把 CLI 能力面板化，并保证触发、审计、权限边界清晰 | 礼部 / 刑部 |
| 2 | 多制度模板与配置热切换 | 当前未见稳定 `configs/` 制度模板目录 | 未落地 | 需先定义模板结构、迁移策略、回滚方式 | 中书省 / 工部 |
| 3 | 自动复盘建议，门下审核后准奏 | 已有 autopsy 报告与 memory 数据目录基础 | 未形成固定机制 | 需建立 Done/Blocked 后的经验提取、建议生成、门下审核、准奏入库流程 | 吏部 / 门下省 |
| 4 | 对外扩展（PWA / Notion / Linear / 移动端） | 未见当前任务内落地证据 | 未落地 | 明显后置；等 P1 可运行机制稳定后再评估 | 礼部 / 工部 |

P2 当前判断：**全部后置**。P2 依赖 P1 的 stalled/autopsy 可观测、gate 测试和运行态闭环稳定后再做，否则会把尚未闭合的治理链扩散到更多入口。

---

## 5. 验收标准

### 5.1 制度侧
- 任意任务都能回答：**谁负责、卡在哪、下一步是什么、超时后谁督办**。
- 中书 / 门下 / 尚书三道 gate 的输出具备统一结构。
- 无“直接绕过台账私聊执行”的隐性链路。

### 5.2 代码侧
- stalled 任务具备分类，不再只是红灯。
- 超时任务有固定恢复链：`retry -> escalate -> blocked -> autopsy`。
- doctor / backup / safe update 三类脚本可执行、可复核。

### 5.3 运维侧
- 可通过单条命令巡检：配置、服务、日志、端口、看板健康、OpenClaw 可用性。
- 关键 memory/task 数据具备备份产物与恢复提示。

---

## 6. 当前落地状态（截至本次推进）

### 6.0 汇报与落盘约定

- 面向用户的默认汇报只输出**结果、结论、产物路径、是否完成**，不展示详细思考过程。
- 当用户明确要求“把规则写入文件”时，除当次结果文件外，还应同步写入项目内可持续遵循的规则文档，避免后续再次违背。
- 本约定适用于三省六部/edict 主线排查、修复、验证、收口场景。

| 项目 | 状态 | 说明 |
|---|---|---|
| 正式审稿稿 | 已完成并重建 | 现已补落盘到 `docs/JJC-20260416-001-sansheng-governance-executable-review.md`；原先 `deliverables/...` 路径不存在，已回正为当前真实路径 |
| 分工推进稿 | 已完成并重建 | 现已补落盘到 `docs/JJC-20260416-001-task-division-plan.txt`；原先 `deliverables/...` 路径不存在，已回正为当前真实路径 |
| 治理升级映射总表 | 已完成 | 本文件 `docs/governance-upgrade-map.md` |
| doctor 脚本 | 本轮补齐 | `scripts/doctor_edict.sh` |
| memory backup 脚本 | 本轮补齐 | `scripts/memory_backup.sh` |
| safe update 脚本 | P1 增强版已落地 | `scripts/safe_update.sh` 已支持 plan/prepare/test/apply/restart/rollback；restart/rollback 需要显式确认令牌，默认不重启 |
| worker 完整闭环（分类+autopsy） | P0 已落地，后续持续运行态观察 | `orchestrator_worker.py`、相关测试与真实任务 autopsy 字段已具备；文档口径已同步 |
| dashboard autopsy 面板 | P0 已落地 | `dashboard/server.py` 与 `dashboard/dashboard.html` 已补 autopsy 读取/生成入口，后续 P1 增强摘要 |
| gate 结构化执行 | P0 已落地并补可逆 probe 证据 | 已实测 `PendingConfirm -> approve -> Done`、`PendingConfirm -> reject -> Zhongshu(review_round=1)`；本轮又补修治理样本聚合的 stale 字段残留问题，并清除现场遗留临时 probe 样本 `PROBE-GOV-20260426`，当前 `tasks_source.json` / `live_status.json` 均已不再残留该探针数据 |
| 自然治理样本厚度 | P1 Phase 1 已起步，继续观察 | 旧问题已确认：截至 2026-04-26 05:04（北京时间）`tasks_source.json` 现场实测仍为 `JJC=32 / OTHER=0 / Done=32`，自然样本为 0；本轮已按专项方案落地第一阶段“三层分离”——`sync_from_openclaw_runtime.py` 改为写 `tasks_runtime_view.json`，新增 `scripts/sync_governance_samples.py` 维护 `tasks_governance_samples.json`，新增 `scripts/rebuild_task_views.py` 聚合 `tasks_source.json`，`refresh_live_data.py` 追加 `taskLayers` 统计，`run_loop.sh/install.sh` 已接入；随后又修复 `sync_governance_samples.py` 在任务已脱离 PendingConfirm 后仍残留旧 `pending_confirm` 的聚合问题，并清除现场遗留临时 probe 样本 `PROBE-GOV-20260426`；最新又补做了一次 scheduler 内部巡检实测：北京时间 2026-04-26 14:44 左右，从上游 `tasks_governance_samples.json` 注入可逆 probe，经 `scripts/rebuild_task_views.py` 聚合后，`edict-dashboard.service` 日志同秒出现 `PROBE-GOV-SCHED-HERMES-20260426T064303Z 新状态 ProbeState 无对应 Agent，跳过自动派发` 与 `🔍 定时巡检：1 个动作`，且样本 `_scheduler.retryCount` 从 `0 -> 1`、`lastDispatchTrigger=taizi-scan-retry`、`flow_log` 追加 `停滞717秒，触发自动重试第1次`；样本随后已清理，无现场残留。另一个关键坑也已坐实：直接往 `tasks_source.json` 注入 probe 会先被 `edict-loop.service` 的 15 秒刷新链覆盖，不能再把这种失败误判为 scheduler 线程失效。最新又修复 runtime 过滤误伤：`should_keep_runtime_task()` 过去会把超过 60 分钟进入 `Next` 的真实 `agent:*:main` 会话直接筛掉，导致连唯一活跃 main session 也可能被误判为“runtime=0”。现已改为保留 24h 窗口内的真实 main session，同时保留 heartbeat 丢弃与飞书噪音过滤规则。现场现状已进一步更新：北京时间 2026-04-26 18:46 左右再次执行 `python3 scripts/guard_openclaw_sessions.py --apply` 后，最新 dry-run 已为 `totalIssues=0`；随后重刷 `sync_officials_stats.py -> sync_from_openclaw_runtime.py -> rebuild_task_views.py -> refresh_live_data.py`，现场三层统计已收口为 `live_status.taskLayers = {runtimeCount: 0, governanceSampleCount: 1, jjcArchiveCount: 32}`，其中 `tasks_runtime_view.json=0`、`tasks_source.json` 也已无 `OC-*` 残留。说明当前 runtime 面已被清干净，后续若要继续做大治理样本，应回到上游自然任务生成与沉淀链路，而不是再纠缠前台 runtime 噪音。 |
| OpenClaw main session 防爆/自愈 | 本轮补齐 | 已按官方文档把 `/root/.openclaw/openclaw.json` 调整为 `agents.defaults.contextTokens=131072`、更积极的 `compaction/contextPruning/session.reset`；新增 `scripts/guard_openclaw_sessions.py` + `tests/test_guard_openclaw_sessions.py`（`3 passed`），并补上 `missing_transcript_file` 检测与轮转后自动创建空 transcript 占位；历史坏会话 `menxia/shangshu/zhongshu` 已做可逆轮转，最新 `python3 scripts/guard_openclaw_sessions.py` dry-run 为 `totalIssues=0`；已创建 Hermes cron `217551f91436 / openclaw-session-guard` 每 30 分钟自动执行修复脚本。随后用户批准重启，已于北京时间 2026-04-26 16:47 执行 `systemctl --user restart openclaw-gateway`，`openclaw gateway status` 返回 `RPC probe: ok`；重启后对 `agent:zhongshu:main` 做最小实测，真实写回 `contextTokens=131072`、`modelProvider=faker`、`model=gpt-5.4`、`status=done`，证明新参数已在真实 main session 生效。 |
| template 字段透传样本 | 已补可逆 probe 证据 | 已用临时样本验证 `templateId/templateParams/targetDept` 可在任务数据中保留，probe 后已恢复原始数据 |
| 尚书显式派部链路 | 本轮补齐产品闭环 | `dashboard/server.py` 新增 `/api/dispatch-task`，`TaskModal` 新增“🎯 显式派给六部”；已实测 build 产物与运行中 bundle 均包含该入口，`Assigned/Next/Doing` 现在可直接落成真实六部执行，不再只靠“推进到下一步”+ `targetDept` 隐式猜路由 |
| backend host-native 常驻 | **已进入生产 dual/export 过渡态，待最终验收** | 现场新复核显示：`127.0.0.1:18000/health -> {"status":"ok","version":"2.0.0","engine":"edict"}`、`/api/admin/health/deep -> {"status":"ok","checks":{"postgres":true,"redis":true}}` 仍健康；`GET /api/tasks` 现已返回 `count=1`，内容为 backend probe 样本；`data/tasks_backend_export_meta.json` 已存在；`live_status.json.taskSource` 已切到 `backend_api_export`；`edict-dashboard.service` 已注入 `EDICT_TASK_WRITE_MODE=dual`，`edict-loop.service` 已注入 `EDICT_ENABLE_BACKEND_EXPORT=true`。这说明现网已不再是“锁在 JSON 主路”的旧状态，而是 backend 主写/兼容导出并存的过渡态。前台关键写链 smoke 与 systemd 最小回滚演练已在 2026-04-30 现场补齐实操证据，当前剩余尾项主要是继续观察 dual/export 稳定性、自然样本厚度，并完成最终验收判断。 |
