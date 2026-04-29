# current progress board

更新时间：2026-04-29 10:56（北京时间） / system `date`：2026-04-29 10:56:29 CST (+0800)

> 本文件用于把 `docs/closeout.md` 与 `docs/governance-upgrade-map.md` 的主线结论压成一份持续跟进板。
> 目标不是重复全部长文，而是给阿爪/值守链一个**当前到哪了、卡在哪、下一步干什么**的统一入口。
> 另外自 2026-04-28 起，**所有系统改动（配置、服务、热修、回滚、守护脚本、运行态止血）默认都要同步汇总到 `docs/current-progress-board.md`**，避免后续出问题时现场分散、回溯找不到。

---

## 1. 一句话总览

**edict / 三省六部治理升级主线目前处于：工程收口基本完成，backend host-native 已进入生产 dual/export 过渡态并出现真实导出证据；但前台写链 smoke、自然治理样本厚度与回滚验收仍未收口。OpenClaw / taizi 本轮已完成直连 DM 结构性修复与 provider/session 去钉死清理，且在晚间重启窗口后已再次拿到多轮 `received message -> dispatching to agent -> dispatch complete` 真实样本；当前不再是“DM 完全断链”，而是收敛为 **taizi 直聊 session 长跑 + 偶发消息整理脏状态** 的不稳定态；`menxia:main` 为历史噪声项，而 `shangshu:main` 本轮已完成 dashboard 重入止血与定点 session recovery。**

---

## 1.5 待审方案：三框架接入取舍与实施顺序（待玄成把关，确认后再执行）

### 目标
本轮不是把 `Superpowers / GenericAgent / Evolver` 全部堆进生产，而是围绕 **edict 现有三省六部主链** 做一轮可控升级：
- 保持 `edict` 继续作为任务治理与状态流转中枢
- 吸收 `tiangong / danghuangshang` 的治理硬度
- 优先补齐演化修复能力，而不是继续把架构做胖

### 结论
**不建议三个框架全部直接安装进 edict 生产主链。**

建议路线：
- **优先接入：Evolver**
- **重点吸收：Superpowers 的流程方法论**
- **暂缓主链接入：GenericAgent，仅保留隔离实验位**

核心原因：三者都碰 `skill / memory / agent loop / evolution / execution`，若同时深接，极易出现：
- 技能体系重复
- 记忆层冲突
- 调度权不清
- 日志归因困难
- 故障面扩大

### 三者定位
#### 1) Evolver
定位：**edict 的外置演化/修复增强层**

适合承担：
- 失败日志扫描
- 状态卡滞模式识别
- 经验沉淀
- 修复/加固策略输出
- 演化事件留痕

本轮建议优先使用：
- `repair-only`
- `harden`

原则：**先稳态，再创新。**

#### 2) Superpowers
定位：**研发治理与交付 SOP 来源，不作为主运行时依赖**

建议吸收的能力：
- 先澄清目标，再开工
- 先设计，再写计划
- 小步拆解
- 先验证，再宣称完成
- review 前置
- 分支/阶段收口

建议映射关系：
- `中书`：目标澄清、任务拆解、方案成文
- `门下`：审核、纠偏、风险把关
- `六部`：执行、验证、交付回写

结论：**拿它的流程，不拿它当运行时底座。**

#### 3) GenericAgent
定位：**后续高执行实验框架，当前不进生产主链**

可预留的适用场景：
- 本地 GUI 自动化
- 浏览器登录态长链操作
- ADB / 手机侧流程执行
- 个性化 skill 自生长执行体

限制原则：
- 单独目录
- 单独记忆
- 单独日志
- 单独调度边界
- 不直接接管三省六部主链

结论：**适合做实验舱，不适合现在直接入朝堂中枢。**

### 推荐架构
建议形成以下分层：
- `edict`：任务治理中枢，负责三省六部编排、状态流转、交付留痕
- `tiangong / danghuangshang 思想层`：治理纪律、角色边界、审批约束
- `Evolver`：memory / logs / signals 驱动的演化、修复、加固
- `Superpowers 方法论层`：研发与执行 SOP
- `GenericAgent（后续可选）`：外勤型高执行代理实验位

### 实施顺序
#### Phase 1：先接 Evolver
从以下输入源开始：
- 任务失败日志
- 状态卡滞记录
- 审核驳回原因
- 角色交接异常
- memory 中沉淀的长期问题模式

接入要求：
- 输出可审计
- 先以“提示/建议/修复策略”形式接入
- 不越权直接改主链

#### Phase 2：把 Superpowers 流程映射进 edict
建议落地为：
- 任务前澄清模板
- 方案审批模板
- 执行拆解模板
- 验证与验收清单
- 交付前 review 节点

重点不是装插件，而是把它转成 edict 内部规则。

#### Phase 3：预留 GenericAgent 实验舱
适用场景：
- 本地 GUI 自动化
- 浏览器登录态长链操作
- ADB / 手机侧流程执行
- 高度个性化、自生长 skill 的专用执行体

但必须：
- 隔离部署
- 单独日志
- 单独记忆
- 明确任务边界
- 不直接接管三省六部主链

### 风险提示
1. **不要三者同时深接入主链**，否则会快速导致架构发胖、治理边界失真。
2. **Evolver 先做 repair / harden，不急着做全自动 innovate**。
3. **GenericAgent 必须隔离**，它适合高执行特种队，不适合直接入当前中枢。
4. **Superpowers 要抽象成制度，不要照搬成新的运行时负担。**

### 当前建议口径
> 以 Evolver 作为 edict 的首个外置增强层，优先补齐演化修复与稳定性治理；以 Superpowers 作为研发治理与交付 SOP 的来源，内化为三省六部规则；将 GenericAgent 保留为后续隔离实验框架，不进入当前生产主链。

### 当前状态
- **该方案仅为待审稿**
- **等待玄成把关**
- **确认后再进入执行拆解**

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
- 前台 dashboard 写入口已补到登录态真实 smoke：匿名直打 `POST /api/create-task` 仍会返回 **401 未登录或会话已过期**，但带有效 `edict_token` 后，`POST /api/auth/login`、`POST /api/create-task`、`POST /api/task-todos`、`POST /api/advance-state`、`POST /api/review-action`、`POST /api/dispatch-task` 已拿到真实现网证据；其中新建任务 `JJC-20260428-001` 已成功创建，随后通过真实 UUID `a38d3eab-415d-4e08-8109-e8f84ca7fce6` 完成 `Taizi -> Zhongshu -> Menxia -> Assigned -> Doing(工部)` 整段推进
- legacy `review-action`：**已在重启 backend API 后恢复路由并完成真实 smoke**；对 `PROBE-BE-20260428-151828` 现场 `POST /api/tasks/by-legacy/{legacy_id}/review-action` 返回 **200 OK**，任务状态从 `Menxia` 准奏推进到 `Assigned`
- legacy `dispatch-target`：**已在重启 backend API 后恢复路由并完成真实 smoke**；对 `PROBE-BACKEND-DIRECT-001` 现场 `POST /api/tasks/by-legacy/{legacy_id}/dispatch-target` 返回 **200 OK**，`assignee_org` 已真实改写为 `工部`
- 三面一致性本轮已补齐：`/api/tasks`、`data/tasks_source.json`、`live_status.json.taskSourceMeta` 当前都已追平到 `count=2`，且 `PROBE-BE-20260428-151828` / `PROBE-BACKEND-DIRECT-001` 的 `state`、`assignee_org`、`updatedAt` 已能跨三面对应；因此“导出未追平”不再是当前阻塞

结论：
- **backend 主写 / 兼容导出过渡态已经进入生产默认值**
- **现网已不再是“锁在 JSON 主路”的旧状态**
- **backend 原生 create / legacy get/todos/progress/部分 transition / backend dispatch 已拿到真实现网证据**
- **legacy review-action / dispatch-target 已在 backend 重启后恢复并拿到真实现网证据，三面一致性与 export 刷新也已追平，前台登录态写链也已补到完整关键闭环；但仍缺前台 progress 入口口径澄清与更多自然业务样本，当前阶段仍然只能叫“过渡态验收中”，不能叫“纯 backend 主链切换完成”**
- **当前看到的 backend 样本仍薄，而且主要还是 probe 证据；自然样本厚度仍需继续补**

关键坑点：
- 不能再按 `Pending -> Taizi` 的老预期写 smoke，现网 backend create 后初始态已直接是 `Taizi`
- 不能把匿名 dashboard POST 当成前台写链通过证据；这条链路有认证门槛，必须先登录拿 `edict_token`
- 不能再把 `/api/task-progress` 当成前台写入口验收项；当前 dashboard 服务端并不存在这条接口，真实可写入口至少已确认 `create-task`、`task-todos`、`advance-state`，且其中后两类状态推进接口吃的是**真实 UUID**，不是 legacy id
- 本轮已确认 `review-action` / `dispatch-target` 的前序 404 根因是 backend API 长时间未重启，未吃到 2026-04-27 的 legacy 路由改动；重启后 openapi 与真实 smoke 已恢复

### 3.2 自然治理样本仍偏薄
- 能力已通过可逆 probe 与测试验证
- 但自然运行样本仍不厚，不能把“能力存在”硬说成“线上已充分自然验证”

### 3.3 2026-04-29 08:36（北京时间）上游 edict 更新同步结果
#### 已完成的同步前置核对
- 已对本机仓库执行 `git fetch --all --prune`。
- 当前工作分支：`feat/governance-upgrade-mainline`。
- 当前远端：
  - `origin = https://github.com/joviji1/edict.git`
  - `upstream = https://github.com/cft0808/edict.git`
- 当前上游 `upstream/main` 已前进到：**`1ceee6b`**。
- 当前本地主线工作 HEAD 仍在：**`81f8739`**。
- 本地工作树存在大量未提交改动（dashboard / backend / scripts / docs / tests / dist 等均有变更），**当前不能直接无脑 merge upstream**。

#### 本机运行环境对照
- `edict-dashboard.service = active`
- `edict-loop.service = active`
- `edict-dashboard.service` 当前环境：`EDICT_TASK_WRITE_MODE=dual`
- `edict-loop.service` 当前环境：`EDICT_ENABLE_BACKEND_EXPORT=true`
- 这说明本机当前确实处于 **backend host-native + dual/export 过渡态**，不是 Docker 环境，也不是 README 里的纯演示态。

#### 本次上游更新里与本机最相关的内容
1. **安装/启动脚本开始正式兼容自定义 OpenClaw Home 与 Python 3.10+**
   - `install.sh`、`scripts/apply_model_changes.py`、`scripts/sync_agent_config.py`、`scripts/sync_from_openclaw_runtime.py` 等，开始统一走 `OPENCLAW_HOME` / `get_openclaw_home()`，不再把路径硬编码到 `~/.openclaw`。
   - `start.sh`、`scripts/run_loop.sh` 开始优先解析 `EDICT_PYTHON`，并把 Python 要求明确提升到 **3.10+**。
   - 这对本机是**有价值但不是立刻阻塞**的同步项：本机当前运行正常，但后续若继续维护 host-native 安装，建议把这些路径/解释器兼容更新吸收进来，减少未来环境漂移。

2. **dashboard/server.py 上游新增了几类关键修复**
   - 用 `python_bin()` 统一子进程调用，减少解释器错位。
   - `file://` 远程 skill 加了路径范围校验，补了 **CWE-22 / 路径遍历防护**。
   - 引入 `modify_tasks()` / `modify_task()` 一类原子读改写封装，目的是修掉任务并发更新的 TOCTOU race。

#### 2026-04-29 08:55（北京时间）定向同步实做结果
- 已先备份本机关键文件到：`/root/.hermes/backups/edict-upstream-sync-20260429-083826/`
- 本轮**已实际吸收**的高优先级兼容更新：
  - `scripts/utils.py` 新增 `get_openclaw_home()`，统一支持 `OPENCLAW_HOME`
  - `scripts/sync_agent_config.py` 改为走 `OPENCLAW_HOME` 推导 `openclaw.json` 与默认 workspace 路径
  - `scripts/sync_from_openclaw_runtime.py` 改为走 `OPENCLAW_HOME/agents`
  - `scripts/sync_officials_stats.py` 改为走 `OPENCLAW_HOME`
  - `scripts/apply_model_changes.py` 改为走 `OPENCLAW_HOME/openclaw.json`
  - `install.sh`、`start.sh`、`scripts/run_loop.sh`、`edict.sh` 已支持 `EDICT_PYTHON`，不再把解释器硬绑死在 `python3`
  - `install.sh` 内嵌 Python 段与首次同步链路已同步改成 `OPENCLAW_HOME` / `EDICT_PYTHON` 口径
- 本轮**未直接整块照搬**上游 `dashboard/server.py`：原因是本机当前 `server.py` 已有 backend dual/api 写链、governance sample 同步、export 过渡态等本地增强；若整文件覆盖会把本机生产逻辑打回去。
- 本轮复核确认：`file://` 本地/远程 skill 路径范围校验在本机 `dashboard/server.py` 里**原本就已存在**，这块无需重复同步。

#### 2026-04-29 08:55（北京时间）验证与顺手修复
- 语法验证已过：
  - `python3 -m py_compile dashboard/server.py scripts/utils.py scripts/sync_agent_config.py scripts/sync_from_openclaw_runtime.py scripts/sync_officials_stats.py scripts/apply_model_changes.py`
  - `bash -n install.sh start.sh scripts/run_loop.sh edict.sh`
- 运行验证已过：
  - `python3 scripts/sync_agent_config.py` → `12 agents synced`
  - `python3 scripts/sync_officials_stats.py` → `11 officials | cost=¥12.06 | top=太子`
  - `python3 scripts/sync_from_openclaw_runtime.py` → `synced 4 tasks from openclaw runtime in 147ms`
- 验证过程中额外暴露出一个**本机旧坑**，已当场修掉：
  - `scripts/sync_from_openclaw_runtime.py` 原先默认把 session `updatedAt` 当整数毫秒；但现网 `sessions.json` 已出现 ISO 时间串（样本：`2026-04-28T12:46:33.134886Z`），导致脚本在 `now_ms - updated_at` 处抛 `TypeError`
  - 现已新增 `_to_timestamp_ms()` 统一兼容 `int/float/ISO string`，并已覆盖到 `build_task()`、`should_keep_runtime_task()`、`tasks.sort(...)` 三处
  - 这不是本轮同步新引入的问题，而是旧脚本的类型假设被验证步骤撞出来；现已随本轮一起收口

#### 仍待后续评估的上游项
- `dashboard/server.py` 的 `python_bin()` 子进程统一口径：对本机有价值，但需要与现有 backend dual/api 写链、JWT、治理样本同步逻辑一起整合，不能直接贴
- `modify_tasks()` / `modify_task()` 原子读改写框架：方向是对的，但本机当前 `server.py` 已接入 backend dual/api 与异步刷新链，后续若要吸收，必须先做局部映射，不能生抄
- 结论：本轮“定向同步”已经把**最值得先吸且低风险**的环境兼容层落完；剩余 server 原子更新框架属于下一层工作，不适合在当前生产魔改基线上无验证硬并
   - `handle_review_action()` 增加“todos 未完成不能直接准奏完结”的校验。
   - 这批改动对本机**高度相关**：当前服务器就是 host-native dashboard 常驻运行，这些修复会直接影响看板写链稳定性与并发安全。

3. **前端 / dashboard 时间展示与交互层继续修正**
   - 上游补了本地时区展示、TaskModal / SessionsPanel 时间归一、看板动画与前端时间工具封装。
   - 这对本机 running dashboard 有实际影响，但优先级低于上面的后端/脚本安全与并发修复。

4. **agents / docs / 远程 skills 生态继续前推**
   - 上游新增 `qintianjian` agent。
   - README 与 remote skills 文档改成以 `mmx_cli` / MiniMax skill 源为默认示例，并移除了旧的 broken default skills hub 口径。
   - 这类更新对本机不是第一优先级阻塞，但如果后续要跟 upstream 文档口径对齐，不能继续沿用旧的官方 skills hub 说法。

5. **backend 与测试层继续补强**
   - 上游新增 QQ 渠道、任务并发 race 测试、dashboard review/dispatch 测试、task mutation race 修复等。
   - 其中“任务并发写入竞争修复”与本机当前三省六部写链/调度链关系很近，值得优先审进去。

#### 当前同步判断
- **现在最该同步的不是整仓库生拉硬拽地 merge，而是优先吸收“路径/解释器兼容 + dashboard 并发安全 + file:// 技能路径防护”这三类改动。**
- 原因很直接：
  1. 它们和本机 host-native 安装环境强相关；
  2. 对当前正在跑的 `edict-dashboard.service` / `edict-loop.service` 有直接收益；
  3. 风险边界相对清晰，适合在本地大量未提交改动的情况下做定向吸收，而不是整仓一锅端。

#### 下一步同步动作
- 先继续细读并拆解上游更新文件，按三类处理：
  1. **必须尽快同步到本机运行面的**：脚本路径兼容、Python 3.10+ 入口、dashboard 原子写任务、file:// 路径防护；
  2. **需要结合本机现有魔改再判断的**：dashboard/server.py 大块逻辑、前端 dist / src、agents SOUL；
  3. **暂先只记账不立刻落地的**：截图、设计文档、QQ 渠道、Windows PS 脚本、默认 skill 示例更新。
- 同步吸收前必须先做备份/分支保护，避免把本机现有主线热修与上游新改动揉成不可回滚的一团。

#### 受控对齐长期执行规则（新增）
- **以后 `origin/main` 再升级，默认也按本轮这套“受控对齐”规则执行本地升级，不做无脑 merge、不做整仓硬覆盖。**
- 默认执行顺序固定为：
  1. `git fetch --all --prune`，确认 `HEAD / origin/main / upstream/main` 的真实提交差异；
  2. 先看 `git diff --name-status origin/main...HEAD` 与当前 worktree / untracked 清单，确认本机生产魔改面；
  3. 按三类分流：**必须保留** / **可以回归** / **继续定向同步**；
  4. 先备份关键文件到 `/root/.hermes/backups/`，再做定向吸收；
  5. 优先吸收对本机 host-native 运行面直接有收益且风险边界清晰的改动（如路径兼容、解释器入口、并发安全、防护补丁、运行态止血脚本）；
  6. 对 `dashboard/server.py`、backend 写链、前端 bundle、systemd/deploy 相关大块改动，默认先做局部映射与验证，**禁止整文件覆盖式同步**；
  7. 每轮升级后必须补做语法检查、关键脚本实跑、必要时补可逆 probe，并把**原因 / 过程 / 结果 / 仍待同步项**回写本文件。
- 结论口径也固定：
  - 若只是吸收了高优先级兼容层，要写成“**已完成定向同步，不等于已与 `origin/main` 完全一致**”；
  - 若仍存在本机生产必需魔改或 worktree 未清，要明确写成“**分叉运行中，继续按受控对齐推进**”，不能误报“已同步完成”。

#### 2026-04-29 09:00（北京时间）本机魔改面解释与受控对齐分叉结论
##### A. 本机主要魔改面（是什么 / 为什么）
1. **backend host-native + dual/export 过渡态**
   - 现场 systemd 已是：`edict-dashboard.service -> EDICT_TASK_WRITE_MODE=dual`、`edict-loop.service -> EDICT_ENABLE_BACKEND_EXPORT=true`。
   - `dashboard/server.py`、backend `api/tasks.py` / `api/legacy.py` / `services/task_service.py`、`scripts/export_backend_tasks_to_legacy_json.py` 等，都围绕“backend 主写 + legacy JSON 兼容导出”做了本机化改造。
   - **为什么这样改：** 本机不是 README 里的演示态，而是 213.35.100.132 上的 host-native 生产过渡态；若只回到单 JSON 主路，前台、旧脚本与现网导出视图会直接断层。

2. **三省六部治理升级主线能力落地**
   - 已落地 `PendingConfirm / gate_checks / templateId / templateParams / targetDept / stalled / retry / escalate / blocked / autopsy`，并补了对应前后端与测试。
   - 已补齐尚书省显式派部、review-action、dispatch-target 等产品/路由闭环。
   - **为什么这样改：** 本机主线目标不是“保留开源默认形态”，而是把三省六部治理升级真正收口到可执行、可审议、可回溯的现网能力。

3. **任务数据三层分离**
   - 本机新增并使用：`tasks_runtime_view.json`、`tasks_governance_samples.json`、`tasks_source.json`。
   - 配套脚本包括：`scripts/sync_governance_samples.py`、`scripts/rebuild_task_views.py`、`scripts/refresh_live_data.py`、改造后的 `scripts/sync_from_openclaw_runtime.py`。
   - **为什么这样改：** 旧的单层 `tasks_source.json` 会把 runtime 噪音、治理样本、JJC 主任务混在一起，现场已经证明会污染前台并误伤调度判断；三层分离是本机稳定运行的必需改造。

4. **OpenClaw / Feishu P2P / session 自愈与守护**
   - 本机新增 `scripts/guard_openclaw_sessions.py`、P2P hotfix 文档与对应测试；并对 main/direct session 的坏指针、缺 transcript、长持锁、stale context window 做了防守逻辑。
   - **为什么这样改：** 这些不是抽象优化，而是本机真实事故驱动出来的止血层；不保留的话，taizi / menxia / shangshu / Feishu direct 链会反复掉回旧坑。

5. **运维脚本与主线文档体系**
   - 本机新增/强化：`scripts/doctor_edict.sh`、`scripts/safe_update.sh`、`scripts/memory_backup.sh`、backend runtime/migration/deploy/systemd 脚本，以及 `docs/closeout.md`、`docs/governance-upgrade-map.md`、`docs/current-progress-board.md` 等交付链。
   - **为什么这样改：** 本机已进入持续运维、回滚演练、事故回溯阶段，不能再只靠 README 或一次性调试命令维持。

##### B. 本机 vs `origin/main` 分叉清单（受控对齐口径）
###### B1. 必须保留
- `dashboard/server.py`
  - 原因：本机已接入 backend dual/api 写链、governance sample 同步、runtime guard、menxia/shangshu/taizi 现场止血逻辑；直接回归会把现网生产逻辑打回去。
- backend 任务链相关：
  - `edict/backend/app/api/legacy.py`
  - `edict/backend/app/api/tasks.py`
  - `edict/backend/app/models/task.py`
  - `edict/backend/app/services/task_service.py`
  - `edict/backend/app/workers/__init__.py`
  - 未跟踪的 `edict/backend/app/services/notification_service.py`
  - 未跟踪的 `edict/migration/versions/002_add_outbox_events.py`
  - 原因：承载 backend host-native / dual-export 过渡态、legacy route 补路由、通知/outbox 等本机生产主链。
- 三层数据与运行态治理脚本：
  - `scripts/sync_from_openclaw_runtime.py`
  - `scripts/refresh_live_data.py`
  - 未跟踪的 `scripts/sync_governance_samples.py`
  - 未跟踪的 `scripts/rebuild_task_views.py`
  - 未跟踪的 `scripts/export_backend_tasks_to_legacy_json.py`
  - 未跟踪的 `scripts/guard_openclaw_sessions.py`
  - 原因：这是本机解决 runtime 噪音、治理样本沉淀、legacy 兼容出口、自愈守护的核心层。
- 本机运维与发布链：
  - `scripts/doctor_edict.sh`
  - `scripts/safe_update.sh`（未跟踪）
  - `scripts/memory_backup.sh`（HEAD 分叉）
  - `scripts/check_backend_prereqs.sh` / `scripts/manage_backend_infra.sh` / `scripts/run_backend_component.sh` / `scripts/run_backend_migrations.sh` / `scripts/setup_backend_runtime.sh`（未跟踪）
  - `deploy/systemd/*`、`deploy/backend/*`（未跟踪）
  - 原因：这些是本机 host-native backend 常驻与可回滚运维链，不属于可随手删掉的实验物。
- 主线收口文档与交付稿：
  - `docs/closeout.md`
  - `docs/current-progress-board.md`
  - `docs/governance-upgrade-map.md`
  - `docs/review-correction-notes.md`
  - `docs/JJC-20260416-001-sansheng-governance-executable-review.md`（未跟踪）
  - `docs/JJC-20260416-001-task-division-plan.txt`（未跟踪）
  - `docs/backend-host-native-productionization.md`（未跟踪）
  - `docs/openclaw-feishu-p2p-hotfix.md`（未跟踪）
  - 原因：这些已经承载本机真实原因/过程/结果与交付物，不是可无损回归的普通文档偏差。

###### B1-Priority. “必须保留”进一步拆分为 P0 / P1 / P2（本地升级优先级）

**P0：升级时必须优先保护，误回归会直接打断现网主链**
- `dashboard/server.py`
  - 原因：当前 dashboard 既承担前台入口，又承担 backend dual/api 写链、legacy 兼容、runtime guard、menxia/shangshu/taizi 现场止血逻辑；误用上游整文件覆盖，最容易把现网写链和调度链直接打断。
- backend 主写 / 兼容路由核心：
  - `edict/backend/app/api/legacy.py`
  - `edict/backend/app/api/tasks.py`
  - `edict/backend/app/models/task.py`
  - `edict/backend/app/services/task_service.py`
  - `edict/backend/app/workers/__init__.py`
  - `edict/backend/app/services/notification_service.py`
  - `edict/migration/versions/002_add_outbox_events.py`
  - 原因：这些文件直接决定 backend host-native、legacy review-action / dispatch-target、通知/outbox 是否还能工作；现场当前 `taskSource=backend_api_export`，已经不是可随手回退的演示态。
- 三层数据与导出守护核心：
  - `scripts/sync_from_openclaw_runtime.py`
  - `scripts/refresh_live_data.py`
  - `scripts/sync_governance_samples.py`
  - `scripts/rebuild_task_views.py`
  - `scripts/export_backend_tasks_to_legacy_json.py`
  - 原因：当前 `live_status.taskLayers={'runtimeCount': 4, 'governanceSampleCount': 4, 'jjcArchiveCount': 34}`，说明前台现实就是靠三层数据在跑；误回归会把 runtime / governance sample / export 兼容视图重新搅成一锅。
- OpenClaw / session 自愈守护：
  - `scripts/guard_openclaw_sessions.py`
  - 原因：这层直接对应 taizi / menxia / shangshu / Feishu direct 的真实历史事故；去掉后很容易重新掉回坏指针、缺 transcript、长持锁、stale context window 的旧坑。
- 本轮已吸收且必须继续保的 host-native 兼容入口：
  - `install.sh`
  - `start.sh`
  - `scripts/run_loop.sh`
  - `scripts/apply_model_changes.py`
  - `scripts/sync_agent_config.py`
  - `scripts/sync_officials_stats.py`
  - `scripts/utils.py`
  - 原因：这些已经承接 `OPENCLAW_HOME` / `EDICT_PYTHON` / model apply / runtime sync 的本机真实运行入口，属于升级时优先保命层。

**P1：升级时应尽量保住，不一定立刻炸，但会显著影响运维、回滚与持续收口效率**
- 运维/回滚/基础设施脚本：
  - `scripts/doctor_edict.sh`
  - `scripts/check_backend_prereqs.sh`
  - `scripts/manage_backend_infra.sh`
  - `scripts/run_backend_component.sh`
  - `scripts/run_backend_migrations.sh`
  - `scripts/setup_backend_runtime.sh`
  - `deploy/systemd/*`
  - `deploy/backend/*`
  - 原因：它们决定 backend host-native 能不能稳定部署、排障、回滚；即使暂时不影响当前进程继续跑，升级时丢掉会让后续运维重新回到裸手状态。
- 关键主线文档：
  - `docs/closeout.md`
  - `docs/current-progress-board.md`
  - `docs/governance-upgrade-map.md`
  - `docs/review-correction-notes.md`
  - 原因：这些文档已经承载“原因 / 过程 / 结果 / 当前阻塞 / 正确口径”；升级时若把它们冲掉，后面排障和交接会重新失忆。

**P2：属于交付沉淀与专项证据，优先级低于 P0/P1，但仍应保留**
- 正式交付稿与专项专题文档：
  - `docs/JJC-20260416-001-sansheng-governance-executable-review.md`
  - `docs/JJC-20260416-001-task-division-plan.txt`
  - `docs/backend-host-native-productionization.md`
  - `docs/openclaw-feishu-p2p-hotfix.md`
  - 原因：它们不直接控制当前服务是否继续跑，但对主线收口、复盘和后续对外/对内说明很重要；升级时不该丢，但保护优先级低于 P0/P1 运行面。

**本地升级执行优先级结论**
1. **先护 P0**：任何 `origin/main` 同步都必须先确保 P0 文件不被整块覆盖；必要时宁可暂缓同步，也不能先动现网主链。
2. **再护 P1**：确认运维脚本、systemd/deploy、主线文档还在，再继续吸收上游功能修复。
3. **最后整理 P2**：交付稿和专项文档可在升级后统一回补，但不应成为阻塞 P0/P1 的理由。
4. 真正的本地升级顺序应该是：**P0 保命 → P1 保运维与可回滚 → P2 保交付沉淀 → 再吸收 `origin/main` 新能力。**

###### B2. 可以回归 / 可择机清理
- `dashboard/dist/assets/*` 与 `dashboard/dist/index.html` 的旧 bundle 漂移
  - 原因：它们本质是构建产物，不应长期作为手工分叉面；确认新构建产物稳定后可统一回到标准构建输出。
- `.gitignore`、`README.md`、部分 docs 表述偏差
  - 原因：其中一部分只是为了本机现场临时补口径，不一定都要长期背离 `origin/main`；后续可择机收敛到更干净的说明层。
- 部分测试新增但仅覆盖本机临时收口口径的条目
  - 例如某些专项 smoke / 文档校正文案测试，后续若主链稳定、实现并入上游，可重整或合并，不一定永久保持现在的散装状态。

###### B3. 继续定向同步（不要硬并）
- `origin/main` 新增但本机还没完整吸收的高价值项：
  - `dashboard/server.py` 的 `python_bin()` 子进程统一（已落地）
  - `modify_tasks()` / `modify_task()` 原子读改写框架（待按本机 dual/api 写链做局部映射）
  - 时间展示本地化、TaskModal / SessionsPanel 时间归一（待前端源码与构建产物一起收口）
  - `fix(flow): prevent premature task completion before review`（已落地 fallback 校验）
  - `fix(dashboard): handle missing OpenClaw CLI during dispatch`（待按本机 dispatch 入口补兜底）
  - `support OPENCLAW_HOME env var`（本轮已吸收大半脚本层，但还未做到全仓统一）
  - `qintianjian` agent / 动画与 UI 体验项（已纳入下一批受控对齐清单，但优先级低于写链稳定性）
- **为什么不是直接 merge：** 这些改动方向大多是对的，但本机 `server.py` / backend / frontend 已经深度挂着生产魔改，必须按局部映射 + 实跑验证吸收，不能整块贴。
- **本轮执行顺序已固定：** 1）时间字段统一本地时区展示；2）dispatch 缺失 OpenClaw CLI 时的兜底；3）`modify_tasks()` / `modify_task()` 原子更新框架；4）`qintianjian` agent；5）动画 / UI 类改动。先收写链与时间口径，再碰生态和体验层。

##### C. 本轮受控对齐结论
- **本机不是“乱改了一堆”，而是已经把 `origin/main` 的通用仓库改造成 213.35.100.132 上的 edict/OpenClaw 生产过渡态。**
- **因此当前不能以“是否与 `origin/main` 完全一致”作为唯一目标，而要以“哪些本机生产魔改必须保留、哪些可回归、哪些继续定向同步”作为升级准绳。**
- 当前正确口径应保持为：**分叉运行中，继续按受控对齐推进。**
- 截至 2026-04-29 09:42（北京时间），本轮又已实际落地两项对本机高价值且低风险的对齐：
  1. `dashboard/server.py` 已补 `python_bin()`，并把本机仍残留的关键子进程调用从硬编码 `python3` 改为走 `EDICT_PYTHON / sys.executable` 统一入口；
  2. `dashboard/server.py::handle_review_action()` 在本机 fallback 路径中已补回 **Review 态 todos 未完成不能直接准奏完结** 校验，避免未完子任务被误提前收口。
- 本轮落地后已再次实跑通过：
  - `python3 -m py_compile dashboard/server.py scripts/utils.py scripts/sync_agent_config.py scripts/sync_from_openclaw_runtime.py scripts/sync_officials_stats.py scripts/apply_model_changes.py`
  - `python3 scripts/sync_agent_config.py` → `12 agents synced`
  - `python3 scripts/sync_from_openclaw_runtime.py` → `synced 4 tasks from openclaw runtime in 152ms`
  - `python3 scripts/sync_officials_stats.py` → `11 officials | cost=¥12.03 | top=太子`
- 因此当前受控对齐状态更新为：**P0 保护规则已落盘，且已继续吸收一批本机可安全落地的 `origin/main` 高价值改动；本机仍未与 `origin/main` 完全一致，但已按“P0 保命 → P1 保运维与可回滚 → P2 保交付沉淀 → 再吸收 `origin/main`”的顺序进入持续收口。**

---

## 4. 最新运行态专题：OpenClaw / taizi / windhub 阻塞

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

### 4.2.3 2026-04-28 晚间 live recovery 验证收口（DM / 前台登录态 / export 三层）
#### 现查结果
- **Feishu DM 闭环仍可实锤**：`/tmp/openclaw/openclaw-2026-04-28.log` 最新窗口仍能抓到 `dispatch complete (queuedFinal=true, replies=2)`（`13:00:57.038Z`）、随后 `received message`（`13:00:57.399Z`）与 `dispatching to agent`（`13:00:57.405Z`）。这说明当前不是 DM 死链，而是**链路可闭环但运行态不干净**。
- **前台登录态 smoke 不只是文档口径，当前 export 投影里仍留有真实产物**：`data/tasks_source.json` 当前仍存在两条 `meta.source=dashboard.create-task` 的前台样本，标题均为 `front-auth-smoke-20260428-2014`，并保留 `meta.legacy_id=JJC-20260428-001`：
  - `0d018beb-fd10-463b-882c-77779a25a486`
  - `a38d3eab-415d-4e08-8109-e8f84ca7fce6`
- **backend/export 三面对齐仍在**：`data/live_status.json.taskSource=backend_api_export`，`taskSourceMeta.count=4`；`data/tasks_backend_export_meta.json.count=4`；`data/tasks_source.json` 当前也确为 4 条任务。
- **此前 backend/legacy acceptance smoke 的任务本体仍在 export 面可读**：
  - `cea48d95-fe4d-4f84-a655-4387f0cffec4`（`PROBE-BE-20260428-151828`）当前仍为 `state=Assigned`、`assignee_org=工部`
  - `5a0e4b5e-4e5d-498d-8203-0d6e5875f221`（`PROBE-BACKEND-DIRECT-001`）当前仍保留 `legacy-route-real-smoke` 到 `工部` 的 flow

#### 验证口径
- **本轮已把“前台登录态 smoke / DM 闭环已恢复”补到 live log + export 数据面双重证据，不再只是文档转述。**
- **但这不等于彻底健康**：同一日晚间更早窗口仍持续出现 taizi 侧 `session file locked`、`Gateway agent failed; falling back to embedded`、`model_fallback_decision ... reason=timeout`。
- 因此当前最准确定性应为：**主链可闭环，运行态仍属不稳定恢复态；shangshu main 重入已止血，但 taizi 侧剩余自锁/长跑脏态仍需继续追。**

### 4.2.4 2026-04-28 晚间 taizi direct session 深挖结论（锁持有者 / transcript 尾部）
#### 现查结果
- 当前 taizi 剩余脏点已进一步收敛到 **Feishu direct session**：`agent:taizi:feishu:direct:ou_ed2187f2ad27e0b7876913371e72c06a`。
- `sessions.json` 现场：
  - `agent:taizi:main -> b1e4202b-da30-4b3b-a6aa-b465597a0dd0`，`status=running`，但**当前无 `.lock`**
  - `agent:taizi:feishu:direct:... -> 3afd9434-7539-462e-96c4-c41903c976d9`，`status=running`，`contextTokens=200000`，transcript 已长到 `1166411` 字节，且**当前唯一存在的 taizi 锁文件**就是 `3afd9434-7539-462e-96c4-c41903c976d9.jsonl.lock`
- 锁文件内容显示 `pid=1118485`、`createdAt=2026-04-28T13:16:01.305Z`；进一步按 `/proc/*/fd` 实查，**当前实际持有这把锁的活进程也正是 live `openclaw-gateway` PID `1118485`**。这说明它不是孤儿锁残渣，而是**live gateway 仍在占着当前用户直聊 session**。
- transcript 尾部补证：
  - `2026-04-28T13:00:55.412Z` 出现空 assistant 结束：`stopReason=error`、`errorMessage=524 status code (no body)`
  - 随后 `2026-04-28T13:16:01.370Z` 又收到用户新一轮 `继续`
  - `2026-04-28T13:26:15.088Z` 之后，这条 direct session 继续在同一 transcript 内跑前台登录态 smoke 的后续推进
- 旧脏态证据仍在同一 session 上留痕：此前已出现 `Removed orphaned user message to prevent consecutive user turns`，且 compaction 也出现过 `outcome=failed reason=timeout`。

#### 结论
- **taizi main 已不再是当前主要锁点；当前主脏点就是用户直聊 direct session `3afd9434-...` 本身。**
- **这不是死锁文件残留，而是 live `openclaw-gateway` 仍在真实占用/复用这条 direct session。**
- 因此当前最准确口径应更新为：**DM 主链能闭环，但当前用户直聊 session 仍处于 long-running + live 持锁 + 历史 524/消息整理脏态并存的未收口状态。**

### 4.2.5 2026-04-28 晚间 taizi direct session 定向旋转执行结果（已获确认后执行）
#### 过程
- 已按最小爆破面只旋转当前用户直聊 session：
  - session key：`agent:taizi:feishu:direct:ou_ed2187f2ad27e0b7876913371e72c06a`
  - 旧 session：`3afd9434-7539-462e-96c4-c41903c976d9`
  - 新 session：`57235628-f120-42e1-8382-8678ca9fa15b`
- 已先备份到：`/root/.openclaw/backups/direct-session-rotate-20260428-214339/`
- 本轮没有触碰 `agent:taizi:main`，也没有改 edict 任务数据。
- 随后已执行 `systemctl --user restart openclaw-gateway` 释放 live lock。

#### 结果
- **旧 direct lock 已释放**：`3afd9434-7539-462e-96c4-c41903c976d9.jsonl.lock` 已不存在。
- **gateway 已切到新进程**：当前 live `openclaw-gateway` PID 为 `1634650`。
- **新 direct session 映射已生效**：`sessions.json` 当前已指向 `57235628-f120-42e1-8382-8678ca9fa15b`。
- **新 session 文件已创建但尚未写入**：`57235628-f120-42e1-8382-8678ca9fa15b.jsonl` 当前为 `0` 字节，且此刻**无新 `.lock`**。

#### 当前口径
- 这次操作已经完成了**结构性止血**：旧的 live direct lock 被成功切走。
- 但截至本轮复核，还**没有拿到新 session 上的 post-restart DM 实时闭环样本**；因此当前状态应表述为：**旧脏 direct session 已成功切离，运行态正在等待新 DM 窗口的活样本验证**，不能提前写成“已彻底恢复”。

### 4.3 当前定性
- **消息入口与 completion 后续样本已重新出现，taizi direct DM 主链可继续闭环。**
- **当前可从 blocker 降级到“基本收口 / 转监控”，但还不能宣告完全结案。**
- **风险已从“DM 完全断链”收敛为：direct session 轮转后的长跑抖动、旧窗口残留歧义，以及 `lane wait exceeded` 等并发压力信号仍需继续盯。**

### 4.3.1 2026-04-29 凌晨 taizi direct DM 监控结论（北京时间对齐）
#### 最新结论
- **可往“基本收口 / 转监控”推进，但监控不能撤。**
- 这轮不再把前一日日志中的 UTC `19:xx` 直接当作“今天 06:xx 的新进展”混报；已按北京时间改为：**先看 `/tmp/openclaw/openclaw-2026-04-29.log`，若当日日志还没业务样本，再回看 `/tmp/openclaw/openclaw-2026-04-28.log` 做历史补证。**

#### 现场证据
- `sessions.json` 中 direct key `agent:taizi:feishu:direct:ou_ed2187f2ad27e0b7876913371e72c06a` 已从旧会话 `34ff0667-d955-4dc3-9fc3-ad29ffa3678a` 轮转到 **`bf9d14e8-a004-4fcd-8c55-5b622fdf5bec`**。
- 对历史主日志 `/tmp/openclaw/openclaw-2026-04-28.log` 的补证显示：在最初盯住的 `19:04:18Z / 19:04:35Z` 两个 ingress 之后，后续已重新出现多轮闭环：
  - `dispatch complete @ 2026-04-28T19:22:06.444Z`
  - `dispatch complete @ 2026-04-28T20:44:10.490Z`
  - `dispatch complete @ 2026-04-28T20:59:47.011Z`
  - `dispatch complete @ 2026-04-28T21:14:33.315Z`
- 同批后续窗口也已看到新的 `received message / dispatching to agent`，说明不是“只进不出”持续主导现场。
- 错误面在这轮监控里未继续恶化：
  - `surface_error = 60`，未新增
  - `embedded run timeout = 56`，未见更晚增长证据
  - `HTTP 524` 未见比已知窗口更晚的新增长证据
- 但并发压力信号仍在：`lane wait exceeded` 仍是需要继续盯的运行噪声/风险项。

#### 北京时间 06:00 之后的当前窗口判断
- 当前北京时间已到 **2026-04-29 06:05**。
- 当日日志 `/tmp/openclaw/openclaw-2026-04-29.log` 目前仅有少量非 taizi direct DM 业务行，**尚未出现新的 `p2p chat entered / received message / dispatching to agent / dispatch complete` 样本**。
- 因此此刻更准确的口径不是“06 点又有新闭环”或“06 点再次回退”，而是：**当前日日志仍是安静窗口；是否继续稳定闭环，需等 29 号日志出现新的 direct DM 业务样本后再判。**

#### 当前口径
- **taizi direct DM 主链已从 blocker 降到“基本收口 / 转监控”。**
- **今天 06 点前后还没有新业务样本进入 29 号日志，因此当前是安静窗口，不算新恶化。**
- **后续只要 29 号日志出现新 ingress 但没有 completion，就要立即把状态重新打回未收口 / blocker。**

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
