# 可靠性治理

> 最后更新: 2026-04-30T16:27 CST
> 状态基线: doctor PASS=31 WARN=1 FAIL=0

## 1. 目标

可靠性文档只管一件事：**让系统持续可跑、出事能查、回退有据。**

具体来说：
- 每个关键服务有明确的存活判定条件
- 每次变更后有可复制的验证步骤
- 每个已知问题有记录、有影响范围、有临时对策
- 回退路径不是"理论上存在"，而是"实际演练过"

---

## 2. 当前服务拓扑与状态

### 2.1 服务清单

| 服务 | systemd unit | 端口 | 状态(截至 2026-04-30 16:27) |
|------|-------------|------|---------------------------|
| EDICT Dashboard | `edict-dashboard.service` | 7892 | ✅ active |
| EDICT Loop | `edict-loop.service` | — | ✅ active |
| Backend API | — | 18000 | ✅ ok, version=2.0.0 |
| OpenClaw Gateway | systemd user / PID | 8000+ | ✅ PID 3485982, uptime ~18.5h, RSS ~526MB |

### 2.2 关键环境变量（当前生产值）

```ini
# edict-loop.service
Environment=EDICT_ENABLE_BACKEND_EXPORT=true

# edict-dashboard.service
Environment=EDICT_TASK_WRITE_MODE=dual
```

### 2.3 Health Endpoints

| 端点 | 用途 | 当前返回 |
|------|------|---------|
| `http://127.0.0.1:7892/healthz` | Dashboard 健康 | `{"status":"ok"}` |
| `http://127.0.0.1:18000/health` | Backend API 基本健康 | `{"status":"ok","version":"2.0.0","engine":"edict"}` |
| `http://127.0.0.1:18000/api/admin/health/deep` | 深度检查（postgres+redis） | `{"status":"ok","checks":{"postgres":true,"redis":true}}` |

### 2.4 数据导出口径

当前数据流：
- `taskSource = backend_api_export`
- `tasks_backend_export_meta.json` 存在，count=4，最近导出 `2026-04-30T08:27:07 UTC`
- `tasks_source.json` 存在，count=4（与 backend `/api/tasks` 一致）

---

## 3. 最小可靠性检查清单（每次变更后必跑）

按顺序执行，任一步失败即停止推进：

```bash
# 1. systemd 服务状态
systemctl is-active edict-dashboard.service edict-loop.service

# 2. health 端点
curl -s http://127.0.0.1:7892/healthz
curl -s http://127.0.0.1:18000/health
curl -s http://127.0.0.1:18000/api/admin/health/deep

# 3. doctor 全检
cd /root/.openclaw/workspace/edict && bash scripts/doctor_edict.sh

# 4. 数据一致性：tasks_source.json vs live_status.json vs /api/tasks
python3 -c "
import json, pathlib
src = json.loads(pathlib.Path('data/tasks_source.json').read_text())
live = json.loads(pathlib.Path('data/live_status.json').read_text())
print(f'tasks_source count={len(src) if isinstance(src,list) else \"N/A\"}')
print(f'live_status taskSource={live.get(\"taskSource\")}')
"
curl -s 'http://127.0.0.1:18000/api/tasks?limit=50' | python3 -c "
import sys,json; d=json.load(sys.stdin); print(f'backend /api/tasks count={len(d.get(\"tasks\",[]))}')
"

# 5. OpenClaw gateway 进程与端口
ps aux | grep openclaw-gateway | grep -v grep
```

### 3.1 doctor_edict.sh 最近结果（2026-04-30）

```
PASS=31  WARN=1  FAIL=0
```

- 31 项全部通过
- 1 项 WARN：`gateway.err.log` 停止更新（见 §5.3）
- 0 项 FAIL

**判定标准：FAIL=0 才可推进变更。WARN 需逐条评估是否阻塞。**

---

## 4. 当前硬规则

| 编号 | 规则 | 说明 |
|------|------|------|
| R-1 | **没有运行态证据，不得宣称稳定** | 必须有 doctor PASS + health 200 的实际输出 |
| R-2 | **没有回滚边界，不做高风险推广** | 变更前必须确认回退路径可执行 |
| R-3 | **系统改动必须回写主板** | `current-progress-board.md` 必须同步更新 |
| R-4 | **验证通过 ≠ 交付完成** | 验证、产物、现场结果必须分开记录 |
| R-5 | **回退态不长时间停留** | 演练回退后 1~3 分钟内必须回切 |

---

## 5. 已知问题与影响记录

### 5.1 ⚠️ windhub/gpt-5.4 API Key 过期（401）

- **现象**: OpenClaw/taizi 出现间歇性无响应
- **根因**: 上游 provider 的 API key 已过期，返回 401
- **影响范围**: 依赖该 provider 的 session 请求会失败或降级到 fallback
- **状态**: 已知问题，需要续期 key 或切换 provider
- **临时对策**: gateway 有 fallback 机制，但 fallback provider 也不稳定（见 5.2）

### 5.2 ⚠️ 524 状态码错误（上游 provider）

- **现象**: 上游模型 provider 间歇返回 524（超时）
- **影响范围**: 部分 session 请求失败，用户侧表现为无响应或延迟回复
- **状态**: 外部依赖问题，无法直接修复
- **对策**: 已在 gateway 层配置 fallback，但仍偶发

### 5.3 ⚠️ Session Lane Wait 超时

- **现象**: `Session lane wait exceeded (146525ms)` on taizi feishu direct session
- **根因**: session 并发排队超时
- **影响范围**: 特定 session 的消息处理延迟
- **状态**: 观察中

### 5.4 ⚠️ Orphaned User Messages

- **现象**: 部分 session 中存在孤立的用户消息未被处理
- **状态**: 需要定期清理

### 5.5 ℹ️ gateway.err.log 停止更新

- **现象**: `gateway.err.log` 自 2026-04-07 后无新内容
- **根因**: 日志输出已重定向到 socket，不再写入该文件
- **影响**: doctor 检查产生 1 条 WARN，不影响实际功能
- **状态**: 预期行为，非故障

### 5.7 ✅ backend 测试隔离统一到 bootstrap + Pydantic v2 告警首轮清理（2026-05-02）

- **现象**：多份 backend async 测试依赖 `DATABASE_URL` / `EDICT_HOME` / `OPENCLAW_PROJECT_DIR`，过去在模块顶层直接改环境变量并清 `sys.modules`；单文件可过，但合并到同一 pytest 进程后容易互相串库、串 engine、串模块缓存。
- **处理**：新增统一 bootstrap `tests/backend_test_env.py`，把临时目录、SQLite DB、环境变量写入、`edict.backend.app*` 模块清缓存、fresh import 全部收敛到一个入口；相关测试改为在 `asyncSetUp()` 内按需建隔离环境。
- **覆盖测试**：`test_backend_task_meta_fallback.py`、`test_backend_review_action.py`、`test_dispatch_output_persistence.py`、`test_review_action_routes.py`、`test_task_service_manual_dispatch.py`、`test_task_service_governance_adoption.py`、`test_legacy_dispatch_target_route.py`、`test_orchestrator_stalled.py`。
- **验证结果**：组合回归 `python3 -m pytest -q ...` 当前为 **19 passed**，说明这批 backend 测试已不再靠“分开跑”规避串扰。
- **并行清理**：`edict/backend/app/api/tasks.py` 已把 `class Config` 升级为 `model_config = ConfigDict(from_attributes=True)`，压掉一批 Pydantic v2 旧告警；`legacy.py` 已补 `ConfigDict` 导入，便于后续继续统一 schema 口径。
- **影响**：这条属于测试可靠性与开发侧告警治理，不等于业务功能新增；但它直接降低了 backend 改动后“单测单独过、组合挂”的假稳定风险。
---

## 6. 可靠性资产清单

### 6.1 诊断与监控

| 资产 | 路径 | 用途 |
|------|------|------|
| doctor 检查脚本 | `scripts/doctor_edict.sh` | 全面健康检查（PASS/WARN/FAIL 计数） |
| Health endpoints | §2.3 | 运行时健康探针 |
| Deep health | `/api/admin/health/deep` | postgres + redis 检查 |

### 6.2 变更与回退

| 资产 | 路径 | 用途 |
|------|------|------|
| 安全更新脚本 | `scripts/safe_update.sh` | 带备份/token gate/rollback 的更新流程 |
| systemd 回滚演练 runbook | `docs/plans/2026-04-30-systemd-rollback-drill-runbook.md` | 完整的双阶段回滚演练步骤 |

### 6.3 文档

| 资产 | 路径 | 用途 |
|------|------|------|
| 主板 | `docs/current-progress-board.md` | 全局进度追踪 |
| 验收记录 | `docs/closeout.md` | 交付验收 |
| 本文件 | `docs/RELIABILITY.md` | 可靠性治理（本文） |

---

## 7. 回滚能力

### 7.1 systemd 级回滚（已演练）

**演练时间**: 2026-04-30 05:45 CST

**验证内容**:
1. `edict-loop.service` 去掉 `EDICT_ENABLE_BACKEND_EXPORT=true` → 服务仍启动，`tasks_source.json` 未被清空
2. `edict-dashboard.service` `EDICT_TASK_WRITE_MODE=dual` 改为 `json` → 服务仍启动，healthz 仍可达
3. 回切后两服务恢复，`taskSource=backend_api_export` 恢复

**演练结果**: PASS — systemd 级回退可执行且可回切

**回退顺序**:
- 退：先 loop，再 dashboard
- 回：先 dashboard，再 loop

**详细步骤**: 见 `docs/plans/2026-04-30-systemd-rollback-drill-runbook.md`

### 7.2 数据面回滚

`scripts/safe_update.sh` 提供 backup/rollback 入口，但：
- **当前未做整包数据回滚演练**
- systemd 演练明确不涉及 `data/` 回滚
- 需要单独补齐数据面回滚验证

---

## 8. 监控与告警现状

### 8.1 已有

- `doctor_edict.sh` — 手动执行，PASS/WARN/FAIL 输出
- health endpoints — 手动 curl 或 agent 定期检查
- OpenClaw Feishu P2P 守卫 — 自动检测 service_start 后的状态

### 8.2 缺失

- ❌ 无自动定时 doctor 执行（需 cron/heartbeat 触发）
- ❌ 无 alerting/webhook（doctor FAIL 时无主动通知）
- ❌ 无日志异常自动检测
- ❌ 无 gateway RSS/uptime 趋势监控

---

## 9. 后续待补齐

### P0（阻塞性）

- [x] `verification-ledger` 落盘：每次变更的验证结果结构化记录 → 已存在 `docs/state/verification-ledger.json`
- [x] 关键服务补"最小可靠性验收清单"：每个服务定义 PASS/FAIL 判定条件 → 已存在 `docs/state/feature-status.json`

### P1（改善型）

- [ ] 把 doctor / health / rollback 验证口径标准化为可自动执行的格式
- [ ] 补数据面回滚演练（与 systemd 演练分开做）
- [ ] 建立 gateway RSS 内存上限告警（当前 526MB，观察趋势）
- [ ] 配置 heartbeat 定期触发 doctor 检查

### P2（观察型）

- [ ] windhub/gpt-5.4 API key 状态跟踪与自动续期机制
- [ ] upstream provider 524 错误率统计
- [ ] session lane wait 超时频率监控
- [ ] orphaned messages 定期清理机制

---

## 10. 变更记录

| 时间 | 变更内容 | 操作人 |
|------|---------|--------|
| 2026-04-30 05:45 | systemd 双阶段回滚演练完成（PASS） | agent |
| 2026-04-30 16:27 | 本文档从骨架补充为完整可靠性治理文档 | agent |

## 11. 相关文档

| 文档 | 关联章节 | 说明 |
|------|---------|------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | §4.2 运行态故障链、§8 巡检与恢复 | 故障定位表、恢复顺序 |
| [SECURITY.md](SECURITY.md) | §3 高风险动作、§8 已验证回退能力 | 高风险动作边界、回退层级总览 |

**关键 Runbook：**

| Runbook | 路径 | 用途 |
|---------|------|------|
| systemd 回滚演练 | [docs/plans/2026-04-30-systemd-rollback-drill-runbook.md](plans/2026-04-30-systemd-rollback-drill-runbook.md) | 双阶段回滚演练步骤 |
| 安全更新脚本 | [scripts/safe_update.sh](../scripts/safe_update.sh) | 带备份/token gate/rollback 的更新流程 |
| 健康检查 | [scripts/doctor_edict.sh](../scripts/doctor_edict.sh) | 全面巡检 (PASS/WARN/FAIL) |
