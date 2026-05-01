# review-correction-notes

更新时间：2026-05-01 13:10（北京时间）

## [2026-04-29 06:05] taizi direct DM 监控口径与北京时间对齐回正
- 提出人：阿爪
- 状态：open
- 复核对象：taizi 当前用户直连 DM 主链 / `docs/current-progress-board.md` / 监控任务 `watch-taizi-direct-close-loop`

### 发现的问题
- 旧监控口径长时间只盯 `/tmp/openclaw/openclaw-2026-04-28.log`，容易把前一日日志里的 UTC `19:xx` 事件误读成“今天 06 点多的最新进展”，时间感明显错位。
- 另一头又容易把“旧窗口后续确实补出过多轮 completion”的历史补证，误说成“今天 06 点这边仍在持续有新 completion”，这同样会带偏值守判断。
- 当前北京时间已到 2026-04-29 06:05，但 `/tmp/openclaw/openclaw-2026-04-29.log` 仍只有少量非 direct DM 业务行，还没有新的 `p2p chat entered / received message / dispatching to agent / dispatch complete` 样本；如果不把“当日日志安静窗口”和“前一日日志历史补证”拆开，后续很容易误报收口或误报回退。

### 建议修正
- 监控与文档统一改为：**先按北京时间查当日日志，再决定是否回看前一日日志补证。**
- 当 `2026-04-29.log` 还没有 taizi direct DM 业务样本时，明确写“当前日日志仍是安静窗口”，不要再拿 `2026-04-28.log` 里的 UTC `19:xx` 直接冒充“今天 06:xx 新进展”。
- 对 direct DM 当前状态的口径统一为：**主链已从 blocker 降级到“基本收口 / 转监控”，但监控不能撤；只要 29 号日志出现新 ingress 而没有 completion，就立即打回未收口 / blocker。**

### 影响口径
- 需要改掉“现在都 6 点了，19:xx 还是最新窗口”的歧义表述。
- 需要把“历史补闭环证据”和“当日日志当前窗口”拆开写，避免混成同一层最新事实。

### Hermes玄成 处理结果
- 已把 `docs/current-progress-board.md` 更新时间刷新到 `2026-04-29 06:05`，并补入“北京时间对齐后的 taizi direct DM 监控结论”专节。
- 已将监控任务 `watch-taizi-direct-close-loop` 的 prompt 改为优先检查 `/tmp/openclaw/openclaw-2026-04-29.log`，只有当日日志业务样本不足时才回看 `/tmp/openclaw/openclaw-2026-04-28.log`。
- 已明确当前口径：旧日志补证显示 direct DM 后续已重新出现多轮 `dispatch complete`，可降级为“基本收口 / 转监控”；但 29 号当日日志 06 点前后仍是安静窗口，暂不算新的 6 点业务闭环样本。

### 已回写文件
- `docs/current-progress-board.md`
- `docs/review-correction-notes.md`

## [2026-04-28 15:18] backend 过渡态口径回正
- 提出人：阿爪
- 状态：open
- 复核对象：backend host-native 主线 / `docs/current-progress-board.md` / `docs/closeout.md` / `docs/governance-upgrade-map.md`

### 发现的问题
- 旧写法容易把 backend 现状继续写成“还没切进生产默认值”或“仍是半接线保守态”，和现场不符。
- 另一头又容易把现状直接拔高成“backend cutover 已完成”，把过渡态和最终验收混成一件事。
- 文档里对 `dual`、`backend export`、`probe 样本`、`最终验收` 的边界没压够清楚，后续接手人容易继续误报。

### 建议修正
- 统一把当前阶段改写为：**已进入生产 dual/export 过渡态，仍待前台写链 smoke、三面一致性持续核对、回滚演练与最终验收。**
- 明确拆开四层含义：能力闭环、默认值切换、自然样本厚度、最终验收完成；禁止再拿其中任一层替代全部完成态。
- 后续所有进度同步优先引用 `docs/current-progress-board.md` 的现行口径，不再沿用旧轮“未切入”或“已完成”两种极端表述。

### 影响口径
- 需要改掉“backend 还没切进去”“仍是 JSON 主路未变”的说法。
- 需要避免“backend 已完成切换”“主链已彻底收口”这类过满状态词。

### Hermes玄成 处理结果
- 待处理

### 已回写文件
- `docs/current-progress-board.md`
- `docs/review-correction-notes.md`

## [2026-04-28 15:18] 模型配置真实源口径回正
- 提出人：阿爪
- 状态：open
- 复核对象：模型配置链路 / `docs/current-progress-board.md`

### 发现的问题
- 旧口径残留把当前模型配置继续写成依赖 `config.yaml`，容易把后续检查、改动入口和故障判断带偏。
- 如果接手人沿旧口径操作，会直接查错文件、改错地方，导致“看起来改了其实没生效”。

### 建议修正
- 统一明确当前真实链路为：`/root/.openclaw/openclaw.json -> scripts/apply_model_changes.py -> scripts/sync_agent_config.py -> data/agent_config.json -> dashboard 前端消费`。
- 后续凡是出现“沿用当前 config.yaml”表述，直接视为口径错误并回正。
- 所有相关文档只保留当前真实配置源，不再混写历史配置形态。

### 影响口径
- 需要改掉“当前模型配置在 config.yaml”这类说法。
- 状态词应从“待确认配置源”改为“配置源已确认，待继续盯执行稳定性”。

### Hermes玄成 处理结果
- 待处理

### 已回写文件
- `docs/current-progress-board.md`
- `docs/review-correction-notes.md`

## [2026-04-28 15:18] 旧阻塞与新阻塞边界回正
- 提出人：阿爪
- 状态：open
- 复核对象：OpenClaw / taizi / windhub 运行阻塞主线 / `docs/current-progress-board.md`

### 发现的问题
- 旧问题 `custom-ai-dcvx-cn/gpt-5.4` 鉴权缺口、`faker/gpt-5.4` 脏错误已基本止血，但文档和口头同步仍容易继续围着旧阻塞打转。
- 新问题也被说得过于粗糙，容易简化成“只是 windhub 慢/超时”，没把 `taizi` 主会话 `.jsonl.lock` 锁竞争带出来。
- 如果不把“旧阻塞已止血”和“新阻塞正在发作”拆开，排障优先级会继续跑偏。

### 建议修正
- 统一写法：旧阻塞大体止血，当前主阻塞已转为 **windhub 执行链异常 + taizi 主会话文件锁竞争 + lane wait 放大**。
- 任何后续汇报都要同时区分：消息入口、执行链、会话写入链三层，不再把问题粗暴压成单点超时。
- 新一轮排查优先盯 `400/timeout/524`、`lane wait exceeded`、`.jsonl.lock` 竞争，而不是回头重复怀疑 faker/custom。

### 影响口径
- 需要改掉“当前主要还是 custom/faker 问题”的说法。
- 需要把“只是 windhub 慢”改成“windhub 不稳叠加 taizi 会话锁竞争”。

### Hermes玄成 处理结果
- 待处理

### 已回写文件
- `docs/current-progress-board.md`
- `docs/review-correction-notes.md`

## [2026-04-28 15:18] taizi DM 修复状态口径回正
- 提出人：阿爪
- 状态：open
- 复核对象：taizi 当前用户直连 DM 主链 / `docs/current-progress-board.md`

### 发现的问题
- 旧表述现在又落后现场了：15:10 之后这条直连 DM 会话再次复发，已不能继续按“已恢复、仅监测”处理。
- 问题也不只是“没有新 completion”这么简单：当前 direct session `agent:taizi:feishu:direct:ou_ed2187f2ad27e0b7876913371e72c06a` 仍处于 `status=running`，`contextTokens=131072` 再次落后于 live `windhub/gpt-5.4` 的 `contextWindow=200000`，对应 `.jsonl.lock` 由当前 live gateway PID 1970076 持有未释放。
- 另一个风险是把这条链说成“彻底死透”。实际它在 15:40 又成功把 `review-correction-notes.md` 写入磁盘，说明更像是长执行 / 间歇放行 / 中途踩参数坑，而不是完全无执行。
- 到 15:40:55，最新 `session file locked` 热点又转移到 `agent:menxia:main`，说明下游六部执行链也在继续 self-lock，问题已不只卡在 taizi direct session。

### 建议修正
- 统一改写为：**当前用户直连 DM 链路已从“曾恢复”回退成“长执行 / 间歇放行 / 无新 dispatch complete”，当前 blocker 为 live direct session 自锁 / stale context 元数据复发 + 执行超时。**
- 后续凡是写“已恢复”，都必须同时满足四段证据再次前推：`p2p chat entered`、`received message`、`dispatching to agent`、`dispatch complete`。只要最后一段不动，就不能继续沿用恢复态口径。
- 对这轮新现场，除 taizi direct session 外，还要同步盯 `agent:menxia:main` 的 `.jsonl.lock`、`lane wait exceeded` 和 timeout/failover，不要再把问题压回单一会话。
- 再继续处理时，优先回看旧/新 session 旋转记录、gateway 重启时间点、15:31 的 `path alias` 参数失败、15:34 的 timeout/failover、以及 15:40 的 `menxia:main` 新锁样本，不要误判成 edict 主线功能缺口。

### 影响口径
- 需要改掉“taizi 已恢复、只待观察”的说法。
- 状态词应从“恢复后监测态”收紧为“复发阻塞中 / 长执行未闭环 / 下游执行链继续 self-lock”。

### Hermes玄成 处理结果
- 待处理

### 已回写文件
- `docs/current-progress-board.md`
- `docs/review-correction-notes.md`

## [2026-04-28 15:18] 测试/Probe 与真实交付边界回正
- 提出人：阿爪
- 状态：open
- 复核对象：治理能力验证主线 / `docs/current-progress-board.md` / `docs/closeout.md`

### 发现的问题
- 文档里虽然已有提醒，但当前仍存在把测试通过、可逆 probe、服务健康直接上提为“真实交付完成”的风险。
- 这会导致治理样本厚度、真实默认值切换、生产长期稳定性三个维度被跳过。

### 建议修正
- 所有文档统一坚持：测试、probe、服务健康只能证明链路/能力存在，不能直接替代真实交付结果。
- 对每条主线都单列“能力闭环证据”和“生产验收证据”，避免继续混写。
- 对自然治理样本继续单列跟踪，不再用一次 probe 成功去冒充“线上已充分自然验证”。

### 影响口径
- 需要改掉“测试通过=任务结果完成”的潜台词。
- 状态词要从“已完成”收紧为“能力已验证 / 生产验收待补齐”。

### Hermes玄成 处理结果
- 待处理

### 已回写文件
- `docs/current-progress-board.md`
- `docs/review-correction-notes.md`

## [2026-05-01 13:07] current-progress-board 二次复核：backend create / taizi直聊 / probe边界口径继续压实
- 提出人：纪火焰
- 状态：open
- 复核对象：`docs/current-progress-board.md` / `docs/review-correction-notes.md` / edict 主线复核任务 `JJC-20260501-001`

### 发现的问题
- 当前主板虽然已经把很多旧误报纠正掉，但仍存在三类高频风险：
  1. **backend create 一致性** 容易被从“已明显前推一轮”误写成“整体收口”；
  2. **taizi / 飞书直聊阻塞** 容易被重新说回旧的 `custom/faker` 问题，或反过来误写成“已恢复”；
  3. **测试 / probe / 能力验证** 与 **真实交付 / 最终验收** 的边界，仍容易在阶段汇报里被说混。
- 现有主板正文已经给出更准确的现场事实：
  - `backend create` 已去掉 `PENDING legacy_id` 旧写法，并补了候选号与 fallback 重算逻辑；但仍缺更厚的自然样本与更复杂并发样本，**不能上提为 create 主链最终验收完成**。
  - taizi 当前主阻塞已收敛为 **windhub 间歇性失效/401/524/timeout + direct session 长跑/持锁/无稳定 dispatch complete + lane wait/self-lock 噪声**；**不应再回退成“主要还是 custom/faker”，也不应再写成“已恢复只需观察”**。
  - 主板已多次强调“测试通过 / probe 成功 / 服务健康”只能证明链路存在，**不能替代真实交付、自然样本厚度或最终验收**；但这条边界仍需继续在 review 文档里压实。

### 建议修正
- 统一把 `backend create` 当前状态写成：
  - **legacy_id / 当日流水号 / fallback 口径已明显收紧**；
  - **create 一致性已前推一轮，但不等于 backend create 主链整体收口**；
  - 后续仍需补更厚自然样本与并发场景验证。
- 统一把 taizi / 飞书直聊当前状态写成：
  - **主链可闭环，但运行态仍不稳定**；
  - **当前主 blocker 是 windhub 间歇性异常叠加 direct session 长跑/持锁/无稳定 dispatch complete**；
  - `menxia:main` / lane wait / self-lock 继续作为并行噪声与风险项盯防；
  - 禁止再沿用“主要还是 custom/faker”或“DM 已恢复、仅监测”这两种过时口径。
- 统一把验收边界写成：
  - **能力闭环 ≠ 生产验收完成**；
  - **probe 样本 ≠ 自然样本充分**；
  - **代码已改 / py_compile 已过 ≠ 全链运行态收口**。
- 本轮复核与后续执行，统一按三省六部模板推进：
  - `task-intake-clarification-template.md`
  - `plan-review-template.md`
  - `implementation-plan-template.md`
  - `acceptance-checklist-template.md`
  不再只靠口头复核。

### 影响口径
- 需要删掉或继续禁止的旧说法：
  - “backend create 已整体收口”
  - “当前主要还是 custom/faker 问题”
  - “taizi DM 已恢复、只待观察”
  - “测试/probe 过了就算真实交付完成”
- 需要统一替换成的新说法：
  - “backend create 一致性已前推一轮，但未最终验收”
  - “当前主阻塞是 windhub 间歇性异常 + direct session 长跑/持锁 + lane wait/self-lock 噪声”
  - “能力已验证 / 生产验收待补齐 / 自然样本继续补厚”

### Hermes玄成 处理结果
- 已按用户要求把“继续复核 current-progress-board 并回写 review-correction-notes”正式派入 edict 主链：
  - 任务号：`JJC-20260501-001`
  - backendTaskId：`2324820b-2d2b-4e98-91e3-9bc4bf864595`
  - 当前状态：`Taizi`
- 已在本文件补入本轮纠偏条目，作为后续中书 / 门下 / 尚书推进时的统一口径约束。
- 后续若 edict 主线继续复核并产出更精确结论，应优先在本条下继续回写，而不是重新散落到聊天里。

### 已回写文件
- `docs/review-correction-notes.md`
- `docs/current-progress-board.md`（本轮要求继续复核，后续若主板正文需同步收紧口径，再按任务结果回写）
