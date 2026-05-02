### 已回写文件
- `docs/review-correction-notes.md`
- `docs/current-progress-board.md`（如后续正式任务推进并补到 output/progress_log，应同步更新主板口径）

## [2026-05-02 09:08] 正式复核任务停在 Assigned，执行链未把结果回写到任务 output / progress_log
- 提出人：纪火焰
- 状态：open
- 复核对象：`docs/current-progress-board.md` / `docs/review-correction-notes.md` / edict 正式复核任务链

### 发现的问题
- 当前用于承载正式复核的任务，现场仍可见停在 `Assigned` 但**没有执行回写痕迹**，这会让“已派发”与“已执行”在看板上混成一件事。
- 现场抽查到的正式任务样本包括：
  - `JJC-20260502-002` / `edict backend 主链最终验收`：当前 `state=Assigned`，`output` 为空，`progress_log` 为空；最后一条 `flow_log` 仅到 `Menxia -> Assigned`。
  - `JJC-20260502-001` / `edict session隔离方案验收`：当前同样 `state=Assigned`，`output` 为空，`progress_log` 为空。
  - 既有正式复核任务 `JJC-20260501-001`（backendTaskId: `2324820b-2d2b-4e98-91e3-9bc4bf864595`）此前也已出现“停在 `Assigned`、未见新的 `progress_log` / `output` 回写”的同类现象。
- 这说明当前 edict 主链已验证“状态可以推进到 `Assigned` / `Done` 等节点”，但**“正式任务本体的结果沉淀字段自动收口”尚未跑实**。
- 进一步对 backend 代码口径复核后，现象与实现也基本一致：
  - `transition_state()` 主要回写 `state`、`flow_log`、`meta.gate_checks`、`meta.memory_extracted`；
  - `review_action()` 主要处理状态流转与门禁确认；
  - `progress_log` 只有显式调用 `/progress` 才会写；
  - 当前链路**没有天然保证**把“最终复核结论 / 结果摘要 / 执行说明”自动补进任务 `output` 或 `progress_log`。

### 建议修正
- 统一把这个问题定性为：**当前缺的不是状态机流转能力，而是正式任务现场的“结果回写收口”能力。**
- 后续由玄成跟进时，至少要分清两层：
  1. 这是**设计上尚未实现**（即本来就没有自动回写 `output/progress_log` 的链路）；
  2. 还是**原本应由 worker / review / dispatch 链回写，但现场漏写或没触发**。
- 最小收口要求应明确为：
  - 正式复核任务从 `Assigned` 往下推进时，必须至少留下一条可见执行痕迹；
  - 任务完结或复核完成时，必须把“结论摘要 / 关键发现 / 是否已收口”写回 `output` 或 `progress_log`；
  - 禁止继续出现“聊天里说已复核 / 已完成，但任务本体字段仍是空白”的情况。
- 若要最小风险修法，优先复核以下两个落点，不要泛泛而谈：
  - backend `review_action / transition_state` 是否应在关键状态批准时补摘要；
  - dispatch / worker 链是否应在执行完成时回填任务 `progress_log` / `output`。

### 影响口径
- 需要禁止的旧说法：
  - “任务到 Assigned 就算已经在执行”
  - “状态推进完了，正式结果就等价于已经留痕”
  - “看板上有状态变化，就可以视为正式复核已写回”
- 统一替换成的新说法：
  - “状态机已推进，不等于正式结果已回写”
  - “正式任务是否真的执行，要看 `progress_log` / `output` / 最终摘要是否落到任务本体”
  - “Assigned 只能说明已派发，不能说明执行链和结果沉淀已收口”

### Hermes玄成 处理结果
- 待玄成跟进。
- 当前建议玄成直接沿本条继续复核：先判定“设计缺口 vs 现场漏写”，再决定最小修法落在 backend 还是 dispatch/worker。

### 已回写文件
- `docs/review-correction-notes.md`
