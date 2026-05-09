# review correction notes

更新时间：2026-05-06 18:18（北京时间）

## 文档定位
这份文档现在按**正式定稿版**维护。

它分两层：
1. **正式结论正文**：只保留当前仍成立、适合交接和引用的结论。
2. **证据附录**：保留 2026-05-05 当天多轮继续下钻的原始证据链，供追溯，不再把它们混写成正文。

如果正文与附录的旧阶段判断有冲突，**以正文为准**。

## 一句话结论
**edict 不是完全不可用；派发链能跑，真正的主问题是：runtime 已推进，但 backend 主任务实体没有跟进，systemd 常驻的 backend export 又把这份旧主状态持续覆盖回主视图，dashboard scheduler scan 再基于空 `_scheduler` 和旧 `updatedAt` 固定节奏重复派发，于是形成“会话在推进、主视图不收敛、同一任务反复重派”的稳定失真链。**

## 背景
2026-05-05 的现场复查，最初是为了确认 `edict` 到底是不是“已经完全不可用”。

首轮核实后可以先排除这个说法：
- backend API 活着；
- dashboard 活着；
- workers 活着；
- 至少 `zhongshu` 方向的自动派发还能真实成功；
- OpenClaw runtime / transcript 侧也能看到任务推进痕迹。

所以问题不在“任务完全派不出去”，而在**派出去以后，多层状态为什么不能稳定收敛成同一个事实源**。

## 当前现状
### 1. 可用性现状
- `edict` 仍可用，但不是稳态可用。
- 自动派发链没死，至少对 `zhongshu` 方向能看到真实 success 回执。
- runtime 会话侧能看到任务已推进到更后状态（如 `Menxia`）。

### 2. 主视图现状
- `tasks_source.json` 当前不是纯 runtime/governance 聚合真相，现场一度被 `backend_export` 全量覆盖。
- `live_status.taskSource = backend_api_export` 不是 refresh 层误判，而是上游主视图真实反映。
- `tasks_governance_samples.json` 对纯推进态任务存在漏收，不足以稳定承担“第二来源”。

### 3. 主状态现状
- backend 主任务实体对关键任务仍停在旧态，如：`Zhongshu + scheduler={} + progress_log=[] + output=''`。
- runtime 会话侧虽然能看到 `Menxia`，但这一步没有稳定沉淀回 backend 主任务实体。

## 最终根因链
当前最接近现场真相的根因链，应收口为下面 6 步：

1. **`edict-loop.service` 常驻开启 `EDICT_ENABLE_BACKEND_EXPORT=true`**，backend export 不是历史尾巴，而是仍在生效的现行覆盖链。
2. **backend 主任务实体本身没有收敛到 runtime 已推进的状态**，仍停在旧的 `Zhongshu + scheduler={}`。
3. **dispatch worker 只会记 `progress/output` 痕迹，不会直接推进主状态；orchestrator 也不消费 `agent.output/agent.thoughts` 去驱动主状态机**。
4. **`sync_from_openclaw_runtime.py` 只是 transcript 观察层**，它能把会话文本语义推断成 `Menxia`，但它不反写 backend。
5. **backend export 持续把 backend 旧态重新写回 `tasks_source.json`**，而 governance sample 对这类纯推进态又不能稳定形成第二来源。
6. **dashboard scheduler scan 每轮面对的都是 `_scheduler={}`、`updatedAt` 很老的旧任务**，于是稳定把同一任务识别成停滞任务，再次自动派发到 `zhongshu`。

一句话压缩就是：

> **runtime 会推进，backend 不会跟；export 会放大旧态；scheduler scan 会把旧态当停滞任务反复重派。**

## 为什么会出现“双真相”
当前系统实际并行维护了两套状态世界：

### 1. backend 主状态世界
- 来源：`transition_state()`、`review_action()`、停滞处理等结构化状态入口。
- 载体：DB task entity。
- 问题：当前没有自动消费 runtime 推进事实的回写链。

### 2. runtime 会话观察世界
- 来源：OpenClaw transcript 文本。
- 载体：`tasks_runtime_view.json`。
- 问题：它能“看出来”任务到了 `Menxia`，但不能强制 backend 主状态跟上。

所以现场出现的不是简单同步延迟，而是：

> **一个是“写进去的主状态”，一个是“看出来的会话真相”；两者之间缺正式汇流桥。**

## 风险
### 1. 调度风险
- 同一任务会被固定节奏重复派发。
- 派发成功不等于状态收敛，反而可能持续制造重复动作和误判。

### 2. 可见性风险
- 值守者看 `tasks_source/live_status` 和看 runtime transcript，会得到两套不一致的现实。
- 很容易误把“主视图没动”理解成“任务没处理”。

### 3. 治理风险
- `governance sample` 漏收纯推进态任务，导致它无法稳定承担治理沉淀层职责。
- 旧结论若只看前半轮排查，容易把问题错压到 provider、taizi、dispatch_worker 单点，而忽略主链失真。

## 正确值守口径
后续如果再对外或对内解释现场，不要再用这些说法：
- “edict 完全不可用”
- “任务派不出去”
- “provider 没回，所以任务没推进”
- “只是 dashboard 看错了文件”

更准确的口径应是：

> **派发链还能跑，但主任务状态收敛链没打通。runtime 会话能推进，backend 主实体没跟上，backend export 又把旧主状态持续放回主视图，dashboard 因此继续按旧态重复派发。问题的中心不是‘能不能派’，而是‘派后为什么不能稳定收敛’。**

## 下一步建议
按优先级，后续该盯的不是泛泛“继续查同步”，而是下面这 4 件事：

1. **先确认并处理 `edict-loop.service` / `EDICT_ENABLE_BACKEND_EXPORT=true` 这条常驻覆盖链**。
2. **补 runtime / agent 输出事实进入 backend 主状态机的正式回写链**。
3. **补 backend `scheduler` 调度记忆的稳定持久化**，避免 `_scheduler={}` 每轮被洗回空白。
4. **再决定是否调整 governance sample 准入与主视图聚合策略**，让纯推进态任务能形成稳定第二来源。

## 2026-05-06 继续复核补记：后续统一按 10 层模型值守，不再沿用 5 层口径

这轮补记不是推翻前文结论，而是把**后续怎么继续核、怎么继续写、怎么避免再漏层**先固定下来。

截至目前，`docs/current-progress-board.md` 与本文正文已经足以说明主矛盾不是“完全派不出去”，而是**派发链能跑，但主状态收敛链和展示链持续失真**。因此后续复核若仍只按“文字层 / 代码层 / DB 层 / dry-run 层 / runtime 层”五层看，会漏掉几条已经在现场反复制造误判的关键链路，尤其是：
- `scheduler scan` 自身是否仍在重复派发；
- `backend export` 是否仍把旧态持续回灌；
- `Redis / dispatch / orchestrator` 事件链到底有没有把推进事实送进 backend 主状态机；
- `live_status / samples / dashboard` 是否继续把多层旧态聚成看似“合理”的假真相；
- `_ensure_scheduler()` 这类规范化函数是否用默认值把故障特征洗平。

所以从这轮开始，更合适的值守框架应固定成下面 **10 层模型**。

### 1. 文字层
核 `board / 文档 / 口径` 是否和现场一致，重点防止：
- 主板已改口，但值守文档仍沿用旧说法；
- 现场已切闸/已止血，但正文还保留“当前仍开启”的过时结论；
- 或反过来，文档先写“已收口”，现场却没真正生效。

### 2. 代码层
核 `dashboard/server.py`、`scripts/run_loop.sh`、`export_backend_tasks_to_legacy_json.py`、`dispatch_worker.py`、`orchestrator_worker.py` 等关键代码，确认问题是否真改到点上，而不是只补了文案或测试。

### 3. DB 层
核 Postgres 主任务实体是否正确，重点看：
- `state / assignee_org / updated_at / progress_log / output / _scheduler`；
- backend 主状态是否仍停在旧态；
- 结构化状态入口是否真把任务往前推进。

### 4. dry-run 产物层
核测试、模拟调用、局部 probe 的输出是否符合预期。这里既包括：
- pytest / 脚本级回归是否通过；
- 也包括定点 probe 某段逻辑时，结果是不是只在函数层“看起来对”，但落盘/落库后又变形。

### 5. runtime 层
核真实 `agent / session / process` 是否在跑、跑到哪一步、是否报错，重点区分：
- runtime transcript 里已经推进；
- 还是其实 agent 根本没跑、只是文档误判。

### 6. 调度层
单独核 `scheduler scan` 是否仍在重复派发，不能再把它混进 runtime 或代码层笼统表述。要直接看：
- scan 周期内有没有新的重复 dispatch；
- suppress / guard 是否真的吃到运行态；
- 是否仍存在 `_scheduler={}` + 旧 `updatedAt` 被稳定识别成停滞任务的问题。

### 7. 导出层
单独核 `backend export` 是否继续把旧态回灌：
- `EDICT_ENABLE_BACKEND_EXPORT` 是否还开着；
- `tasks_backend_export_meta.json` 是否继续刷新；
- `tasks_source.json` 是否仍被 backend `/api/tasks` 定时覆盖。

### 8. 事件层
单独核 `Redis / dispatch / orchestrator` 链是否真打通。关键不是“有事件”，而是：
- `dispatch_worker` 发布的事实有没有被下游消费；
- `orchestrator` 是否真的把推进结果喂回 `transition_state()` 或等价主状态入口；
- 是否还停留在“只记录 output/progress，不推动主状态”的半截链路。

### 9. 展示聚合层
单独核 `live_status / tasks_governance_samples / tasks_runtime_view / dashboard` 是否继续失真。重点不是看“有没有数据”，而是看：
- 同一任务在多层是不是仍给出两套甚至三套现实；
- `live_status.taskSource` 与 `taskLayers` 是否仍在认旧态；
- governance sample 对纯推进态是否仍漏收。

### 10. 默认值污染层
这是这轮新增必须单列的一层。重点核：
- `_ensure_scheduler()` 这类规范化 / 补默认值函数，是否把原始故障特征抹掉；
- 是否把“缺失 / 异常 / 旧态 / 空调度记忆”洗成一个看上去结构完整、但其实已经失真的“正常对象”；
- 从而让值守者误把“默认值补齐后的对象”当作真实现场。

当前 `scheduler` 这条线尤其要防这个坑：如果先让 `_ensure_scheduler()` 给任务补上 `stallThresholdSec / maxRetry / lastProgressAt / snapshot` 等默认值，再去判断它是不是“旧态空轨迹任务”，那故障特征就已经先被规范化函数洗掉了。

## 这 10 层模型对本文的实际意义
这不是额外造框架，而是给后续值守立一条更稳的检查顺序，避免再次出现下面这种误判：
- 只看 runtime，误以为“任务已经推进，所以主链没事”；
- 只看 backend，误以为“任务没动，所以 agent 根本没跑”；
- 只看 live_status，误以为“refresh 写错了口径”；
- 只看代码 diff，误以为“guard 已加，所以重复派发应该已彻底解决”；
- 只看补完后的 `_scheduler`，误以为调度记忆本来就存在。

更准确的后续值守方式应是：

> **以后复核 edict，不再只问“派没派出去”，而是按 10 层逐条问：文本口径是否真对、代码是否真生效、DB 是否真更新、dry-run 是否真落结果、runtime 是否真推进、scheduler 是否真止重派、export 是否真停回灌、事件链是否真打通、展示聚合是否真不失真、默认值函数是否把故障洗平。**

这一段本身不替代前面的根因链，但它决定了后续 `review-correction-notes.md` 与 `current-progress-board.md` 应怎样继续增量维护，才能避免再次把不同层的问题混写成一句“系统看起来怪怪的”。

## 首轮复查结论（保留原始现场口径）
### 2026-05-05 复查补记：按主板要求对文字层 / 代码层 / DB层 / dry-run 产物层 / runtime 层做现场核实

这轮不是泛读代码，而是按 `docs/current-progress-board.md` 里 A6-5、2.5.1 的口径，直接对 edict 现网做五层复查，并专门核实“任务是否还能真实派发进 edict”。

先说总结：

> **edict 不是完全不可用，任务派发链也不是全断。当前现场仍能看到任务被自动派发进 `zhongshu`，并且 runtime 会话里已经推进到 `Menxia`。但系统稳定性并未收口：主板宣称过的若干“已切回 tasks_source / 已去掉 backend export 误报 / 三层视图已对齐”的结论，在 2026-05-05 这次现网复查下并不完全成立；当前最突出的现实问题是主视图、runtime 视图、governance sample、backend live-status 四层仍有状态脱节。**

（以下首轮五层复查原文保留，供追溯。）

## 证据附录：2026-05-05 后续继续下钻原始链路
说明：以下内容保留为证据堆栈，价值在于展示“结论如何一轮轮收紧”。
不再把其中每一轮的中间判断当作当前最终口径直接引用。

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

> **1. runtime 推进态无法稳定升格为主视图真相；**
> **2. governance sample 对纯推进态任务存在结构性漏收；**
> **3. live_status 继续显示 backend_api_export，不是误判，而是上游主视图确实还混着 backend_export 任务。**

也就是说：
- 不是 runtime 一点用都没有；
- 不是 live_status 自己瞎显示；
- 也不是 governance sample 本该全量收、只是这次偶然没收。

更准确的当前口径应更新为：

> **edict 当前的核心问题已经收紧为“推进态真相提升失败”：runtime 看得到，主视图抬不上去，样本层还会漏收，最终导致 live_status 继续暴露旧的 backend_export 主状态。**

## 2026-05-05 再继续复查补记：backend export 不是历史残留，而是当前 loop 仍在显式开启

在上一轮把问题收紧到“推进态真相提升失败”后，我继续往下看进程现场、`run_loop.sh` 运行环境和 systemd 落点。新的结论比前一轮更硬：

> **当前 `backend_api_export` 不是旧数据尾巴，也不只是某处文档口径没更新；而是运行中的 `run_loop.sh` 进程现在就带着 `EDICT_ENABLE_BACKEND_EXPORT=true`，在持续执行 backend export 覆盖链。**

### 1. 现场进程环境已直接坐实：run loop 现在就是开着 backend export 跑的
（以下证据附录原文继续保留，不再在正文重复展开。）
