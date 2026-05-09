# edict local overlay / 本地魔改分层

> 目的：把本机 `/root/.openclaw/workspace/edict` 的生产魔改从散装 dirty tree 收束成可解释、可回放、可升级的 overlay 结构。以后跟 `cft0808/edict` 官方版时，不再直接整仓 merge，而是先保护本机生产层，再按 patch 队列受控吸收上游。

## 基线

- 上游只读副本：`/root/.openclaw/workspace/_third_party/cft0808-edict-upstream`
- 当前上游 HEAD：`14a2075`
- 本机生产仓库：`/root/.openclaw/workspace/edict`
- 本机当前 HEAD：`a239c8e`

## 分层

### layer0-upstream-baseline
记录官方基线信息、上游文件清单、逐文件阅读摘要。不得放本机生产私货。

### layer1-content-docs
文档、SOUL、交付稿、主板、closeout、治理说明。影响交付口径，但不直接改变运行链。

### layer2-runtime-overrides
host-native 运行态、systemd、脚本入口、OpenClaw 兼容、环境变量、doctor、guard、自愈脚本。

### layer3-backend-governance
backend API、legacy 兼容、任务状态机、PendingConfirm、outbox、dispatch/orchestrator、Postgres/Redis 相关生产增强。

### layer4-frontend-ui
React/Vite 前端、dashboard dist、审批/急递铺/过滤/登录态等 UI 增强。

### layer5-tests-verification
测试、验证脚本、验证账本、现实状态审计报告。

### upgrade-patches
未来把稳定本地魔改压成最小 patch 队列，按 P0/P1/P2 顺序回放。

## 升级顺序

1. P0 保命层：`dashboard/server.py`、backend 主链、三层数据导出、自愈守护、host-native 启动脚本。
2. P1 运维与可回滚层：doctor、deploy/runtime/migration、current-progress-board、closeout、governance docs。
3. P2 交付沉淀层：正式交付稿、任务分工稿、专题方案、状态账本。
4. 最后才吸收 `cft0808/edict` 新能力。

## 当前 reality sync 摘要（2026-05-08）

- 上游 `cft0808/edict` 共 221 个文件：backend 35、frontend 31、scripts 15、tests 12、docs 48、dashboard 7、agents 15。
- 本机不是简单 fork：`dashboard/server.py` 2947→4317 行，`task_service.py` 299→544 行，`store.ts` 459→538 行，`test_server.py` 41→1996 行。
- 本机运行态：dashboard/backend/deep health 均 ok，dashboard/loop systemd active。
- 当前 loop 环境是 `EDICT_ENABLE_BACKEND_EXPORT=false`，所以 `live_status.taskSource=tasks_source.json`；这不是 backend export 主链已三面一致。
- 当前三面数据不一致：backend 18 条，`tasks_source.json` 16 条，`live_status.taskSourceMeta` 为空对象。
- 验证现状：Python compile 通过；前端 `npm run build` 通过；目标 pytest 组合当前 63 passed / 11 failed，失败集中在旧测试预期与本机生产行为漂移、dual fallback、main-session guard、通知标记等。

## 不允许的升级方式

- 不直接 `git merge upstream/main`。
- 不整块覆盖 `dashboard/server.py` / backend 主链。
- 不把旧 verification-ledger 的历史 PASS 当成当前现网完成。
- 不把 doctor 或 build 通过冒充真实交付收口。
