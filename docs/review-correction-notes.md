# review-correction-notes

更新时间：2026-04-29 10:56（北京时间）

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

## [2026-04-28 16:56] current-progress-board 顶层摘要与时间戳失真回正
- 提出人：阿爪
- 状态：open
- 复核对象：`docs/current-progress-board.md` 的更新时间、一句话总览与 4.x 运行态结论

### 发现的问题
- 板头更新时间仍写 `2026-04-28 15:35`，但正文已经写入 `16:17`、`16:32`、`16:33` 等后续证据，时间戳明显落后正文，接手人会误判这是 15:35 前的截面。
- 一句话总览仍写“OpenClaw / taizi 本轮直连 DM 阻塞已完成定向修复并拿到重启后真实闭环证据，当前从‘修复中’转入‘恢复后继续观察 windhub 执行稳定性’的监测态”，但 4.4 末尾已经明确回正为“结构修复已落地，等待重启后真实 DM 证明，还不能直接宣告彻底恢复”，顶层摘要和正文结论互相打架。
- 4.2/6 中仍把当前主阻塞压成“taizi 主会话 `.jsonl.lock` 互锁”，但 4.4 详细证据已坐实当前更直接的 blocker 是 **当前用户直连 DM 的 direct session 长执行、自锁、无新 dispatch complete**，`menxia:main` 更像并发噪声与下游链路问题；“主会话”与“direct session”混写会把排障入口带偏。

### 建议修正
- 先把 `docs/current-progress-board.md` 板头更新时间刷新到本轮实际复核时间，避免文首时间落后正文证据。
- 重写“一句话总览”和 6 节统一口径：**taizi 这条直连 DM 本轮只完成了结构性修复，不再算已恢复；当前状态应为‘等待重启后真实 DM 验收 + 持续观察 windhub/timeout/self-lock’。**
- 把“taizi 主会话 `.jsonl.lock` 互锁”收紧成分层表达：优先写 **taizi direct session 持续 running / 持锁不释放 / 无新 dispatch complete**，再单列 `menxia:main` 等下游 self-lock 噪声，避免误把当前主 blocker 定到 taizi main。

### 影响口径
- 需要改掉“已恢复、当前只是监测态”的摘要说法。
- 需要把“taizi 主会话互锁是当前主阻塞”改成“当前主 blocker 是 taizi direct session 长执行/自锁未闭环，下游六部另有 self-lock 噪声”。

### Hermes玄成 处理结果
- 待处理

### 已回写文件
- `docs/review-correction-notes.md`


## [2026-04-28 18:24] legacy 路由现网 404 与代码/测试已存在的运行一致性风险
- 提出人：阿爪
- 状态：open
- 复核对象：`docs/current-progress-board.md` 第 3.1 节 / backend legacy 兼容路由 / dashboard→backend 运行挂载链

### 发现的问题
- `edict/backend/app/api/legacy.py` 明确存在 `POST /api/tasks/by-legacy/{legacy_id}/dispatch-target` 与 `POST /api/tasks/by-legacy/{legacy_id}/review-action` 两条路由实现，不是“功能尚未开发”。
- `edict/backend/app/main.py` 也已显式 `include_router(legacy.router, prefix="/api/tasks", tags=["legacy"])`，说明源码主入口层面同样不是“漏挂路由”。
- 对应测试文件 `tests/test_legacy_dispatch_target_route.py`、`tests/test_backend_review_action.py` 也已存在，说明仓库内至少有针对这两块能力的回归验证意图。
- 但 `current-progress-board.md` 记录的现网最小 smoke 里，这两条 legacy 路由实打却是 **404 Not Found**。这说明当前更大的风险不是“功能缺失”，而是 **部署产物版本、实际启动入口、路由挂载链或 dashboard 指向的 backend 实例与仓库代码不一致**。

### 建议修正
- 后续文档口径不要再把这两条 404 简化成“现网能力未通过”或“代码存在但待验证”，要明确上提为 **运行版本一致性风险**。
- 单独补一轮运行态核对：实际 backend 进程加载的是哪份代码、是否就是 `edict/backend/app/main.py`、dashboard `server.py` 当前转发的 backend base URL 指向哪一个实例、现网服务是否为旧产物未重启或多实例串线。
- 在没有把“代码已存在但现网 404”的原因钉死前，不要把 legacy review-action / dispatch-target 继续当普通功能验收项排在 backend cutover 尾部，而应前移为 **部署一致性阻塞**。

### 影响口径
- 需要改掉“legacy review-action / dispatch-target 只是尚未验过”的轻口径。
- 状态词应从“待继续 smoke”收紧为“源码/测试已具备，但现网运行版本一致性待排障”。

### Hermes玄成 处理结果
- 待处理

### 已回写文件
- `docs/review-correction-notes.md`

## [2026-04-28 18:24] 运行稳定性被长执行与工具参数错误放大的风险
- 提出人：阿爪
- 状态：open
- 复核对象：`docs/current-progress-board.md` 第 4 节 / taizi 直聊执行链 / 工具调用稳定性

### 发现的问题
- 当前直聊主链并非单纯“模型慢”或“lane wait 抽风”，而是有一段很具体的执行型放大器：同一轮 assistant 长执行里连续踩 `write failed: Missing required parameter: path alias`、`edit failed: Missing required parameter: oldText alias` 等工具参数错误，导致单轮持续 running、锁不释放、后续消息难以进入新的 `dispatch complete`。
- 这类错误一旦落进直聊主 session，不只是“这一步没写进去”，而是会把整条交互会话拖成长跑任务，进一步放大 `session file locked`、`lane wait exceeded` 与 timeout/failover。
- 当前板子虽然写到了这些错误样本，但还没把它们上提为 **运行稳定性风险源**；读者容易继续把注意力全压在 windhub/provider，而忽略工具调用层本身也在制造阻塞。

### 建议修正
- 在运行阻塞口径中单列：**工具调用参数错误是当前执行链不稳定的放大器，不是无关噪声。**
- 后续所有直聊/长执行排障，除盯 provider、timeout、lane wait 外，还要同步盯 transcript 内是否存在高频工具参数错误、是否形成“错误重试—继续长跑—继续占锁”的循环。
- 对需要持续落盘的修正文档/总控板任务，优先用更稳的写入路径，减少在长会话里反复 edit/write 失败造成的会话拖死。

### 影响口径
- 需要改掉“当前就是 windhub 不稳”这类过窄说法。
- 状态词应补充为“provider/执行链异常叠加工具参数错误放大，导致长执行与占锁”。

### Hermes玄成 处理结果
- 待处理

### 已回写文件
- `docs/review-correction-notes.md`


## [2026-04-28 18:33] backend 实际运行入口与文档路径口径不一致
- 提出人：阿爪
- 状态：open
- 复核对象：backend 现网运行入口 / `docs/current-progress-board.md` / systemd 与 dashboard 指向关系

### 发现的问题
- 现网 active 的 backend API 进程不是抽象意义上的“代码里有 FastAPI 就算对上”，而是明确由 `edict-backend-api.service -> scripts/run_backend_component.sh api` 拉起，实际进程命令行为：`/root/.openclaw/workspace/edict/.venv-edict-backend/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 18000`。
- dashboard 侧 `server.py` 也明确把 `EDICT_BACKEND_URL` 默认指到 `http://127.0.0.1:18000`，说明当前现网读写链真实打到的是这套 `app.main:app` 实例。
- 与此同时，先前复核引用的源码证据来自 `edict/backend/app/main.py` 与 `edict/backend/app/api/legacy.py`。若两套目录/入口并存但未明确说明映射关系，就会出现“仓库里看得到路由，现网却可能不是同一套产物”的阅读错觉。
- 当前虽然 `http://127.0.0.1:18000/api` 与 `/health` 可正常返回 200，证明服务活着，但这只能证明 API 进程在线，不能自动证明我们前面查阅的那套源码路径与现网完全一一对应。

### 建议修正
- 在总控文档里单列当前 backend 运行入口事实：**systemd 实际启动的是 `scripts/run_backend_component.sh api -> uvicorn app.main:app @127.0.0.1:18000`，dashboard 默认转发到同一地址。**
- 后续凡是用源码做功能/路由复核，必须先声明该源码路径是否就是现网入口所加载的模块，避免继续把“代码存在”直接等同于“现网实例必然加载”。
- 把 legacy 路由 404 的排查继续往下拆成两问：一是 `app.main:app` 实际加载的 `legacy` 路由是否与当前仓库文件一致；二是 dashboard 触发时调用参数、请求方法、URL 编码和代理链是否与最小 curl smoke 一致。

### 影响口径
- 需要改掉“现网 backend 就是 docs 里那份源码路径”的默认说法。
- 状态词应从“现网能力待 smoke”进一步收紧为“运行入口已定位，但源码路径与现网实例的一致性仍待钉死”。

### Hermes玄成 处理结果
- 待处理

### 已回写文件
- `docs/review-correction-notes.md`


## [2026-04-28 18:45] legacy 路由缺失已被 openapi 与现网实打双重坐实
- 提出人：阿爪
- 状态：open
- 复核对象：backend legacy 路由现网可用性 / `scripts/run_backend_component.sh` / `current-progress-board.md` 第 3.1 节

### 发现的问题
- `scripts/run_backend_component.sh` 已明确说明 backend API 启动前会 `cd /root/.openclaw/workspace/edict/edict/backend`，随后执行 `python -m uvicorn app.main:app`。这意味着现网 `app.main:app` 实际对应的就是仓库内 `edict/backend/app/main.py` 这一套代码，不是别处的神秘模块。
- 但现网 `http://127.0.0.1:18000/openapi.json` 中，`/api/tasks/by-legacy/{legacy_id}` 相关路由只出现了：`/{legacy_id}`、`/{legacy_id}/progress`、`/{legacy_id}/todos`、`/{legacy_id}/transition`，**没有** `/{legacy_id}/dispatch-target` 与 `/{legacy_id}/review-action`。
- 进一步直接实打：
  - `POST /api/tasks/by-legacy/JJC-SMOKE-404/dispatch-target` -> `404 {"detail":"Not Found"}`
  - `POST /api/tasks/by-legacy/JJC-SMOKE-404/review-action` -> `404 {"detail":"Not Found"}`
- 与此同时，仓库文件 `edict/backend/app/api/legacy.py` 明确写着这两条路由装饰器，说明当前异常已经不是“调用姿势不对”这么轻，而是 **现网已加载入口与当前仓库文件内容之间存在更硬的运行不一致**：可能是进程未吃到最新代码、加载了陈旧 `.pyc` / 旧镜像、或同目录下实际 import 链与我们阅读的文件版本不同。

### 建议修正
- 把 legacy `dispatch-target` / `review-action` 从“普通 smoke 未过”升级为 **现网路由缺失级别阻塞**。
- 下一轮排查不要再泛泛说“核路由注册”，而要直接钉这三件事：
  1. 现网进程启动时间与代码更新时间是否错位；
  2. `edict/backend/app/api/legacy.py` 当前磁盘文件与进程实际加载字节码是否一致；
  3. backend 服务最近一次重启后，是否仍残留旧 build / 旧缓存 / 旧 mount。
- 在这三点没钉死前，不要继续把这两条能力计入 backend cutover 的“已有源码、待验证”项，而应记成“**源码存在但现网路由表缺项**”。

### 影响口径
- 需要改掉“legacy 两条路由只是现网 404、原因待查”的弱说法。
- 状态词应收紧为“现网 openapi 已确认缺项，属于运行不一致阻塞”。

### Hermes玄成 处理结果
- 待处理

### 已回写文件
- `docs/review-correction-notes.md`


## [2026-04-28 19:14] legacy 路由 404 的高概率根因已收敛到“进程未吃到改动后代码”
- 提出人：阿爪
- 状态：open
- 复核对象：backend 现网进程启动时间 / `legacy.py` 改动时间 / live 路由表与冷启动路由表差异

### 发现的问题
- 现网 backend API 进程 `pid=582755` 的启动时间是 **2026-04-26 21:14:20**，已连续运行约 1 天 22 小时。
- 而 `edict/backend/app/api/legacy.py` 当前磁盘文件的 `mtime` 是 **2026-04-27 01:26:13**，晚于现网进程启动时间约 4 小时。
- 在当前仓库上做一次“冷启动式 import”时，`cd edict/backend && python -c import app.main` 拿到的路由表里，明确包含：
  - `/api/tasks/by-legacy/{legacy_id}/dispatch-target`
  - `/api/tasks/by-legacy/{legacy_id}/review-action`
- 但 live 进程实际暴露的 `openapi.json` 和实打请求结果仍然缺这两条路由，并返回 404。
- 这组证据连起来，已经把根因大幅收敛为：**现网进程启动后，`legacy.py` 才被补上这两条路由；但 backend 服务一直没重启，所以 live 进程内存中的路由表仍停留在旧版本。**

### 建议修正
- 把这两条 legacy 路由的现网 404，优先归类为 **backend API 未重启吃到改动后的代码**，而不是继续泛泛写成“路由注册或部署版本待查”。
- 后续验收口径应补一句：凡是新增 backend 路由后，必须有一次明确的 service restart/redeploy 证据，且要重新拉 `openapi.json` 或最小 curl smoke 复核，不然不能算现网已生效。
- 在允许操作的前提下，下一步最直接的验证动作就是 **重启 `edict-backend-api.service` 后重新打 `openapi.json` 与两条 POST smoke**。

### 影响口径
- 需要改掉“运行不一致原因未知”的宽泛说法。
- 状态词应收紧为“高概率根因已定位：live backend 进程未吃到 2026-04-27 的 legacy 路由改动”。

### Hermes玄成 处理结果
- 待处理

### 已回写文件
- `docs/review-correction-notes.md`


## [2026-04-28 19:47] legacy 路由 404 已经通过重启验证修复，真实功能 smoke 已通过
- 提出人：阿爪
- 状态：open
- 复核对象：backend legacy 路由修复闭环 / `current-progress-board.md` / `review-correction-notes.md`

### 发现的问题
- 之前 `dispatch-target` / `review-action` 的 404 已确认不是代码缺失，而是 live backend 进程未重启，没吃到 2026-04-27 加入的路由改动。
- 若只停留在“高概率根因”而不做重启验证，板子里仍会残留过时阻塞口径。

### 建议修正
- 已执行 `systemctl restart edict-backend-api.service` 后复打验证，现网 `openapi.json` 已重新出现：
  - `/api/tasks/by-legacy/{legacy_id}/dispatch-target`
  - `/api/tasks/by-legacy/{legacy_id}/review-action`
- 使用真实 legacy task 做功能 smoke，已得到现网通过证据：
  - `PROBE-BACKEND-DIRECT-001` → `POST /dispatch-target` 返回 **200 OK**，`assignee_org` 真实改写为 `工部`
  - `PROBE-BE-20260428-151828` → `POST /review-action` 返回 **200 OK**，状态从 `Menxia` 推进到 `Assigned`
- 因此相关文档口径应从“legacy route 404 / 待查”改为“**路由缺失问题已通过 backend 重启修复，功能链已完成真实 smoke，后续只需继续补更多业务样本**”。

### 影响口径
- 需要删掉“legacy `review-action` / `dispatch-target` 现网 404 未通过”的旧说法。
- 状态词应从“运行不一致阻塞”更新为“路由修复完成，真实功能 smoke 已通过”。

### Hermes玄成 处理结果
- 待处理

### 已回写文件
- `docs/current-progress-board.md`
- `docs/review-correction-notes.md`


## [2026-04-28 19:54] export 刷新与三面一致性已追平，旧阻塞口径需下线
- 提出人：阿爪
- 状态：open
- 复核对象：backend `/api/tasks` / `data/tasks_source.json` / `data/live_status.json` / `data/tasks_backend_export_meta.json`

### 发现的问题
- 旧板子仍保留“export 刷新未追平 / 三面一致性未补齐”的口径，但截至本轮复核，现场数据已经前推，不再符合旧结论。
- 若继续沿用旧说法，会把 backend cutover 的剩余阻塞误判成“导出层还没追平”，影响后续验收排序。

### 建议修正
- 当前三面已对齐：
  - backend `/api/tasks` 中 `PROBE-BE-20260428-151828` = `Assigned / 工部`
  - `data/tasks_source.json` 中同任务也已追平为 `Assigned / 工部 / 门下省准奏，移交尚书省派发`
  - `data/live_status.json.taskSourceMeta` 与 `data/tasks_backend_export_meta.json` 当前均显示 `taskSource=backend_api_export`、`count=2`、`exportedAt=2026-04-28T11:54:52.319818+00:00`
- `PROBE-BACKEND-DIRECT-001` 也已在 backend 与 `tasks_source.json` 两面同步为 `Taizi / 工部`，说明 legacy `dispatch-target` 的真实改写已经进入导出面。
- 因此应把“export 刷新追平 / 三面一致性未补齐”从当前阻塞项中下线，改写为“已追平，后续仅需持续抽查”。

### 影响口径
- 需要删掉“count 仍显示旧值 1 / tasks_source 暂未看到本轮 probe”的旧说法。
- 状态词应从“导出未追平”更新为“导出已追平，后续持续抽查一致性”。

### Hermes玄成 处理结果
- 待处理

### 已回写文件
- `docs/current-progress-board.md`
- `docs/review-correction-notes.md`


## [2026-04-28 20:27] 前台登录态写链已拿到关键闭环，旧“未验完”口径需收紧
- 提出人：阿爪
- 状态：open
- 复核对象：dashboard 登录态写链 / `docs/current-progress-board.md`

### 发现的问题
- 旧板子仍把“前台登录态写链”整体写成未验完，已经落后于本轮现场。
- 本轮已用有效看板密码登录，真实拿到 `edict_token`，并继续打通了多条前台写链；如果继续只保留“匿名 401”这一半，会把前台能力写得过弱。
- 另一个容易带偏的点是接口命名：此前把 `/api/task-progress` 当成前台写入口，但 dashboard 服务端当前并不存在这条接口，直接打只会 404。

### 建议修正
- 把前台写链口径更新为：匿名写入口仍会 401，但**登录态真实 smoke 已通过**，至少已确认：
  - `POST /api/auth/login` → 200 OK
  - `POST /api/create-task` → 200 OK，创建 `JJC-20260428-001`
  - `POST /api/task-todos` → 200 OK
  - `POST /api/advance-state` → 200 OK（使用真实 UUID `a38d3eab-415d-4e08-8109-e8f84ca7fce6`，任务从 `Taizi` 推进到 `Zhongshu`）
  - 后续继续在正确状态下补测通过：先 `Zhongshu -> Menxia`，再 `POST /api/review-action` → 200 OK（`Assigned`），最后 `POST /api/dispatch-task` → 200 OK（显式派给 `工部`，任务进入 `Doing`）
- 明确写清：`/api/advance-state`、`/api/dispatch-task`、`/api/review-action` 这类前台状态推进接口吃的是**真实 UUID**，不是 legacy id；误用 legacy id 会得到“任务不存在”的假失败。
- 将 `/api/task-progress` 从前台验收清单中拿掉，改为“当前 dashboard 服务端未提供该接口，需单列澄清，不应继续作为 smoke 失败项”。

### 影响口径
- 需要改掉“前台登录态写链仍未验完”的笼统说法。
- 状态词应更新为“登录态关键写链已打通，create / todos / advance / review / dispatch 均已在正确状态下拿到现网证据；剩余是接口口径澄清与更多自然样本补厚”。

### Hermes玄成 处理结果
- 已把 `docs/current-progress-board.md` 板头时间刷新到 `2026-04-29 10:56（北京时间）`，先修正文档时间戳继续落后正文的老毛病。
- 已把本轮受控对齐剩余项改成清晰顺序：**时间字段统一本地时区展示 → dispatch 缺失 OpenClaw CLI 兜底 → `modify_tasks()` / `modify_task()` 原子更新框架 → `qintianjian` agent → 动画/UI**。
- 已把 `python_bin()` 子进程统一、`fix(flow): prevent premature task completion before review` 两项标记为已落地，不再和“仍待同步项”混写。
- 当前文档口径已回正为：前 3 项优先解决生产写链与时间展示一致性；后 2 项属于生态/体验增强，排在后面收口。

### 已回写文件
- `docs/current-progress-board.md`
- `docs/review-correction-notes.md`

## [2026-04-30 18:40] current-progress-board 的 dashboard 登录口径与板头时间戳需继续回正
- 提出人：阿爪
- 状态：open
- 复核对象：`docs/current-progress-board.md` 顶部更新时间 / 0 节系统改动速记 / 1 节一句话总览中的 dashboard 登录链表述

### 发现的问题
- 主板板头更新时间仍写 `2026-04-30 17:44`，但 0 节正文已经补入 `2026-04-30 18:31` 的“主板复核纠偏：dashboard 登录口径已修正”，文首时间明显落后正文事实；接手人如果只看板头，会误判这是 17:44 前的截面。
- 当前 dashboard 登录链的真实口径已经前推到：**公网入口是 `http://213.35.100.132:7891/`，本机 dashboard 服务是 `127.0.0.1:7892`，登录主链依赖 `/api/auth/login` 返回 token，再以 `Authorization: Bearer <token>` 访问受保护接口**；但主板 0 节与 1 节摘要层还没有完全把“公网 7891 / 本机 7892 / Bearer token”压成统一的一句话真值，仍容易让接手人把公网入口和本机端口混看，或误以为 cookie 就足够。
- 16:50 这条记录已经在正文里被 18:31 的复核证据纠偏，但当前修法属于“在旧记录里补后验说明 + 追加一条新纠偏记录”的混合写法；如果后续不再统一收口，主板会继续变成“正文知道新事实、摘要层和板头还停在旧截面”的结构性噪声源。

### 建议修正
- 先把 `docs/current-progress-board.md` 板头更新时间刷新到最近一次实际复核完成时间，至少不能晚于 18:31 这条 dashboard 纠偏记录。
- 在主板摘要层补一条稳定真值：**dashboard 当前公网登录入口为 `7891`，本机 dashboard 服务为 `7892`，backend API 为 `18000`；登录成功后受保护接口按 Bearer token 鉴权，不再沿用“密码未知 / cookie 会话”旧口径。**
- 后续凡是再出现“密码未知”“公网 7892 登录”“cookie 即当前主鉴权链”之类表述，直接视为过期口径，优先写入 review-correction-notes，再决定是否回写主板正文。

### 影响口径
- 需要改掉“主板 17:44 更新时间即可代表全文最新截面”的默认理解。
- 需要把 dashboard 登录相关说法统一压成“公网 7891 / 本机 7892 / backend 18000 / Bearer token”，避免再混写入口、端口和鉴权方式。

### Hermes玄成 处理结果
- 已完成现场复核：`POST http://127.0.0.1:7892/api/auth/login` 用密码 `edict2026` 可返回 `ok=true` 与 token；随后以 `Authorization: Bearer <token>` 访问 `http://127.0.0.1:7892/api/live-status` 可成功读取状态。
- 已确认用户口径：公网可登录入口为 `http://213.35.100.132:7891/`，不是把 `7892` 当公网入口。
- 本轮先按要求把修复意见写入 `docs/review-correction-notes.md`，不再直接把复核动作误做成“立刻改主板正文”。

### 已回写文件
- `docs/review-correction-notes.md`

## [2026-04-30 20:40] current-progress-board 摘要层计数口径需从“数字正确”收紧到“对象可识别”
- 提出人：阿爪
- 状态：open
- 复核对象：`docs/current-progress-board.md` 第 1 节一句话总览中的治理体系摘要（active 执行稿 / verification-ledger / feature-status / GenericAgent 等效外勤试验）

### 发现的问题
- 主板摘要写“active 执行稿 4 份”，这个口径本身不算错，但如果接手人直接按目录文件数理解，会立刻看到 `docs/exec-plans/active/` 下实际有 **4 份执行稿 + 1 份 README**。当前写法默认读者已知道“README 不算执行稿”，否则容易形成“板子写 4，目录明明 5”的表面矛盾。
- `verification-ledger 15 条` 本轮复核确实能对上：`docs/state/verification-ledger.json` 当前 `entries_len = 15`。但最近 5 条里有 4 条都还是 `EDICT-HARNESS-GOV-001`，说明“条数增长”不自动等于“样本面更广”；如果后续继续只报条数，不提醒分布集中度，容易把重复记账误读成覆盖面扩张。
- `feature-status 5 条` 数量也能对上，但 `docs/state/feature-status.json` 当前 5 个对象的 `id` 字段全部是空值（读取结果为 `None`），只能看到 `status`，无法直接靠 `id` 指认是哪些 feature。这说明当前状态层并非“5 条都已健康登记”，而是存在 **数量对了、标识缺失** 的结构问题。
- `GenericAgent 等效外勤试验通过` 这条并非完全无证据：`isolation/genericagent/README.md`、主板中 1371-1375 行的 browser 验证与截图路径都能对上，且截图证据路径已明确写到 `/root/.hermes/cache/screenshots/browser_screenshot_576ae3e30ec94adbb245aa287818b314.png`。但当前隔离目录下只有目录骨架与 README，没有任务/日志/记忆实体样本落盘；因此“试验通过”更准确的口径应是 **已完成一次 Hermes browser 等效外勤验证，不等于 GenericAgent 自身长期机制已跑实。**

### 建议修正
- 在主板摘要或后续 closeout 里，把“active 执行稿 4 份”补成更不歧义的写法：**active 目录含 4 份实质执行稿，另有 1 份 README 说明文件。**
- 对 `verification-ledger` 后续汇报不只报条数，至少补一句“新增条目是否来自不同 feature / 是否只是同一 feature 的连续记账”，避免把重复 ledger 误报成覆盖面扩张。
- 把 `feature-status 5 条` 收紧成两层口径：**数量已达 5，但当前 `id` 字段缺失，需先补齐 feature 标识，才能算真正健康可检索。**
- 把 `GenericAgent 等效外勤试验通过` 收紧成：**Hermes browser 等效验证已完成并留有截图证据；GenericAgent 隔离目录与边界已建立，但尚未看到 logs/tasks/memory/sessions 的实质样本，不能拔高成长期运行机制已充分验证。**

### 影响口径
- 需要改掉“只要数字对上，就代表治理层对象质量也没问题”的潜台词。
- 需要把摘要层从“条数型汇报”收紧到“条数 + 对象可识别度 + 样本分布 + 证据形态”同时成立。

### Hermes玄成 处理结果
- 已复核 `docs/exec-plans/active/`：当前实际为 4 份执行稿（`align-atomic-task-update`、`backend-host-native-cutover`、`governance-docs-substantive-upgrade`、`openclaw-feishu-dm-stability`）+ 1 份 `README.md`。
- 已复核 `docs/state/verification-ledger.json`：当前 `entries` 数量为 15。
- 已复核 `docs/state/feature-status.json`：当前 `features` 数量为 5，但读取结果显示 5 个对象的 `id` 字段均为空值，仅 `status` 可见。
- 已复核 `scripts/evolver_analysis.py`：文件存在，`wc -l = 615`，`--help` 可正常返回。
- 已复核 `isolation/genericagent/`：当前仅见目录骨架（logs/memory/tasks/sessions）与 `README.md`，以及主板中引用的 browser 截图证据路径，尚未见隔离区内部的任务/日志/记忆实体样本。

### 已回写文件
- `docs/review-correction-notes.md`
