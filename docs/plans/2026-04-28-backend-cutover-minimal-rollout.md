# EDICT backend cutover 最小可回滚实施稿（2026-04-28）

> 适用任务：`EDICT-BACKEND-CUTOVER-001`
>
> 定位：不是重新设计理想架构，而是基于**现网默认值**给出一版能落地、可回滚、不误报完成的切流方案。

## 1. 当前结论

> 2026-04-30 reality-sync 补记：本稿前半段是 **2026-04-28 切流前夜** 的实施设计，不再代表当前默认运行态。继续使用本稿时，必须先套用下面这层新口径。

当前不是“backend 没接进来”，而是：

- **入口壳已落地**：`scripts/kanban_update.py` 已支持 `EDICT_KANBAN_ENTRY_MODE=legacy/api/auto/json`
- **dashboard 已埋 backend 分支**：`EDICT_TASK_WRITE_MODE in ('dual', 'api')` 时会走 backend client
- **backend export 已挂进 loop**：`EDICT_ENABLE_BACKEND_EXPORT=true` 时会跑 `export_backend_tasks_to_legacy_json.py`
- **现网默认值也已切到 dual/export 过渡态**：当前 `/etc/systemd/system/edict-dashboard.service` 已含 `Environment=EDICT_TASK_WRITE_MODE=dual`，`/etc/systemd/system/edict-loop.service` 已含 `Environment=EDICT_ENABLE_BACKEND_EXPORT=true`，`data/live_status.json.taskSource = "backend_api_export"`，`data/tasks_backend_export_meta.json` 已存在

**所以：生产现状已经不是 JSON 主路，而是 backend dual/export 过渡态；本稿现在主要用于指导“如何可逆回退”和“如何补 systemd 回滚演练证据”，不再用于证明默认值尚未切入。**

---

## 2. 本轮目标

本稿只解决一件事：

**把“已具备切换能力但默认未切”的状态，推进到“可控双写/双读过渡”阶段。**

不建议本轮直接追求：

- 一步切纯 `api`
- 彻底删除 JSON 兼容层
- 先动 workspace 默认入口、后补前台可见性

---

## 3. 现网约束

### 3.1 dashboard 仍是 JSON 主写

证据：

- `dashboard/server.py`
  - `TASK_WRITE_MODE = os.environ.get('EDICT_TASK_WRITE_MODE', 'json')`
  - `save_tasks()` 仍直接 `atomic_json_write(task_data_dir / 'tasks_source.json', tasks)`
- `edict-dashboard.service`
  - 仅设置 `EDICT_DASHBOARD_HOST=127.0.0.1`
  - 仅设置 `EDICT_DASHBOARD_PORT=7892`
  - **未设置 `EDICT_TASK_WRITE_MODE`**

结论：

- dashboard 代码虽然已有 backend 分支
- 但现网默认仍是 **JSON 写路径**

### 3.2 loop 仍未启 backend export

证据：

- `scripts/run_loop.sh`
  - `BACKEND_EXPORT_ENABLED="${EDICT_ENABLE_BACKEND_EXPORT:-0}"`
  - 仅 `is_true "$BACKEND_EXPORT_ENABLED"` 时才执行 `export_backend_tasks_to_legacy_json.py`
- `edict-loop.service`
  - 仅设置 `EDICT_HOME=/root/.openclaw/workspace/edict`
  - 仅设置 `EDICT_DASHBOARD_PORT=7892`
  - **未设置 `EDICT_ENABLE_BACKEND_EXPORT`**

结论：

- export 能力已接线
- 但生产刷新链默认仍是 **关闭状态**

### 3.3 workspace 仍共享项目根 data/scripts

证据：

- `workspace-taizi/data`、`workspace-taizi/scripts` 均是 symlink
- 实际解析回 `/root/.openclaw/workspace/edict/data` 与 `/root/.openclaw/workspace/edict/scripts`

结论：

- 一旦根脚本默认值切换，workspace 会整体受影响
- 所以**不能先切 workspace 默认入口，再补 dashboard/兼容层**

---

## 4. 切流原则

1. **先让 dashboard 与兼容导出层进入 dual 过渡，再动 workspace 默认入口**
2. **任何切换都必须能靠 systemd 环境变量回滚，不靠现场改源码**
3. **空 backend 不能覆盖前台兼容出口**
4. **验证通过 ≠ 已切流；必须以运行态默认值为准**

---

## 5. 推荐实施顺序

## Phase 1：只打开 backend export，不改 dashboard 默认写模式

### 目标
先验证 backend -> JSON 兼容导出链在现网可稳定跑通。

### 动作
1. 变更前备份：
   - `/etc/systemd/system/edict-loop.service`
2. 给 `edict-loop.service` 增加：
   - `Environment=EDICT_ENABLE_BACKEND_EXPORT=true`
3. 暂不设置：
   - `EDICT_BACKEND_EXPORT_ALLOW_EMPTY=true`
4. `daemon-reload` + 重启 `edict-loop.service`

### 预期
- 若 backend 仍为空：
  - export 脚本应因空结果保护而**不覆盖现有 `tasks_source.json`**
- 若 backend 开始有任务：
  - `data/tasks_backend_export_meta.json` 出现
  - `live_status.json.taskSource` 变为 `backend_api_export`

### 验证点
- `data/tasks_backend_export_meta.json` 是否生成
- `data/live_status.json` 的 `taskSource / taskSourceMeta`
- `tasks_source.json` 是否未被误清空

### 回滚
- 去掉 `EDICT_ENABLE_BACKEND_EXPORT=true`
- `daemon-reload` + 重启 `edict-loop.service`

---

## Phase 2：把 dashboard 从 `json` 提到 `dual`

### 目标
让前台关键写入口优先走 backend，但保留兼容读面。

### 前提
必须先满足至少一条：

- backend `GET /api/tasks` 已非空
- 或 backend create/review/dispatch 的最小 smoke 已确认可写

### 动作
1. 变更前备份：
   - `/etc/systemd/system/edict-dashboard.service`
2. 给 `edict-dashboard.service` 增加：
   - `Environment=EDICT_TASK_WRITE_MODE=dual`
3. 保持 loop 侧 export 开启
4. `daemon-reload` + 重启 `edict-dashboard.service`

### 预期
- `/api/create-task`、`/api/review-action` 之类前台关键入口优先写 backend
- 前台读面仍可通过兼容导出层看到任务
- 若 backend 某条入口失败，`dual` 模式应保留清晰失败/回退行为，而不是静默吞掉

### 验证点
- dashboard 新建任务后，backend `/api/tasks` 中能看到该任务
- `tasks_backend_export_meta.json` 的 `count` 与 `tasks_source.json` 同步变化
- `live_status.json.taskSource = backend_api_export`
- 前台 UI 仍能看到任务，不出现“后台成功但前台没影”

### 回滚
- 把 `EDICT_TASK_WRITE_MODE=dual` 改回 `json`
- 重启 `edict-dashboard.service`

---

## Phase 3：再评估 workspace 默认入口是否切 `api/auto`

### 目标
只有在 dashboard + export 过渡稳定后，才允许影响 workspace 默认入口。

### 动作
本轮**不建议直接改默认值**。

更稳的方式是先做小范围验证：
- 单独对某个受控执行环境临时设：
  - `EDICT_KANBAN_ENTRY_MODE=auto` 或 `api`

### 前提
- dashboard 已稳定 dual
- backend export 已持续正常
- 至少一轮真实 smoke 证明 backend 主写链可见、可查、可回读

### 回滚
- 去掉 `EDICT_KANBAN_ENTRY_MODE`
- 默认即回到 legacy

---

## 6. 不要现在就做的事

以下动作现在做，风险大于收益：

1. **直接把 dashboard 设成 `api`**
   - 现网还没有证据证明所有写入口都已完全覆盖
2. **直接把 workspace 默认入口切 `api`**
   - 会先影响 agent 真实任务流，且前台未必同步稳住
3. **开启 `EDICT_BACKEND_EXPORT_ALLOW_EMPTY=true`**
   - 这等于允许空 backend 覆盖掉前台现有任务出口，太危险

---

## 7. 最小 smoke 清单

进入 Phase 2 前后，至少做一轮最小 smoke：

1. 新建一个临时任务
2. 更新一次 progress
3. 更新一次 todos
4. 做一次 review/approve 或 dispatch
5. 检查：
   - backend `/api/tasks` 里有它
   - `tasks_source.json` 里也能看到兼容投影
   - `live_status.json.taskSource` 口径正确
6. 清理临时任务或标记为 smoke 样本

---

## 8. 收口标准

只有满足下面条件，才能把主线口径改成“已切 backend 主链”：

- `edict-dashboard.service` 默认已是 `EDICT_TASK_WRITE_MODE=dual` 或 `api`
- `edict-loop.service` 默认已开启 backend export
- `live_status.json.taskSource` 不再是裸 `tasks_source.json`
- `tasks_backend_export_meta.json` 持续存在并正常刷新
- 至少一轮真实 smoke 证明 backend 写入、兼容导出、前台可见三者一致
- 回滚方法已写入文档并现场可执行

在此之前，统一口径都应保持：

**“backend 代码链已具备，生产默认仍在 JSON 主路，当前处于可控过渡前夜。”**
