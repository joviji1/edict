# 安全与动作边界

## 1. 目标
这里的安全不只指漏洞，也包括：**谁能动什么、什么动作必须先确认、怎样避免误操作扩大化。**

## 2. 当前安全边界

### 必须先确认的动作
- 对外发送内容（飞书/微信/邮件等）
- 群里发言 / 公开表态
- 高成本操作（配置变更、服务重启、session 重置）
- 明显有副作用的操作
- 删除、重启、强制切换、批量改写

### 默认可直接做的
- 只读查询（health check、日志查看、状态核查）
- 低风险核查（doctor 脚本、端口检查、任务计数核对）
- 文档整理与回写
- 基于现有边界的证据收集

## 3. 高风险动作清单与观测后果

### 3.1 Session Reset
- **动作**：`sessions.reset` 清空某 agent 某 channel 的会话历史
- **观测后果**：conversation context 全部丢失；reset 后 transcript 原路径重建为新 session header（仅剩 1 行 ~128 bytes），旧脏消息体被清空
- **观测实例**：2026-04-29 22:16 对 `taizi` 飞书直聊 session 执行 reset，旧 transcript 缩为单行 header，新 sessionId 切为 `c4d78b68-5c2b-4bf8-a813-c54a20b460b6`
- **必须动作**：reset 前备份原 transcript 到 `/root/.hermes/backups/`
- **验证口径**：reset 返回 `ok=true` + 新 sessionId 已生效 + 后续入站消息能命中新 session

### 3.2 Gateway Restart
- **动作**：`openclaw gateway restart`
- **观测后果**：PID 变化、短暂服务中断（秒级）、所有进行中的 dispatch 可能丢失
- **观测实例**：2026-04-29 21:56 重启后 PID 切到 `3485982`，原 524 快速失败转为 `accepted_but_no_final` / 120s timeout，说明现场有改善但 session 脏状态未清
- **必须动作**：记录重启前后 PID；重启后立即做健康检查
- **验证口径**：新 PID 已生效 + `/healthz` 返回 200 + 至少一条测试入站可 dispatch

### 3.3 Model / Provider 切换
- **动作**：修改 `openclaw.json` 中 `agents.defaults.model.primary` 或 `fallbacks`
- **观测后果**：可打断 fallback 链；provider key 过期直接 401
- **观测实例**：`windhub/gpt-5.4` key 过期 → 所有调用返回 `524 status code (no body)` 或 401；补 `longcat/LongCat-Flash-Chat` 为 fallback 后症状从"快速 524"转为"能进 session 但长跑无 final"
- **必须动作**：改前备份 `openclaw.json`；改后重启 gateway 验证
- **验证口径**：新 primary/fallback 已生效 + `/api/admin/health/deep` 返回 200 + 至少一轮完整 dispatch 无 `stopReason=error`

### 3.4 Systemd / Service 级改动
- **动作**：修改 `edict-dashboard.service` 或 `edict-loop.service` 的环境变量
- **观测后果**：写入模式切换（`dual` ↔ `json`）直接影响数据导出链路；回退窗口内可能有缓存滞后
- **观测实例**：2026-04-30 05:45 完成 systemd 回滚演练——先退 loop（去掉 `EDICT_ENABLE_BACKEND_EXPORT=true`）再退 dashboard（`dual` → `json`），回切后 `doctor_edict.sh` 结果 `PASS=31 WARN=1 FAIL=0`，所有 health endpoint 恢复 200
- **必须动作**：按 `docs/plans/2026-04-30-systemd-rollback-drill-runbook.md` 执行；变更前备份 unit 文件 + `live_status.json` + `tasks_source.json` + `tasks_backend_export_meta.json` + doctor/HTTP 基线
- **验证口径**：两个 service 均 `active` + doctor PASS + 所有 health endpoint 200 + 数据源计数对齐

### 3.5 旁路补偿链误报为主链修复完成
- **动作**：使用 `openclaw_feishu_relay.py` 的 `compensate` 模式
- **风险**：补偿链能注入消息到正确 session，但不等于主链（provider → gateway → session → dispatch → final reply → 投递）已修复
- **观测实例**：`sessionKey` 绑定正确后 probe 能进目标飞书直聊 session，但 assistant 回复 `stopReason=error` / `524 status code`，说明入口通了但上游模型仍故障
- **硬规则**：补偿链运行结果不得包装成"飞书直聊已恢复"；必须有独立的 dispatch → final reply → 投递证据才能下主链恢复结论

## 4. 确认模板格式

任何高风险动作执行前，应按以下格式确认：

```
### 动作确认：[动作名称]
- **动作对象**：[具体文件/服务/session]
- **变更前备份位置**：`/root/.hermes/backups/[备份路径]`
- **计划执行动作**：[具体命令或操作]
- **预期影响**：[什么会变、什么不会变]
- **回退方案**：[如何恢复到变更前状态]
- **验证口径**：[怎么判断变更成功]
- **主板回写**：变更完成后回写到 `docs/current-progress-board.md`
```

## 5. 配置变更协议

**四步走，缺一不可：**

1. **备份**：先备份到 `/root/.hermes/backups/`，命名格式 `[原文件名].before-[变更描述]-[YYYYMMDD-HHMMSS]`
2. **变更**：执行具体改动
3. **验证**：按对应验证口径确认变更生效且无副作用
4. **回写**：把变更内容、备份位置、验证结果写入 `docs/current-progress-board.md`

**备份目录**：`/root/.hermes/backups/`

已有备份样例：
- `openclaw.json.before-add-fallback-20260429-215201`
- `openclaw.json.before-add-second-group-sender-20260429-175730`
- `openclaw.json.before-session-scope-memos-20260429-173308`
- `rollback-drill-20260430-053642/`（含 unit 文件 + 数据文件 + 基线证据）
- `taizi-feishu-direct-*.before-session-reset-20260429-220356.jsonl`
- `config.yaml.20260425-155444.bak`
- `config-write-20260427-084519/`
- `config-write-20260427-090555/`

## 6. 硬规则
- 改配置前先备份
- 现场变更必须回写主板（`docs/current-progress-board.md`）
- 不把补偿链包装成主链已修好
- 不把不成熟判断包装成定论
- 不让外勤型执行体抢本体回话权

## 7. 文档与留痕要求

任何涉及风险边界的动作，至少应留下：
- 动作对象
- 变更前备份位置
- 执行动作
- 验证结果
- 是否已回退 / 可回退
- 主板回写位置

## 8. 当前已验证的回退能力

| 回退层级 | 工具/入口 | 最近演练 | 状态 |
|---------|----------|---------|------|
| systemd unit 环境变量 | `docs/plans/2026-04-30-systemd-rollback-drill-runbook.md` | 2026-04-30 05:45 | ✅ 已有实操证据 |
| openclaw.json 配置 | 手动还原备份 + gateway restart | 2026-04-29 21:56 | ✅ 已有实操证据 |
| session transcript | `sessions.reset` + 备份还原 | 2026-04-29 22:16 | ✅ 已有实操证据 |
| data/ 整包回滚 | 尚未演练 | — | ⚠️ 缺实操证据 |
| 源码级回滚 | 尚未演练 | — | ⚠️ 缺实操证据 |

## 9. 相关文档

| 文档 | 关联章节 | 说明 |
|------|---------|------|
| [RELIABILITY.md](RELIABILITY.md) | §5 已知问题、§7 回滚能力 | 已知故障记录、回退路径验证 |
| [ARCHITECTURE.md](ARCHITECTURE.md) | §4 关键链路 | 数据流链路、故障链、调度链 |

**关键 Runbook：**

| Runbook | 路径 | 用途 |
|---------|------|------|
| 飞书旁路补偿 | [docs/openclaw-feishu-bypass-compensation-runbook.md](openclaw-feishu-bypass-compensation-runbook.md) | feishu bypass 补偿流程（§3.5 关联） |
| systemd 回滚演练 | [docs/plans/2026-04-30-systemd-rollback-drill-runbook.md](plans/2026-04-30-systemd-rollback-drill-runbook.md) | 双阶段回滚演练步骤（§3.4 关联） |
