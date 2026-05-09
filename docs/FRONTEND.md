# 前端与展示治理

## 1. 目标
前端治理文档只管：**展示层有没有真实反映后端事实，用户看到的东西有没有误导。**

## 2. 当前关注点
1. dashboard 展示是否与后端真实状态一致
2. 是否存在"后端已有字段，前端没消费"的断层
3. 是否存在"页面能看，但口径是假完成"的误导
4. 前端异常是否有最小可复现路径与截图/证据

## 3. 治理原则
- 不把 UI 可见当成事实已成立
- 不把接口 200 当成用户链路真实闭环
- 前后端口径不一致时，以运行态证据和主板回写为准
- 前端问题要区分：数据没来、字段没接、展示错了、交互链断了

## 4. 关键入口与端口

| 组件 | 地址 | 用途 |
|------|------|------|
| Dashboard 前端 | `http://127.0.0.1:7892` | 主看板入口 |
| Dashboard API | `http://127.0.0.1:7892` (同端口) | 前端调用的后端 API |
| Backend API | `http://127.0.0.1:18000` | edict 后端主 API |
| Health check | `http://127.0.0.1:7892/healthz` | Dashboard 健康 |
| Deep health | `http://127.0.0.1:18000/api/admin/health/deep` | 后端深度健康 |
| 任务列表 | `http://127.0.0.1:18000/api/tasks?limit=10` | 后端任务 API |

**注意**：Dashboard 端口 7892 和 Backend API 端口 18000 是两个独立服务。Dashboard 有自己的 `/healthz`，Backend 有自己的 `/health`。

## 5. 关键页面

| 页面 | 功能 | 对应后端真值源 |
|------|------|--------------|
| 任务看板（Kanban） | 任务列表、状态、分配 | `/api/tasks` + `data/tasks_source.json` |
| 审批面板 | 待审批任务与操作 | `/api/tasks` (status filter) |
| 调度器状态 | scheduler 运行状态 | `task._scheduler` 字段 |
| 超时汇总 | 超时任务统计 | 任务 timeout 相关字段 |
| Autopsy | 任务复盘/死因分析 | 任务生命周期记录 |
| 模型配置 | provider/model 设置 | `openclaw.json` → `agents.defaults.model` |
| Skills 配置 | 技能管理 | `/api/skills` 或本地 skill 目录 |
| Sessions | 会话管理 | `sessions.list` |

截图参考：`docs/screenshots/` 目录下有完整页面截图。

## 6. 前后端已知断层（Frontend/Backend Gaps）

### 6.1 `/api/task-progress` 不存在
- **现象**：文档或早期方案中提到 `task-progress` 端点
- **实际**：dashboard 使用 `advance-state` 而非 `task-progress` 来推进任务状态
- **影响**：不要依赖 `task-progress` 作为任务推进入口

### 6.2 匿名 POST 返回 401
- **现象**：直接 POST dashboard API 返回 401 Unauthorized
- **实际**：需要先通过 `edict_token` 登录，获得认证后才能调用
- **影响**：脚本/自动化调用前必须先处理认证

### 6.3 Backend 创建初始状态是 Taizi，不是 Pending
- **现象**：旧文档说新任务初始状态为 `Pending`
- **实际**：backend create 的初始状态为 `Taizi`
- **影响**：任务生命周期模型和前端状态筛选需对应更新

### 6.4 `_scheduler` 字段 vs 顶层 `scheduler` 字段
- **现象**：任务对象存在 `_scheduler` 字段（带下划线前缀），但很多活跃任务缺少顶层 `scheduler` 字段
- **实际**：`_scheduler` 是内部字段，前端不一定消费；顶层 `scheduler` 字段覆盖率不完整
- **影响**：基于 `scheduler` 字段做调度状态展示时可能遗漏任务

### 6.5 任务计数三方对齐
- 验证时需确认三方计数一致：`data/live_status.json.taskSourceMeta.count` = `data/tasks_backend_export_meta.json.count` = `data/tasks_source.json` 行数
- 不一致时说明导出链路有问题，前端展示的数字不可信

## 7. 前端治理技能

- **技能名称**：`edict-frontend-governance-ui`
- **职责**：前端展示层治理、UI 问题排查、前后端一致性验证
- **关联资产**：`docs/screenshots/`、dashboard 方案与主板记录

## 8. 检查清单

### 前端展示 ≠ 治理落地
- [ ] 页面能打开 ≠ 数据已到位
- [ ] 接口返回 200 ≠ 数据正确
- [ ] 数字在变 ≠ 变化有意义
- [ ] 状态显示完成 ≠ 真实执行完成
- [ ] 图表有数据 ≠ 数据来源可信

### 前端问题分类
| 类型 | 判断标准 | 处理方向 |
|------|---------|---------|
| 数据没来 | 接口无返回或返回空 | 查后端 API + 数据源 |
| 字段没接 | 后端有字段但前端未消费 | 查前端组件映射 |
| 展示错了 | 数据到了但渲染不对 | 查前端展示逻辑 |
| 交互链断了 | 操作无响应或报错 | 查 API 调用链 + 认证 |

## 9. 当前相关资产
- `docs/screenshots/`：12 张关键页面截图（kanban、monitor、task-detail、model-config 等）
- `docs/current-progress-board.md`：主板中的 dashboard 相关记录
- `docs/plans/2026-04-30-systemd-rollback-drill-runbook.md`：涉及 dashboard service 的回滚演练
- `edict-frontend-governance-ui` 技能
- `scripts/doctor_edict.sh`：包含 dashboard health check 验证
- `tests/backend_test_env.py`：backend 相关测试统一 bootstrap，降低前端/后端联调时的假红假绿
- `edict/backend/app/api/tasks.py`：`TaskOut` 已改用 `ConfigDict(from_attributes=True)`，减少 Pydantic v2 旧告警对前后端联调日志的噪声

## 10. 后续待补
- 补一份完整的 API 端点清单（dashboard 7892 vs backend 18000）
- 把 `_scheduler` 字段覆盖率做成定期检查
- 记录关键 UI 问题的最小复现与验收口径
- 建立前端 E2E 验证：至少覆盖"创建任务 → 看板可见 → 状态推进 → 完成"链路

## 11. 相关文档

| 文档 | 关联章节 | 说明 |
|------|---------|------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | §7 关键端口速查、§4.4 数据刷新链 | 端口映射、数据流链路 |
| [RELIABILITY.md](RELIABILITY.md) | §2 服务拓扑与状态、§3 检查清单 | 服务存活判定、变更后验证步骤 |
