# edict / OpenClaw / Hermes 架构治理

## 1. 目的

这份文档不重复源码细节，只回答三件事：
1. **谁负责什么**
2. **关键链路怎么走**
3. **出问题时先去哪一层定位**

## 2. 三层职责

### 2.1 Hermes (玄成)

- **角色**: AI 助手，前台入口，本体判断，任务分派，分身督办，最终汇报
- **常驻能力**: SOUL / memory / skills / todo / cron / delegation
- **运行位置**: 213.35.100.132，进程 hermes-gateway
- **模型**: GPT-5.4 via custom provider (windhub.cc)
- **通信**: 飞书 (Feishu) 主通道，DM + 群聊
- **workspace**: `/root/.hermes`
- **日志**: `/root/.hermes/logs/gateway.log`
- **重点约束**: 本体统一接活与收口，分身不直接对外表态

**出问题先去**:
- `journalctl -u hermes-gateway --user` 或 `tail -100 /root/.hermes/logs/gateway.log`
- 检查 memory 目录下当天日志确认上下文是否连续

### 2.2 OpenClaw (阿爪 / taizi)

- **角色**: Agent 运行时，执行总线，session 管理，渠道投递，模型调用链
- **运行位置**: 213.35.100.132，进程 `openclaw-gateway` (PID 3485982)
- **监听端口**: 38463 (内部) / 18789 (gateway API + control UI)
- **配置**: `/root/.openclaw/openclaw.json`
- **workspace**: `/root/.openclaw/workspace` (共享)，各 agent 独立 workspace 在 `/root/.openclaw/workspace-{agent_id}`
- **模型链**: primary `windhub/gpt-5.4`，fallback `longcat/LongCat-Flash-Chat` (contextWindow 256000)
- **重点链路**: 入站 → 路由 → dispatch → agent 执行 → final reply → timeout/fallback → session continuity

**当前注册 agent**:

| Agent ID | edict 对应角色 | workspace | 可调度子 agent |
|----------|---------------|-----------|---------------|
| taizi | 太子 | workspace-taizi | zhongshu |
| zhongshu | 中书 | workspace-zhongshu | menxia, shangshu |
| menxia | 门下 | workspace-menxia | shangshu, zhongshu |
| shangshu | 尚书 | workspace-shangshu | hubu, libu, bingbu, xingbu, gongbu, libu_hr, zhongshu, menxia |
| hubu | 户部 | workspace-hubu | shangshu |
| libu | 礼部 | workspace-libu | shangshu |
| bingbu | 兵部 | workspace-bingbu | shangshu |
| xingbu | 刑部 | workspace-xingbu | shangshu |
| gongbu | 工部 | workspace-gongbu | shangshu |
| libu_hr | 吏部 | workspace-libu_hr | shangshu |
| zaochao | 早朝 | workspace-zaochao | (无) |

**渠道绑定**: telegram → taizi, feishu → taizi（群聊 groupSessionScope = `group_sender`）

**出问题先去**:
- `ss -ltnp | grep 38463` 或 `ss -ltnp | grep 18789` 确认 gateway 端口是否在听
- `journalctl -u openclaw` 或直接检查 OpenClaw 日志目录
- 确认 `openclaw.json` 中 provider apiKey 是否有效（windhub/longcat 两个 provider）
- session 卡死时检查 `/root/.openclaw/agents/` 下对应 agent 的 session 文件

### 2.3 edict

- **角色**: 治理主板，任务生命周期管理，数据聚合，巡检，runbook
- **仓库**: `/root/.openclaw/workspace/edict`
- **后台 API**: `127.0.0.1:18000` (FastAPI/uvicorn，app.main:app)
- **看板**: `127.0.0.1:7892` (dashboard/server.py)
- **数据层**: PostgreSQL (127.0.0.1:5432, db=edict) + Redis (127.0.0.1:6379/0) + JSON 文件层
- **写入模式**: `EDICT_TASK_WRITE_MODE=dual` (同时写 JSON 和 backend)

**后台 worker 进程**:

| Worker | systemd 服务 | 入口 | 职责 |
|--------|-------------|------|------|
| API | edict-backend-api.service | uvicorn app.main:app :18000 | REST API + WebSocket |
| outbox-relay | edict-backend-outbox-relay.service | app.workers.outbox_relay | outbox 事件投递 |
| orchestrator | edict-backend-orchestrator.service | app.workers.orchestrator_worker | 任务编排 |
| dispatch | edict-backend-dispatch.service | app.workers.dispatch_worker | agent 调度 |

**数据刷新循环** (edict-loop.service): 每 15 秒执行一轮：

```
guard_openclaw_sessions.py  → session 健康检查
sync_from_openclaw_runtime.py → 同步 OpenClaw 运行态数据
sync_governance_samples.py → 同步治理样本
rebuild_task_views.py → 重建任务视图
export_backend_tasks_to_legacy_json.py → backend → JSON 导出 (需 EDICT_ENABLE_BACKEND_EXPORT=true)
sync_agent_config.py → 同步 agent 配置
apply_model_changes.py → 应用模型变更 (超时 75s)
sync_officials_stats.py → 同步官员统计
refresh_live_data.py → 刷新 live_status.json
baota_webserver_patrol.py → 宝塔 webserver 巡检
```

**出问题先去**:
- `systemctl status edict-backend-api edict-backend-dispatch edict-backend-orchestrator edict-backend-outbox-relay` 检查 worker 状态
- `journalctl -u edict-backend-api -n 50 --no-pager` 查 API 日志
- `journalctl -u edict-loop -n 50 --no-pager` 查刷新循环日志
- `/tmp/sansheng_liubu_refresh.log` 是循环脚本的标准输出日志
- `curl http://127.0.0.1:7892/healthz` 检查看板是否存活
- `curl http://127.0.0.1:18000/docs` 检查 backend API 是否存活

## 3. 当前推荐事实源分层

### 3.1 文档层 (人工可读)

- `docs/current-progress-board.md`: 当前主板
- `docs/exec-plans/active/`: 执行中的标准执行稿
- `docs/exec-plans/completed/`: 已完成执行稿归档
- `docs/plans/`: 历史方案、专题方案、背景稿
- `docs/closeout.md`: 正式收口结论
- `docs/templates/`: 模板与 pilot 样例

### 3.2 机器可读状态层

- `docs/state/feature-status.json`: 功能状态跟踪 (schema_version 1.0)
- `data/tasks_source.json`: 任务源数据
- `data/tasks_runtime_view.json`: 运行态任务视图
- `data/tasks_governance_samples.json`: 治理样本
- `data/tasks_jjc_archive.json`: JJC 归档
- `data/live_status.json`: 系统实时状态
- `data/officials_stats.json`: 官员统计
- `data/agent_config.json`: agent 配置快照
- `data/sync_status.json`: 同步状态
- `data/audit_log.json`: 审计日志
- `data/task_memory/{task_id}.json`: 单任务记忆文件 (带 .lock 文件)
- `data/agent_memory/{agent_id}.json`: agent 级记忆文件

### 3.3 三层数据分离

| 层 | 文件 | 用途 |
|----|------|------|
| runtime | tasks_runtime_view.json | 当前运行态视图 |
| governance | tasks_governance_samples.json | 治理验收样本 |
| archive | tasks_jjc_archive.json | 历史归档 |

## 4. 关键链路

### 4.1 主线治理升级链

```
用户需求 / 现场问题
  → 飞书消息 → OpenClaw gateway (feishu plugin) → taizi agent session
  → Hermes 判断与路由
  → edict 形成执行稿 / 验收口径 / 主板回写
     - tasks_source.json 写入 (legacy JSON)
     - backend API 写入 (POST /api/tasks)
     - dual 模式下两者同步
  → shangshu/六部 agent 执行
  → 运行态证据回流 edict
     - sync_from_openclaw_runtime.py 拉取
     - rebuild_task_views.py 重建视图
  → Hermes 对外汇报与收口
```

### 4.2 运行态故障链

```
现场异常
  → OpenClaw / systemd / API / logs 定位
     - `journalctl -u edict-backend-api -n 100`
     - `tail -100 /tmp/sansheng_liubu_refresh.log`
  → edict 汇总证据与止血方案
     - doctor_edict.sh 全面巡检
     - guard_openclaw_sessions.py session 健康检查
  → Hermes 组织执行与回报
```

### 4.3 任务调度链 (三省六部)

```
太子 (taizi) 接收用户请求
  → 中书 (zhongshu) 起草方案
  → 门下 (menxia) 审核驳回/通过
  → 尚书 (shangshu) 分发到具体部:
     - 户部 (hubu): 财务/资源
     - 礼部 (libu): 礼仪/规范
     - 兵部 (bingbu): 安全/运维
     - 刑部 (xingbu): 审计/纠错
     - 工部 (gongbu): 工程/建设
     - 吏部 (libu_hr): 人事/考核
  → Assigned → Doing → Done
```

### 4.4 数据刷新链

```
edict-loop.service (每 15s)
  → run_loop.sh 驱动 Python 脚本序列
  → 各脚本通过 file_lock.py 原子读写 JSON
  → dashboard/server.py 内部 120s 线程做 scheduler-scan
  → live_status.json / officials_stats.json 等实时文件更新
  → 看板前端通过 /api/live-status 等 endpoint 拉取
```

### 4.5 后台 Backend 数据链

```
API (uvicorn :18000)
  → PostgreSQL (127.0.0.1:5432/edict)
  → Redis (127.0.0.1:6379/0)
  → outbox_relay: 监听 outbox 表，投递到 channel
  → orchestrator_worker: 任务编排，状态机推进
  → dispatch_worker: agent 调度，超时处理 (DISPATCH_TIMEOUT_SEC=300)
```

## 5. systemd 服务全景

### 5.1 edict 服务栈

| 服务 | 类型 | 依赖 | 说明 |
|------|------|------|------|
| edict-backend-infra.service | oneshot | docker.service | PostgreSQL + Redis 容器管理 |
| edict-backend-api.service | simple | infra | FastAPI 后端 |
| edict-backend-outbox-relay.service | simple | infra | outbox 事件投递 |
| edict-backend-orchestrator.service | simple | infra, outbox-relay | 任务编排 |
| edict-backend-dispatch.service | simple | infra, orchestrator | agent 调度 |
| edict-dashboard.service | simple | - | 看板 server |
| edict-loop.service | simple | dashboard | 数据刷新循环 |

所有 backend 服务通过 `PartOf=edict-backend-stack.target` 组成一个 target。

### 5.2 Hermes 服务

| 服务 | 类型 | 说明 |
|------|------|------|
| hermes-gateway (user) | simple | Hermes 主进程 |

## 6. 当前架构原则

1. **不平行再造一套与现有体系竞争真值的工作流** — 只有一条 mainboard
2. **不把"测试通过"冒充"真实交付完成"** — closeout 要有真实证据
3. **任何系统变动都要回写主板** — current-progress-board.md 是 truth source
4. **高风险动作先过边界闸口** — model changes 经 apply_model_changes.py + lock
5. **文档骨架要服务真实主线，不做摆设** — 不写没用的文档
6. **三层数据不混** — runtime / governance / archive 各司其职
7. **dual 写入模式** — JSON 文件层 + backend API 并行写，保证过渡期不丢数据

## 7. 关键端口速查

| 端口 | 服务 | 绑定 |
|------|------|------|
| 18000 | edict backend API | 127.0.0.1 |
| 7892 | edict dashboard | 127.0.0.1 |
| 18789 | OpenClaw gateway API | 127.0.0.1 (loopback) |
| 38463 | OpenClaw 内部端口 | 127.0.0.1 |
| 5432 | PostgreSQL | 127.0.0.1 (Docker infra) |
| 6379 | Redis | 127.0.0.1 (Docker infra) |

## 8. 巡检与恢复

### 8.1 全面巡检

```bash
bash /root/.openclaw/workspace/edict/scripts/doctor_edict.sh
```

检查项: python3/openclaw/jq 命令、数据目录、JSON 完整性、所有 workspace、systemd 服务、端口监听、healthz endpoint、Feishu P2P 守卫。

### 8.2 Session 健康检查

```bash
python3 /root/.openclaw/workspace/edict/scripts/guard_openclaw_sessions.py
```

扫描 `/root/.openclaw/agents/` 下所有 session，检测 context overflow、模型 fallback、token 异常等问题。

### 8.3 常见故障定位

| 症状 | 先查 | 再查 |
|------|------|------|
| 飞书消息不回 | OpenClaw gateway 端口、feishu plugin 状态 | taizi session 是否卡死、provider apiKey 是否有效 |
| 后台 API 无响应 | `systemctl status edict-backend-api` | PostgreSQL/Redis 是否在运行、`journalctl -u edict-backend-api` |
| 数据刷新停止 | `systemctl status edict-loop` | `/tmp/sansheng_liubu_refresh.log`、单个脚本手动执行 |
| 任务卡在 Assigned | `data/tasks_runtime_view.json` | orchestrator_worker 日志、dispatch_worker 超时配置 |
| 看板空白 | `curl http://127.0.0.1:7892/healthz` | `data/live_status.json` 是否存在且非空 |
| model fallback 频繁 | `data/last_model_change_result.json` | windhub apiKey 余额、longcat provider 状态 |

### 8.4 恢复顺序

1. 先重试轻量操作 (restart 个别 service)
2. 再切换备选路径 (fallback model)
3. 再隔离局部故障 (停单个 worker)
4. 最后考虑整体重启 (edict-backend-stack.target)

## 9. 插件与集成

| 插件 | 状态 | 用途 |
|------|------|------|
| feishu | enabled | 飞书消息收发 (websocket 连接模式) |
| telegram | enabled | Telegram 消息收发 |
| memos-cloud-openclaw-plugin | enabled | 记忆存储 (memtensor.cn) |

飞书群聊配置:
- `oc_d47ec695600634cc6a6d9dd577bedd22`: groupSender scope
- `oc_5db4fdccbb3e018b405fb6c6c9fb7243`: groupSender scope

## 10. 当前风险与待办

参见 `docs/state/feature-status.json` 获取实时状态。当前已知:

- **EDICT-BACKEND-CUTOVER-001**: backend host-native dual/export 过渡态，前台写链 smoke 仍未收口
- **OPENCLAW-FEISHU-DM-001**: taizi 直聊 session 长跑 + 偶发消息整理脏状态
- **EDICT-HARNESS-GOV-001**: 治理骨架已落，真实主线迁入 exec-plans/active/ 仍进行中

## 11. 相关文档

| 文档 | 关联章节 | 说明 |
|------|---------|------|
| [RELIABILITY.md](RELIABILITY.md) | §2 服务拓扑、§3 检查清单、§7 回滚能力 | 服务存活判定、变更后验证、回退路径 |
| [SECURITY.md](SECURITY.md) | §3 高风险动作、§5 配置变更协议 | 高风险动作边界、备份与回写要求 |
| [FRONTEND.md](FRONTEND.md) | §4 端口与入口、§6 前后端断层 | 前端展示层与后端一致性 |

**关键 Runbook：**

| Runbook | 路径 | 用途 |
|---------|------|------|
| systemd 回滚演练 | [docs/plans/2026-04-30-systemd-rollback-drill-runbook.md](plans/2026-04-30-systemd-rollback-drill-runbook.md) | 双阶段回滚演练步骤 |
| 飞书旁路补偿 | [docs/openclaw-feishu-bypass-compensation-runbook.md](openclaw-feishu-bypass-compensation-runbook.md) | feishu bypass 补偿流程 |
| 健康检查 | [scripts/doctor_edict.sh](../scripts/doctor_edict.sh) | 全面巡检 (PASS/WARN/FAIL) |
| 安全更新 | [scripts/safe_update.sh](../scripts/safe_update.sh) | 带备份/token gate/rollback 的更新 |
| 记忆备份 | [scripts/memory_backup.sh](../scripts/memory_backup.sh) | memory 数据备份 |
