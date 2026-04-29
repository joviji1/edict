# current progress board

更新时间：2026-04-30 02:00（北京时间） / system `date`：2026-04-30 02:00:20 CST (+0800)

## 0. 本轮系统改动速记
- 2026-04-30 02:00（北京时间）：继续推进主板 checklist 去假待办；已把 A6-5 中与上文已拍板/已执行态重复、但仍挂 `[ ]` 的条目推进为 `[x]`，包括：阿爪默认先补澄清/计划、门下 review 与验收闸口、结果回写主板、`align-atomic-task-update` 作为真实 pilot、Evolver 第一批输入/输出/人工闸口、GenericAgent 只做外勤且结果先回流阿爪、以及三框架接入顺序固定且禁止并列接生产主链。仍缺实证的项（如 Evolver 质量验证、GenericAgent 隔离目录/日志/记忆落地）继续保留未完成。
- 2026-04-29 23:07（北京时间）：已继续推进 `docs/current-progress-board.md` 中原属“未完成”但其实已有板内证据支撑的事项：将 `align-atomic-task-update` 试跑与回写两项改为完成；将 Evolver 的只读定位、首批输入/输出、人工闸口改为已明确；将 GenericAgent 的实验舱范围、阿爪三框架接入顺序、禁止并列接生产主链等改为已拍板，避免主板长期挂着过时的 `[ ]` 假待办。
- 2026-04-29 22:16（北京时间）：已对 taizi 飞书直聊 `agent:taizi:feishu:direct:ou_ed2187f2ad27e0b7876913371e72c06a` 执行**内置 `sessions.reset` 清污**；变更前先按约定备份原 transcript 到 `/root/.hermes/backups/taizi-feishu-direct-89f35078-bb0d-49c2-96bf-e250b69af111.before-session-reset-20260429-220356.jsonl`。reset 返回 `ok=true`，新 `sessionId` 切为 `c4d78b68-5c2b-4bf8-a813-c54a20b460b6`。
- 2026-04-29 22:16（北京时间）：本次 `sessions.reset` 的落盘形态不是删除旧 transcript 文件，而是**原路径重建为新 session header**；`/root/.openclaw/agents/taizi/sessions/89f35078-bb0d-49c2-96bf-e250b69af111.jsonl` 已缩成 1 行、128 bytes，仅剩 `{"type":"session","version":3,"id":"c4d78b68-5c2b-4bf8-a813-c54a20b460b6",...}` 头记录，说明旧脏消息体已被清空。
- 2026-04-29 22:17（北京时间）：reset 后补查 `openclaw-gateway` 自 22:15:30 以来日志，尚未出现新的 `p2p chat entered` / `received message` / `dispatch complete` / `524 status code` / `auth_unavailable` 样本；当前只能确认**脏 session 已清掉**，还**未拿到 reset 后新一轮直聊入站与最终回复的正向证据**。
- 2026-04-29 21:08（北京时间）：继续为“补投递入口”收口，已确认 OpenClaw 当前**存在内部 Gateway `agent` RPC 入口**，可直接接受 `message + idempotencyKey + agentId`，并在传入 `sessionId` 时进入对应会话链；但当前公开 CLI 外壳 `openclaw agent` / `openclaw message send` 的 help 仍未把 `feishu` 暴露为可选 channel，`message send --help` 仅展示 telegram/whatsapp/discord/irc/googlechat/slack/signal/imessage/line。
- 2026-04-29 21:08（北京时间）：实测 `openclaw gateway call agent` 的最小可用参数集为 `message` 与 `idempotencyKey`；带 `agentId=taizi` 可被网关接受，返回 `{"status":"accepted"}`；带 `sessionId=89f35078-bb0d-49c2-96bf-e250b69af111` 时在 3s probe 窗口内未立即回错，而是进入运行并超时，说明该入口大概率已能命中既有 taizi 会话链。另一方面，`deliveryContext` 不是当前 `agent` RPC 允许字段，直接传会报 `invalid agent params: unexpected property 'deliveryContext'`。
- 2026-04-29 21:42（北京时间）：已把旁路脚本 `/root/.openclaw/workspace/edict/scripts/openclaw_feishu_relay.py` 从“`sessionId` 优先”改成“**`sessionKey` 优先绑定**”，默认直指 `agent:taizi:feishu:direct:ou_ed2187f2ad27e0b7876913371e72c06a`；`sessionId=89f35078-bb0d-49c2-96bf-e250b69af111` 仅保留作留痕/辅助，不再作为主绑定依据。脚本现支持 `probe/send/compensate` 三种模式，并在日志中同步记录 `sessionKey` 与 `sessionId`。
- 2026-04-29 17:57（北京时间）：为 OpenClaw 飞书群会话隔离继续止血；在 `/root/.openclaw/openclaw.json` 的 `channels.feishu.groups` 下新增 `oc_5db4fdccbb3e018b405fb6c6c9fb7243.groupSessionScope = "group_sender"`，与既有的 `oc_d47ec695600634cc6a6d9dd577bedd22` 保持一致。
- 现场结论：当前两个人机共同飞书群都已显式按发送人拆会话；其他未单独配置的飞书群仍按代码默认 `group` 走整群共享会话。
- 关联现状：`/new`、`/reset` 为渠道内置命令匹配，不依赖 `resetTriggers` 配置；memos-cloud 额外只支持 `command:new` 的 counter reset hook，不覆盖 `/reset`。
- 变更前备份：`/root/.hermes/backups/openclaw.json.before-add-second-group-sender-20260429-175730`。

### 0.1 补投递入口阶段结论（2026-04-29 21:14 北京时间）
- **现成内部入口：有。** 最靠谱的是本机 Gateway RPC `agent`，不是 CLI 表层 `openclaw agent --deliver`，后者当前 help 没暴露 Feishu 选项，拿来做补投递会误导。
- **低风险真实样本已做两轮，根因已从“会话漂移”进一步收紧。** 第一轮只传 `sessionId=89f35078-bb0d-49c2-96bf-e250b69af111` 时，探针文本 `[Wed 2026-04-29 21:10 GMT+8] 系统补投递链路验收：请只回复「补投递验收OK」` 与回复 `[[reply_to_current]] 补投递验收OK` 实际落在 `/root/.openclaw/agents/taizi/sessions/e748e404-8c81-4daa-ba44-739012f13003.jsonl`，即 `agent:taizi:main`（heartbeat 主会话），证明**只靠 `sessionId` 会漂移**。第二轮改为显式传 `sessionKey=agent:taizi:feishu:direct:ou_ed2187f2ad27e0b7876913371e72c06a` 后，探针文本 `[Wed 2026-04-29 21:26 GMT+8] 系统补投递链路验收2：请只回复「补投递验收OK2」` 已真实落在目标飞书直聊 transcript `/root/.openclaw/agents/taizi/sessions/89f35078-bb0d-49c2-96bf-e250b69af111.jsonl` 第 132 行，但第 133 行紧跟的 assistant 结果是 `stopReason=error`、`errorMessage="524 status code (no body)"`，没有生成任何回复文本；而 `agent:taizi:main` transcript 已无这轮 `OK2` 样本。当前更精确定性为：**`sessionKey` 已能把补处理入口绑定到正确飞书直聊 session；剩余阻塞已不再是会话漂移，而是该直聊 session 上游模型调用/网关返回 524，导致无回复回投。**
- **因此正式口径调整为两段式旁路补偿，而不是伪装成自动闭环。** 现阶段把这条入口定义为“补处理入口”，不要把它包装成“已证明能自动回投飞书”的方案。
- **正式落地物已补齐：**
  - 运行脚本：`/root/.openclaw/workspace/edict/scripts/openclaw_feishu_relay.py`
  - 运行手册：`/root/.openclaw/workspace/edict/docs/openclaw-feishu-bypass-compensation-runbook.md`
  - 值班模板：`/root/.openclaw/workspace/edict/docs/openclaw-feishu-bypass-duty-template.md`
  - 运行日志目录：`/root/.openclaw/workspace/edict/logs/feishu-relay/`
- **当前运营方案：**
  - `probe`：只验证 taizi 补处理入口
  - `send`：只做人工飞书补送达
  - `compensate`：先试 `agent` 注入，再按需人工 `send`，并把两步都留痕
- **当前判断：** 用户要求的“把这个入口正式收成可运营的旁路补偿方案”已完成；但该方案属于补偿链路，不是主链修复结论。后续若要升级为自动闭环，必须另外补通过“agent 注入后自动回投飞书”的真实证据。
- **2026-04-29 21:46（北京时间）新增根因收紧：** 当前 taizi 飞书直聊 `agent:taizi:feishu:direct:ou_ed2187f2ad27e0b7876913371e72c06a` / `89f35078-bb0d-49c2-96bf-e250b69af111` 的失败，已经不能再单独归因为会话绑定错误。现场证据显示：1）该直聊 session 在 `sessions.list` 中仍长期挂为 `status=running`，provider/model 为 `windhub/gpt-5.4`；2）对应 transcript 最近两次 assistant 结果都直接落成 `stopReason="error"`、`errorMessage="524 status code (no body)"`；3）同日 taizi 其他 session（含群聊与旧会话）也多次出现同款 `524 status code (no body)`，说明**524 属于 windhub/gpt-5.4 的系统性上游错误，不是这条直聊独有**；4）live log 另有 `lane wait exceeded: lane=session:agent:taizi:feishu:direct:ou_ed2187f2ad27e0b7876913371e72c06a waitedMs=146525 queueAhead=0`，说明这条直聊 session 自身还叠加了长跑/排队异常；5）embedded failover 日志明确 `fallbackConfigured=false`，而当前 `/root/.openclaw/openclaw.json` 的 `agents.defaults.model.primary` 仍是单一 `windhub/gpt-5.4`，没有实质可用的模型 fallback。因此当前更精确定性为：**主故障是 windhub/gpt-5.4 上游 524，无可用 fallback；飞书直聊 session 另有 running/lane 堵塞副作用，二者叠加导致“已绑定正确 session 但仍无回复”。**
- **2026-04-29 21:52（北京时间）新增止血动作：** 已按“改前先备份”要求先备份 live 配置到 `/root/.hermes/backups/openclaw.json.before-add-fallback-20260429-215201`，随后把 `/root/.openclaw/openclaw.json` 的 `agents.defaults.model.fallbacks` 恢复为 `["longcat/LongCat-Flash-Chat"]`。
- **2026-04-29 21:56（北京时间）重启后验收结果：** 已执行 `openclaw gateway restart`，gateway 新 PID 已切到 `3485982`。重启后再用 `sessionKey=agent:taizi:feishu:direct:ou_ed2187f2ad27e0b7876913371e72c06a` 打第三轮 probe（`系统补投递链路验收3`）时，返回形态已从之前的“很快落成 transcript 内 `524 status code (no body)`”变为 **`accepted_but_no_final` / 120s gateway timeout**；目标直聊 transcript 已新增用户行（第 135 行），说明 probe 仍能进入正确飞书直聊 session，但截至本轮截面尚未拿到 assistant 最终回复。新增 live log 还出现 `Removed orphaned user message to prevent consecutive user turns. runId=7c43103a-0b6b-468d-a359-bb464830988d sessionId=89f35078-bb0d-49c2-96bf-e250b69af111`，说明这条直聊 session 内部消息序列仍有脏状态需要清理。当前暂未在新日志里抓到 `fallbackConfigured=true` 的正向证据，因此只能下到这个口径：**重启+补 fallback 后，故障表象已从“快速 524 空 body”转成“能进正确 session 但长跑无 final”；说明现场有改善，但 session 脏状态/长跑问题仍未收口。**

> 本文件用于把 `docs/closeout.md` 与 `docs/governance-upgrade-map.md` 的主线结论压成一份持续跟进板。
> 目标不是重复全部长文，而是给阿爪/值守链一个**当前到哪了、卡在哪、下一步干什么**的统一入口。
> 另外自 2026-04-28 起，**所有系统改动（配置、服务、热修、回滚、守护脚本、运行态止血）默认都要同步汇总到 `docs/current-progress-board.md`**，避免后续出问题时现场分散、回溯找不到。
> **自 2026-04-29 起，这条要求升级为强制制度：系统有任何变动，都必须同步写入 `/root/.openclaw/workspace/edict/docs/current-progress-board.md`；不得只改现场不回写主板。**

---

## 1. 一句话总览

**edict / 三省六部治理升级主线目前处于：工程收口基本完成，backend host-native 已进入生产 dual/export 过渡态并出现真实导出证据；但前台写链 smoke、自然治理样本厚度与回滚验收仍未收口。OpenClaw / taizi 本轮已完成直连 DM 结构性修复与 provider/session 去钉死清理，且在晚间重启窗口后已再次拿到多轮 `received message -> dispatching to agent -> dispatch complete` 真实样本；当前不再是“DM 完全断链”，而是收敛为 **taizi 直聊 session 长跑 + 偶发消息整理脏状态** 的不稳定态；`menxia:main` 为历史噪声项，而 `shangshu:main` 本轮已完成 dashboard 重入止血与定点 session recovery。**

---

## 1.5 待审方案：三框架接入取舍与实施顺序（分为业务主链与玄成自身两部分）

### 仓库来源
1. `Superpowers`：<https://github.com/obra/superpowers>
2. `GenericAgent`：<https://github.com/lsdefine/GenericAgent>
3. `Evolver`：<https://github.com/EvoMap/evolver>

### 先说总结论
这件事不能只看 **OpenClaw / 阿爪 / edict 要不要接**，还要单独看 **玄成/Hermes 自己能不能从中得到提升**。

所以这里拆成两部分：
- **A 部分：对 OpenClaw / 阿爪 / edict 主链的接入取舍与实施顺序**
- **B 部分：对玄成/Hermes 自身能力层的可吸收点与实施顺序**

---

### A. 对 OpenClaw / 阿爪 / edict 的接入取舍与实施顺序

#### A-1. 结论
**不建议把三者当成同一层框架，直接并列塞进 edict / 阿爪生产主链。**

对业务主链的建议顺序是：
1. **先吸收 Superpowers 的方法论，内化成 edict 规则**
2. **再把 Evolver 作为只读演化侧车接入**
3. **GenericAgent 暂不进入主链，只保留实验舱**

#### A-2. 为什么这样排
这三者根本不是一类东西：
- `Superpowers`：更像**开发流程方法论 + skills/plugin 体系**
- `Evolver`：更像**演化治理引擎**
- `GenericAgent`：更像**高执行 runtime / 外勤执行体**

如果不分层，直接一起塞，会马上出现：
- skill 体系重复
- memory 边界冲突
- 调度权混乱
- 日志归因困难
- 故障面膨胀

#### A-3. 各自适合怎么用
##### 1) Superpowers
最适合阿爪 / edict 的不是它的壳，而是它的流程约束：
- 先澄清需求
- 先出 spec / design
- 再拆实现计划
- 强调 review / TDD / 验收

对 edict 的映射最顺：
- `中书`：需求澄清、规格成文、计划拆解
- `门下`：方案审查、风险把关、验收门槛
- `六部`：执行、验证、交付回写

**业务侧结论：先吸收方法论，不把它当生产运行时依赖。**

##### 2) Evolver
Evolver 对业务主链最有价值的地方在：
- 失败任务复盘
- 卡滞模式聚类
- 修复策略建议
- 治理规则加固
- 经验资产化沉淀

但它不该一上来就进入主写链：
- 它天然会碰演化、经验、治理边界
- 容易和现有 task-state / memory / skill 职责打架
- 仓库已明确未来版本会转向 source-available，长期依赖要更谨慎

**业务侧结论：作为只读分析侧车最合适，先给建议，不直接改主链。**

##### 3) GenericAgent
GenericAgent 强在：
- 登录态浏览器长链
- GUI 自动化
- ADB / 手机侧流程
- 自生长 skill tree

但它最不适合现在直接进 edict 主链：
- 它自己就有 memory / skill / scheduler 倾向
- 强执行 + 长链注入很容易把当前治理边界打散
- 最容易把“谁负责、谁留痕、谁回滚”搞乱

**业务侧结论：只配做隔离实验舱，不进入当前三省六部中枢。**

#### A-4. 对业务主链的实施顺序
##### Phase A1：先落 Superpowers 制度映射
先落这些：
- 任务前澄清模板
- 方案评审模板
- 实施计划模板
- 验证/验收清单
- 交付前 review 节点
- 子任务拆解与回写格式

目标：
- 先把 `中书-门下-六部` 的协作文本变硬
- 先减少“没讲清就开工”“验证通过冒充真实交付”这类老问题

##### Phase A2：再接 Evolver 只读演化侧车
输入源先限于：
- `docs/current-progress-board.md`
- 失败/回退日志
- 审批驳回原因
- 卡滞任务状态样本
- 已沉淀的治理规则与事故文档

输出只允许是：
- 演化建议
- 修复候选
- 加固建议
- 可审计经验资产

约束：
- 不允许直接改生产主链
- 不允许绕过门下审查
- 必须保留人工拍板点

##### Phase A3：最后预留 GenericAgent 实验舱
只在这些场景考虑启用：
- GUI 自动化
- 浏览器登录态长链
- ADB / 手机流程
- 高个性化外勤任务

隔离要求：
- 单独目录
- 单独日志
- 单独记忆
- 单独调度
- 单独故障归因
- 不直接接管三省六部主链

#### A-5. 业务侧拍板建议
> 对 OpenClaw / 阿爪 / edict，当前最稳的路是：先吃 Superpowers 的流程方法论，把制度和模板补硬；再把 Evolver 作为只读、可审计、人工复核的演化侧车接进来；GenericAgent 只保留实验舱，不进当前生产主链。

#### A-6. 业务主链执行 checklist（可直接开干）
##### A6-1. Phase A1：Superpowers 方法论内化
- [x] 在 `docs/templates/task-intake-clarification-template.md` 新增三省六部任务前澄清模板，明确：目标、范围、验收口径、风险、是否允许对外动作
- [x] 在 `docs/templates/plan-review-template.md` 新增方案评审模板，明确：中书输出、门下审查点、否决条件、回退条件
- [x] 在 `docs/templates/implementation-plan-template.md` 新增实施计划模板，明确：拆解粒度、责任角色、验证步骤、真实交付物
- [x] 在 `docs/templates/acceptance-checklist-template.md` 新增验收清单模板，明确区分“测试通过”“真实产出”“运行态证据”
- [x] 已将模板统一落到 `docs/templates/`，作为 edict 当前三省六部文档体系的模板入口，避免另起一套孤立口径
- [x] 已拿真实主线 `align-atomic-task-update` 做试跑，并在本板 `2.5 / 2.5.1` 回写本轮收口、边界与下一轮优先级
- [x] 试跑后已回写 `docs/current-progress-board.md`；当前已明确模板/制度的现实落点是：先把主线任务拆成执行清单与收口口径，但阿爪侧是否“流程过重”仍需后续继续观察

##### A6-2. Phase A2：Evolver 只读演化侧车
- [x] 已明确当前不接生产写链，先按只读治理侧车定位推进
- [x] 已明确第一批输入材料：`docs/current-progress-board.md`、事故文档、失败日志、审批驳回样本、卡滞任务样本，以及原子更新改造记录
- [x] 已明确第一批输出格式：演化建议、修复候选、治理加固建议、经验资产草案 / 批量写口候选 / 优先级排序
- [x] 已明确人工审查闸口：未经门下/人工拍板，任何建议不得直接进主链
- [ ] 先用 1~2 类高频问题做小样本验证，例如：任务卡滞、验收口径跑偏、重复事故
- [ ] 记录 Evolver 输出里哪些建议真有用，哪些只是空泛总结
- [ ] 只有在“建议质量稳定”后，才讨论是否扩大输入面

##### A6-3. Phase A3：GenericAgent 隔离实验舱
- [x] 已明确当前不接主链，只服务于 GUI / 浏览器登录态 / ADB / 外勤任务
- [ ] 单独准备目录、日志、记忆、调度边界，不与 edict 主链混写
- [ ] 先挑 1 个典型外勤任务做隔离试验，不碰主线治理任务
- [ ] 验证它的执行留痕、故障归因、回滚边界是否足够清楚
- [ ] 若试验期出现职责混乱、状态归属不清、日志难追，立即停止扩大使用范围
- [ ] 只有在“外勤价值明显 > 集成成本”后，才决定是否保留长期实验位

###### 当前拍板
- [x] 当前阿爪适配顺序固定为：**先 Superpowers 工作流层，再 Evolver 只读治理侧车，最后才是 GenericAgent 隔离实验舱**
- [x] 当前不允许把三者并列接进阿爪生产主链，避免 session / memory / scheduler / 日志归因打架

###### 当前实验舱定位
- [x] 当前阶段不并入生产主链，只保留实验舱定位

##### A6-4. 业务侧验收口径
- [ ] 不是写完文档就算完成，至少要有 1 次真实任务试跑证据
- [ ] 不是接上框架名字就算完成，要能证明对现有主链有净收益
- [ ] 任何接入只要让日志、职责、回滚变乱，就视为失败

##### A6-5. 阿爪执行清单（2026-04-29 再完善版）
###### Superpowers：先吸工作流，不装整套 runtime 壳
- [x] 阿爪收到开发/治理任务后，默认先补 `task-intake-clarification`，未澄清目标/范围/验收前不直接开干
- [x] 阿爪进入实施前，必须先补 `implementation-plan`，把文件、写口、验证命令、边界写清
- [x] 门下审查继续作为硬闸口；review / acceptance 不允许被“测试过了”替代
- [x] 六部执行结果必须回写 `docs/current-progress-board.md`，不得只留在聊天或临时日志里
- [x] 已先拿真实主线 `align-atomic-task-update` 做 pilot；当前至少已证明这套模板/制度能压缩成执行清单与收口口径，至于是否“过重”仍待后续继续观察

###### Evolver：只读治理侧车，不直接写生产链
- [x] 第一批只读输入已固定为：`docs/current-progress-board.md`、失败样本、审批驳回记录、flow log、卡滞任务、原子更新改造记录
- [x] 第一批输出已固定为：优先级排序、治理加固建议、批量写口候选、经验沉淀候选
- [x] 未经门下/人工拍板，Evolver 不得直接改 `tasks_source.json`、backend 数据、调度器、session、memory
- [x] 当前已明确让 Evolver 专打主线缺口排序：`adopt_court_conclusion` > `_startup_recover_queued_dispatches`（两段式）> backend create 一致性 > 其余散落 `load_tasks()+save_tasks()` 写口
- [ ] 只有当建议质量稳定、且能减少真实返工后，才扩大输入面

###### GenericAgent：隔离外勤执行体，不进阿爪中枢
- [x] 只允许用于 GUI、浏览器登录态、ADB、长链外勤，不接管三省六部主链
- [ ] 单独目录、单独日志、单独记忆、单独调度、单独故障归因，避免污染阿爪主上下文
- [x] 只接受阿爪派单，结果必须先回流给阿爪，再由阿爪统一汇报，不得抢本体回话权
- [x] 若出现职责混乱、日志不可追、回滚不清，立即停用该路线
- [x] 当前阶段不并入生产主链，只保留实验舱定位

###### 当前拍板
- [x] 当前阿爪适配顺序固定为：**先 Superpowers 工作流层，再 Evolver 只读治理侧车，最后才是 GenericAgent 隔离实验舱**
- [x] 当前不允许把三者并列接进阿爪生产主链，避免 session / memory / scheduler / 日志归因打架

---

### B. 该方案对玄成 / Hermes 自己有没有提升空间

#### B-1. 结论
**有，而且这部分其实比业务主链更适合先吸收。**

原因很简单：
- 玄成本来就承担“本体接活、分身督办、统一收口”的角色
- 很多能力如果先落在玄成自己身上，风险远低于先改阿爪主链
- 先把玄成自身做强，再反哺 OpenClaw / edict，会更稳

#### B-2. 三个框架分别能提升玄成什么
##### 1) Superpowers 对玄成的提升
这部分最适合马上吸收。

可直接提升的点：
- 任务先澄清、再开工
- 先出 spec / plan，再执行
- 复杂任务拆成可验证小步
- 执行前后都做 review
- 先验收、再宣称完成

这和你现在对我的要求几乎完全一致。

**对玄成的结论：Superpowers 最适合直接内化进我的工作方式。**

##### 2) Evolver 对玄成的提升
这部分适合做“经验升级器”。

可提升的点：
- 从多轮任务里提炼稳定经验
- 把重复踩坑沉淀成更强的治理规则
- 给我自己的 skill / memory / 处置策略做版本化演化
- 给“为什么这次判断失误 / 为什么这类任务反复出错”提供更可审计的解释

也就是说，它不只是能帮阿爪，也能帮我自己少重复犯错。

**对玄成的结论：Evolver 适合作为我的后台演化器，但先只读、先建议，不直接全自动改人格/规则。**

##### 3) GenericAgent 对玄成的提升
这部分也有用，但不该先上主线。

可提升的点：
- 给玄成补一类“高执行外勤分身”
- 处理 GUI / 浏览器登录态 / ADB 这类 Hermes 现阶段不够顺手的任务
- 作为专职外勤 agent，替本体去跑长链实操

但风险同样大：
- 很容易把“本体判断”和“外勤执行”混成一坨
- 也容易把日志、记忆、责任边界搞乱

**对玄成的结论：可以作为外挂型执行分身研究，但不能直接混进本体。**

#### B-3. 对玄成自身的实施顺序
##### Phase B1：先吸收 Superpowers 方法论
优先落到我自己的行为规范里：
- 复杂任务先澄清目标
- 先出计划，再施工
- 执行过程中按阶段汇报
- 先验证，再报完成
- 高风险动作继续先请示

这部分其实最该先做，因为几乎零副作用。

##### Phase B2：再让 Evolver 做玄成的后台演化器
优先让它分析这些材料：
- 失败任务
- 用户纠正记录
- 已形成的 skill
- 长期重复事故
- 判断偏差样本

输出：
- 更优规则建议
- 经验升级建议
- 可沉淀为 skill 的流程
- 可写入 memory / USER 规则的稳定结论

##### Phase B3：最后再研究 GenericAgent 型外勤分身
只在这些场景研究：
- 桌面 GUI 任务
- 登录态浏览器长链
- 手机 / ADB 执行
- 需要长时间自主摸索的外勤流程

前提：
- 必须和玄成本体隔离
- 只做执行，不抢本体回话权
- 结果必须统一回流给玄成再对外汇报

#### B-4. 对玄成侧的拍板建议
> 对玄成/Hermes 自身，最值得先吸收的是 Superpowers 的工作方法；其次才是用 Evolver 做后台经验演化；GenericAgent 只适合后续研究成“外挂型外勤分身”，不应直接混进玄成本体。

#### B-5. 玄成自身升级 checklist（可直接开干）
##### B5-1. Phase B1：先吸收 Superpowers 工作法
- [ ] 把“复杂任务先澄清、先出计划、再执行、先验证再报完成”固化进玄成当前工作规范
- [ ] 把“不要拿测试通过冒充真实交付”继续作为显式验收规则保留
- [ ] 把复杂任务的阶段汇报格式统一成：做到哪、结果是什么、还有什么风险、下一步干什么
- [ ] 给多步骤任务默认补一层 checklist / todo 约束，避免做着做着跑偏
- [ ] 选 1~2 条复杂真实任务复盘，检查当前玄成是否已经按这套工作法稳定执行
- [ ] 若发现规则已有但执行不稳，优先补规则落地，而不是继续加新口号

##### B5-2. Phase B2：让 Evolver 做玄成后台演化器
- [ ] 先只读分析玄成的失败任务、用户纠正、长期重复事故、已有 skill
- [ ] 明确输出只允许是：规则优化建议、经验升级建议、skill 候选、memory 候选
- [ ] 不允许它直接改玄成的人格规则、记忆、skill，本轮先做人审建议稿
- [ ] 先拿 1 类高频错误做验证，例如：验收口径跑偏、任务收口不彻底、阶段汇报失真
- [ ] 记录哪些建议真能减少重复纠错，哪些只是正确废话
- [ ] 只有当建议质量稳定后，才考虑把部分建议转成半自动沉淀流程

##### B5-3. Phase B3：研究 GenericAgent 型外挂外勤分身
- [ ] 明确它只做外勤执行，不参与本体判断与最终回话
- [ ] 优先研究 Hermes 现阶段不够顺手的场景：GUI、登录态浏览器、ADB、长链实操
- [ ] 单独保留日志、记忆、任务边界，避免污染玄成本体上下文
- [ ] 外勤结果必须先回流给玄成，再由玄成统一对外汇报
- [ ] 若出现本体/分身职责混淆、结果不可复核、日志不可追，则立即停用该路线
- [ ] 只有在“明显补足 Hermes 执行短板”后，才保留为长期能力位

##### B5-4. 玄成侧验收口径
- [ ] 不是加了几条规则就算升级完成，要看后续真实任务里用户是否明显少纠正
- [ ] 不是多了一个外勤分身就算能力增强，要看是否真的补上 Hermes 当前短板
- [ ] 任何升级只要让本体判断变混乱、汇报变失真、责任边界变模糊，就视为失败

### 当前总建议
> **业务主链（OpenClaw / 阿爪 / edict）**：先方法论，后演化侧车，最后实验执行体。  
> **玄成自身（Hermes）**：先吸收 Superpowers 工作法，再引入 Evolver 做后台演化，最后再研究 GenericAgent 外勤分身。

### 当前状态
- **该方案现已拆成业务主链与玄成自身两部分**
- **两部分的结论不完全一样：对玄成自身，吸收优先级更高；对业务主链，接入要更保守**
- **业务主链侧执行清单已补到 A6-5，当前已进入执行态**
- **当前交接口径已明确：由阿爪按 A6-5 与 2.5.1 继续落实，不再停留在“待拍板/待拆清单”阶段**

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

## 2.5 2026-04-29 align-atomic-task-update：modify_tasks()/modify_task() 扩面一轮收口

### 本轮目标
- 继续扫描 `dashboard/server.py` 中剩余仍走 `load_tasks() + save_tasks()` 的写口
- 优先处理高频 / 高风险写口，按本轮要求聚焦：
  - `handle_archive_task`
  - 创建任务路径 `handle_create_task`
  - `handle_review_action`
  - 任务修复 / 回填类批量写口 `handle_repair_flow_order`
- 每轮改后执行：`python3 -m py_compile /root/.openclaw/workspace/edict/dashboard/server.py`
- 本轮不扩张到 `qintianjian agent`、动画 / UI、服务重启、配置改动或对外通道操作

### 本轮已完成迁移
1. **`handle_archive_task` → 已迁入原子更新框架**
   - 单任务归档 / 取消归档：改为 `modify_task()`
   - `archive_all_done` 批量归档：改为 `modify_tasks()`
   - 归档批量口现在不再直接 `load_tasks() + save_tasks()`

2. **`handle_review_action` → 已迁入原子更新框架**
   - 原先整段御批逻辑基于 `load_tasks() + save_tasks()` 改写
   - 现改为通过 `modify_task()` 完成状态推进、`pending_confirm` 清理、`gate_checks` 回写、`flow_log` 追加与 `updatedAt` 更新
   - `_notify_review_result()` 与 `dispatch_for_state()` 保持在原子写完成后执行，避免把外部副作用塞进 JSON 锁内

3. **`handle_repair_flow_order` → 已迁入原子更新框架**
   - 该批量回填口已改为 `modify_tasks()`
   - 仍保留原有修复语义：修正首条流转 `皇上 -> 中书省` 为 `皇上 -> 太子`，并在符合条件时把 `Zhongshu/中书省` 纠正回 `Taizi/太子`

4. **`handle_create_task` → 已把 JSON fallback 写链迁入 `modify_tasks()`**
   - 本地 JSON 写链已不再直接 `tasks.insert(...) + save_tasks(...)`
   - 改为在 `modify_tasks()` 内完成当日流水号计算、`new_task` 组装、插入与调度前快照字段补齐
   - 调度 `dispatch_for_state()` 仍保留在写入后执行，避免把派发副作用塞进原子更新闭包

### 语法校验结果
- 本轮每轮关键改动后都执行了：
  - `python3 -m py_compile /root/.openclaw/workspace/edict/dashboard/server.py`
- 当前结果：**通过**
- 说明：该结果只证明本轮 patch 语法层面未炸，不等于运行态已自动生效；本轮未重启服务，也未宣称现网已切换

### 扫描后仍残留的 `load_tasks() + save_tasks()` 直写口
按 2026-04-30 这轮继续收口后的结果，上一版列出的两处高价值写口已处理：
1. **`adopt_court_conclusion` → 已迁入 `modify_tasks()`**
   - 去掉了整段 `load_tasks()` 后原地改 `target_task.todos` / 插入 `COURT-*` 任务，再统一 `save_tasks(tasks)` 的写法
   - 现改为在 `modify_tasks()` 内完成 todo 追加、`COURT-*` 任务插入与 `updatedAt` 回写
   - `rule` 仍保持独立 `atomic_json_update(shared_memory.json)`，不与任务写锁硬绑在一起

2. **`_startup_recover_queued_dispatches` → 已按“两段式”拆开**
   - 去掉了 `load_tasks()` 后边扫边改、边改边 `dispatch_for_state()` 的混合写法
   - 现改为：
     - 第一步：`modify_tasks()` 内只做 `queued` 任务筛选、`startup-recovery` 标记回写、`shangshu main-session guard` 抑制修正
     - 第二步：写后再对 recoverable snapshot 执行 `dispatch_for_state()`
   - 这样外部派发副作用不再塞在 JSON 写锁内

### 本轮未迁但不属于本轮目标的 `load_tasks()` 读口
以下扫描命中仍主要是读口 / 面板聚合口，本轮未动：
- `get_scheduler_state`
- `get_approval_panel`
- `get_timeout_summary`
- `get_jidipu_panel`
- `get_command_panel`
- `get_task_autopsy`
- `get_guoshiguan_panel`
- `handle_scheduler_scan`（本轮未改）
- `get_task_activity`
- `/api/task-output/*` 输出读取路径

### 当前残留风险
1. **创建任务路径在 backend 模式下仍有一致性风险**
   - 本轮已把 JSON fallback 写链收进 `modify_tasks()`，但 `dual/api` 模式下 backend create 仍走独立请求
   - 由于 backend create 与本地 JSON 流水号生成是两条链，`legacy_id` / 当日流水号的一致性仍需后续单独收口，不能把“fallback 已原子化”误报成“backend create 也完全收口”

2. **`adopt_court_conclusion` 仍是剩余高价值批量写口**
   - 同时涉及“给现有任务追加 todos”与“插入新 COURT 任务”两类修改
   - 若继续推进 align-atomic-task-update，建议下一轮优先拿它开刀

3. **带外部副作用的写口仍需坚持“两段式”拆法**
   - 像 `dispatch_for_state()`、通知、启动恢复这类动作，不应直接塞进 `modify_tasks()` 闭包
   - 否则会把 JSON 原子更新与外部副作用锁死在一起，后续更难排障

### 当前结论
- **本轮已完成一轮有实质价值的原子更新扩面**：归档、review、修复回填、创建任务 fallback 写链均已纳入 `modify_task()` / `modify_tasks()`
- **本轮未越界**：未扩张到 `qintianjian`、动画/UI、服务重启、配置改动或对外通道
- **下一轮优先级建议**：`adopt_court_conclusion` > `_startup_recover_queued_dispatches` / `handle_scheduler_scan` 相关写链

### 2.5.1 2026-04-29 再完善版收口（给阿爪执行侧的明确口径）
1. **这轮已经是“真收口一轮”，不是只过语法**
   - 代码提交已存在：`53bf28e`
   - 提交信息：`Expand atomic task updates in dashboard server`
   - `python3 -m py_compile /root/.openclaw/workspace/edict/dashboard/server.py` 已通过
   - 但这仍只代表：**本轮 patch 已落盘且语法未炸**；不代表 backend/现网所有相关链路已自动验收完成

2. **阿爪后续落实时，必须按“两段判断”汇报，不准再把“改了代码”说成“全链收口”**
   - 第一段：本轮到底收了哪些写口（`handle_archive_task` / `handle_review_action` / `handle_repair_flow_order` / `handle_create_task` JSON fallback）
   - 第二段：哪些高风险链路还没收（`adopt_court_conclusion`、`_startup_recover_queued_dispatches`、backend create 一致性）
   - 没有真实运行态/自然样本证据前，不得把“atomic 扩面一轮完成”包装成“任务写链已整体收口”

3. **阿爪下一轮执行靶点已经明确，不要再散打**
   - 第一优先级：`adopt_court_conclusion`
   - 第二优先级：`_startup_recover_queued_dispatches`，但必须按“两段式”拆成“原子状态修正 + 写后外部派发”
   - 第三优先级：backend create 链路的一致性核查，重点盯 `legacy_id` / 当日流水号 / dual-api 与 JSON fallback 的口径差异
   - 本轮之外的读口、面板聚合口、UI/动画/qintianjian 路线继续不碰

4. **阿爪执行边界**
   - 不允许把通知、派发、恢复性外部动作粗暴塞进 `modify_tasks()` / `modify_task()` 闭包
   - 不允许为了追求“全都原子化”而把带副作用链路锁死到 JSON 写锁里
   - 不允许把 backend create 未收口部分藏掉，必须继续在主板上保留“fallback 已收、backend 主链未完全收”的明确口径

5. **阿爪下一轮验收口径**
   - 至少给出 1 次真实改动后的运行态证据，不许只报 py_compile 通过
   - 至少明确“改了哪个函数、去掉了哪段 `load_tasks()+save_tasks()`、副作用如何移到写后”
   - 若下一轮动到启动恢复/派发链，必须额外说明：有没有新增重复派发、锁等待、状态错乱风险


### 2.5.2 2026-04-30 阿爪执行侧续收口（align-atomic-task-update）
1. **这轮实际收了什么**
   - `adopt_court_conclusion`
     - 去掉了原先整段 `load_tasks()` + `save_tasks(tasks)` 写法
     - 改成 `modify_tasks()`：在闭包内完成 target task todo 追加、`COURT-*` 任务插入、`updatedAt` 回写
   - `_startup_recover_queued_dispatches`
     - 去掉了原先 `load_tasks()` 后一边改 `_scheduler`、一边直接 `dispatch_for_state()` 的混合写法
     - 改成“两段式”：先 `modify_tasks()` 做原子状态修正与 recoverable snapshot 收集，再在写后执行 `dispatch_for_state()`

2. **这轮运行态证据**
   - 已跑最小 Python 运行态脚本，不只停留在 `py_compile`
   - 证据要点：
     - `adopt_court_conclusion` 已真实写入 1 条 `todo` 与 1 条 `rule`
     - `adopt_court_conclusion` 已可真实插入 `COURT-*` 任务，产物 `source=court_discuss`
     - `_startup_recover_queued_dispatches` 已验证只重派发 `queued->gongbu` 样本 1 条；`queued->shangshu` 样本被改写为 `suppressed-main-session-guard`，未发生重复派发
   - 运行态脚本现场还踩出一处真实缺口：两段式拆分后初版遗漏 `copy` 导入；已当场补齐，不是只凭静态眼测过关

3. **副作用如何移到写后**
   - `_startup_recover_queued_dispatches` 中外部副作用仅剩写后阶段的 `dispatch_for_state()`
   - `modify_tasks()` 闭包内不再直接做派发线程启动，避免把恢复性外部动作锁进 JSON 原子写区

4. **这轮仍未收的项**
   - `backend create` 一致性已继续前推一轮，但还不能叫“整体收口”
   - `handle_create_task` 在 `dual/api` 模式下，已不再走 `_create_task_via_backend(legacy_id=f'JJC-{today}-PENDING', ...)`
   - 现已改为：
     - 先基于现有任务快照计算 `candidate_task_id`
     - backend create 直接使用真实当日流水号 `legacy_id`
     - 若 backend 失败再 fallback，本地 `modify_tasks()` 会重新基于最新 tasks 计算实际可用流水号，避免把已被占用的候选号硬写回 JSON
   - 但结论仍必须保持：**legacy_id / 当日流水号口径已明显收紧，不等于 backend create 主链已整体收口**

5. **这轮启动恢复风险说明**
   - 重复派发：当前最小运行态样本未见新增 `shangshu` 重复派发；guard 仍生效
   - 锁等待：两段式后，派发动作已移出 `modify_tasks()`，理论上比原实现更不容易把外部阻塞带进 JSON 写锁
   - 状态错乱：当前 recoverable 样本保留 `queued` 状态并在写后派发，`shangshu` 抑制样本则改写为 `suppressed-main-session-guard`；最小样本未见状态错乱，但仍缺更厚的自然样本


### 2.5.3 2026-04-30 阿爪执行侧续收口（backend create 一致性）
1. **这轮实际收了什么**
   - `handle_create_task`
     - 去掉了 backend create 路径里固定传 `legacy_id=f'JJC-{today}-PENDING'` 的写法
     - 改成先基于当前任务快照计算 `candidate_task_id`
     - backend create 直接带真实当日流水号进 `_create_task_via_backend()`
   - `_create_task_via_backend`
     - 返回值补齐 `legacyId`
     - 保持 `taskId=legacy_id`，让 dual/api 返回口径与 fallback 更一致
   - 新增 `_next_legacy_task_id(tasks, today, preferred=None)`
     - 统一 backend create 候选号与 fallback 本地落盘号的生成逻辑
     - fallback 时若候选号已被别的写入占用，会在 `modify_tasks()` 内重新计算真实可用号，而不是硬写旧候选号

2. **这轮运行态证据**
   - 已跑最小 Python 运行态脚本，不只停留在 `py_compile`
   - 证据要点：
     - helper 口径：`JJC-20260430-001/002` 已存在时，优先候选号为 `003`；若 `003` 已被占用，则自动推进到 `004`
     - dual/backend 成功链：`handle_create_task()` 已真实把 `legacy_id=JJC-20260430-003` 传给 backend，不再出现 `PENDING`
     - fallback 回退链：当 backend 失败且 `003` 已被并发占用时，本地 JSON 实际创建为 `JJC-20260430-004`，说明 fallback 与最新 tasks 快照重新对齐，未把过期候选号硬写落盘

3. **这轮仍未完全收的项**
   - backend create 当前收紧的是：
     - `legacy_id`
     - 当日流水号
     - dual/api 与 fallback 的返回口径一致性
   - 但还没拿到更厚的现网自然样本去证明：
     - backend create 后导出面与 live status 长时间稳定一致
     - 更复杂并发场景下没有新的序号漂移/重复号
   - 所以当前只能说：**backend create 一致性已明显前推一轮，不等于整条 create 主链已最终验收完成**

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
