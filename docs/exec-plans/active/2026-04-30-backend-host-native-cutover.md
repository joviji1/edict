# 执行稿：backend host-native cutover 过渡态验收

**执行编号**: EXEC-20260428-001
**状态**: 进行中
**创建时间**: 2026-04-30 16:45（北京时间）
**负责人**: 玄成（Hermes）

## 1. 目标
把 edict backend host-native 从 JSON 主路成功切入生产 dual/export 过渡态，并通过真实 smoke、前台登录态写链、systemd 回滚演练与三面一致性验证，最终收敛为可长期运行的生产态。

## 2. 当前已完成

### 2.1 基础设施就位
- [x] backend 常驻服务健康：`GET /api/tasks` 已返回真实列表
- [x] 生产 `edict-dashboard.service` 已注入 `EDICT_TASK_WRITE_MODE=dual`
- [x] 生产 `edict-loop.service` 已注入 `EDICT_ENABLE_BACKEND_EXPORT=true`
- [x] `data/tasks_backend_export_meta.json` 已存在
- [x] `live_status.json.taskSource` 已切到 `backend_api_export`
- [x] `data/tasks_source.json` 当前已是 backend export 的兼容投影

### 2.2 smoke 验证
- [x] backend 原生 create：`POST /api/tasks` → **201 Created**，初始态直接为 `Taizi`
- [x] legacy get：`GET /api/tasks/by-legacy/{legacy_id}` → **200 OK**
- [x] legacy todos：`PUT /api/tasks/by-legacy/{legacy_id}/todos` → **200 OK**
- [x] legacy progress：`POST /api/tasks/by-legacy/{legacy_id}/progress` → **200 OK**
- [x] legacy transition：`POST /api/tasks/by-legacy/{legacy_id}/transition` → Taizi → Zhongshu → Menxia 成功
- [x] backend dispatch：`POST /api/tasks/{uuid}/dispatch?agent=gongbu` → **200 OK**
- [x] legacy review-action：重启 backend API 后恢复路由并完成 smoke
- [x] legacy dispatch-target：重启 backend API 后恢复路由并完成 smoke

### 2.3 前台登录态写链
- [x] `POST /api/auth/login` → 获取 `edict_token`
- [x] `POST /api/create-task` → 创建任务 `JJC-20260428-001`
- [x] 完整推进链：Taizi → Zhongshu → Menxia → Assigned → Doing（工部）
- [x] 前台已确认可写入口：`create-task`、`task-todos`、`advance-state`（后两者吃 UUID，非 legacy id）

### 2.4 三面一致性
- [x] `/api/tasks`、`data/tasks_source.json`、`live_status.json.taskSourceMeta` 已追平到 `count=4`
- [x] `tasks_backend_export_meta.json.count=4` 与上述三面对齐
- [x] probe 任务的状态、assignee_org、updatedAt 已能跨三面对应

### 2.5 systemd 回滚演练
- [x] 已完成一轮真实 systemd 级实操：`dual -> json` + 去掉 backend export → 回切
- [x] 备份目录：`/root/.hermes/backups/rollback-drill-20260430-053642/`
- [x] 回切后 doctor 结果：`PASS=31 WARN=1 FAIL=0`
- [x] 回切后所有健康端点恢复 200
- [x] 回切后 `taskSource` 与 export meta 恢复一致

## 3. 仍待补

- [ ] 更多自然业务样本：当前证据主要基于 probe，需持续观察自然任务创建/流转/导出的稳定性
- [ ] 前台 `progress` 入口口径澄清：当前 dashboard 服务端不存在 `/api/task-progress`，不应再列为验收项
- [ ] 持续抽查三面一致性：backend `/api/tasks`、`data/tasks_source.json`、`live_status.json.taskSource/taskSourceMeta`
- [ ] 观察 loop 回退窗口内兼容导出口径刷新是否足够及时
- [ ] 只有在 dual/export 稳定后，才评估 workspace 默认入口是否切到 `EDICT_KANBAN_ENTRY_MODE=auto/api`

## 4. 验收口径

- 不是"backend 服务能启动"就算完成，要看 dual/export 过渡态在连续刷新周期内稳定
- 不是"probe 通过"就算完成，要有自然业务样本
- 三面一致性必须在多个观测窗口持续对齐
- systemd 回滚演练不只是一次性动作，需要证明可重复
- 当前只能叫"过渡态验收中"，不能叫"纯 backend 主链切换完成"

## 5. 风险

- backend create 后初始态直接是 `Taizi`（不是 `Pending`），与旧预期不同，需持续注意
- 匿名 dashboard POST 有认证门槛（401），不能当成前台写链证据
- 本机处于分叉运行态（与 origin/main 不完全一致），升级时必须按 P0/P1/P2 保护规则执行

## 6. 证据引用

- 进度主板 §3.1：`docs/current-progress-board.md` 第 598–641 行
- 进度主板 §3.2：`docs/current-progress-board.md` 第 643–645 行
- 进度主板 §4.2.3：`docs/current-progress-board.md` 第 1002–1016 行
- systemd 回滚 runbook：`docs/plans/2026-04-30-systemd-rollback-drill-runbook.md`
- 回滚备份：`/root/.hermes/backups/rollback-drill-20260430-053642/`
