# JJC-20260412-001：从 wanikua/danghuangshang 到 edict 的隔离实验 / 后续吸收队列

更新时间：2026-05-08 23:08 CST

## 判断口径

先切低风险、可隔离、可回滚、不直接改生产状态的部分。第一阶段只允许：只读诊断、生成备份、dry-run/预检/测试、草稿化分类。不开放自动重启、自动回滚、自动写库、直接改任务状态。

同时补一条现场约束：当前 edict 运行态健康，dashboard / backend / deep health 均为 200，backend / `tasks_source.json` / `live_status.json` 三面一致，均为 18 条、状态 `Done=3 / Cancelled=15`。所以本轮隔离实验不该碰在线任务状态，优先做只读、离线、旁路验证。

## 隔离实验 / 后续吸收队列清单

| 切口 | 实验目标 | 风险 | 验证 | 吸收落点 |
|---|---|---|---|---|
| doctor 诊断快照 | 把 danghuangshang 里“看现场/判健康”的思路，先转成 edict 的只读诊断快照：服务存活、关键端口、Redis/Postgres 可达、任务停滞摘要、最近错误摘要。 | 低。只读，不改任务、不写库、不重启；风险主要是误报或输出太吵。 | 在隔离目录或临时输出文件跑一次；确认不触发 systemctl restart、不执行 UPDATE/DELETE/INSERT；输出能对应到 dashboard/backend/Redis 三面事实。 | 后续吸收到 `doctor_edict` / dashboard 运维检查入口，作为人工判断前置证据，不直接驱动处置动作。 |
| memory_backup 备份前置 | 把“变更前先留快照”的能力固化成标准前置动作：配置、任务源、关键状态摘要、脚本版本清单先备份。 | 低。只生成备份文件；风险是备份范围不足、泄漏敏感字段、占用磁盘。 | 生成一次备份并核对文件存在、可读、敏感字段脱敏为 `[REDACTED]`；确认不覆盖生产配置、不恢复、不清理旧数据。 | 后续吸收到 safe_update / 变更执行前置钩子；作为每次人工批准前的固定证据包。 |
| safe_update 的 plan → prepare → test | 只吸收安全更新流程的前三段：plan 生成计划、prepare 做备份/依赖/差异预检、test 做构建或脚本级验证。暂不开放 apply/restart/rollback 自动执行。 | 中低。dry-run 和测试本身低风险；风险在于脚本误把 dry-run 变成 apply，或隐藏触发重启/写库。 | 用 `--dry-run` / 临时 worktree / 隔离环境跑；审计命令日志，确认没有 restart、rollback、数据库写入和任务状态修改；测试结果不能替代真实交付，只作为准入信号。 | 后续吸收到 edict 变更治理流程：先形成“计划 + 备份 + 验证结果”，再由人工确认是否进入 apply。 |
| autopsy / stalled 分类草稿 | 把失败复盘、停滞任务分类、建议动作先做成草稿：只产出分类、原因假设、推荐人工动作，不自动写回 backend。 | 中低。不改状态；风险是分类误导、重复扫描造成噪声、把草稿误当结论。 | 选一批历史停滞任务离线跑；核对输出是否包含证据来源、置信度和“不自动处置”标记；确认不调用任务状态写回、不发布 Redis 变更事件。 | 后续吸收到 PendingConfirm / 人工审批流，作为“建议处置草稿”，由人或审批链决定是否写回。 |

## 现有落点证据

### 1. doctor 诊断快照
- 当前已有脚本：`scripts/doctor_edict.sh`
- 当前可直接验证的只读信号：
  - `http://127.0.0.1:7892/healthz`
  - `http://127.0.0.1:18000/health`
  - `http://127.0.0.1:18000/api/admin/health/deep`
  - backend / tasks_source / live_status 三面一致性
- 说明：这个切口已经有现成运行基础，最适合先做“统一输出格式”和“增加 stalled 摘要”的隔离增强。

### 2. memory_backup 备份前置
- 当前已有脚本：`scripts/memory_backup.sh`
- 已覆盖对象：
  - `data/agent_memory`
  - `data/task_memory`
  - `data/shared_memory.json`
  - `data/tasks_source.json`
  - `data/tasks.json`
  - `~/.openclaw/openclaw.json`
  - `~/.openclaw/workspace`（带递归保护）
- 说明：这个切口不是从零开始，适合直接升级成“实验前固定动作”。

### 3. safe_update 的 plan → prepare → test
- 当前已有脚本：`scripts/safe_update.sh`
- 当前已实现阶段：
  - `plan`：只生成计划与风险提示
  - `prepare`：备份 + JSON 校验 + `doctor_edict.sh`
  - `test`：`py_compile` + `pytest`
  - `apply`：低风险 dry-run / 依赖检查
  - `restart/rollback`：有确认 token 才允许执行
- 说明：前三段已经天然适合做隔离实验，不需要先发明新流程，只需要收紧边界，明确“本轮只允许 plan/prepare/test”。

### 4. autopsy / stalled 分类草稿
- 当前已有落点：`scripts/kanban_update_legacy.py`
- 现有能力包括：
  - `cmd_autopsy(task_id, reason='')`
  - `_infer_stall_reason(task)`
  - `STALL_REASON_LABELS`
  - 自动生成 `data/autopsy/` 报告
- 风险点：当前实现会回写任务 `autopsy` 字段、`_scheduler`、`flow_log`、`updatedAt`
- 说明：所以这个切口**不能直接拿现实现网跑**，要先做一层隔离版，只产出草稿文件，不回写任务。

## 下一步可执行版（按优先级）

### P1：doctor 诊断快照实验
目标：产出一个只读版诊断快照样例。

建议动作：
1. 复用 `doctor_edict.sh` + health 接口 + 三面一致性检查。
2. 输出到隔离目录，例如：`isolation/danghuangshang/doctor-snapshots/`。
3. 先固定一个最小 JSON/Markdown 结构：
   - 时间
   - 服务健康
   - 三面任务数
   - stalled/残留摘要
   - 最近错误摘要
4. 不接 dashboard 按钮，不接自动修复。

验收：
- 输出文件存在。
- 无服务重启。
- 无数据写入。
- 能被人工快速读懂。

### P2：memory_backup 备份前置实验
目标：把备份动作从“脚本存在”升级成“实验前固定前置”。

建议动作：
1. 包一层实验入口脚本，只调用 `memory_backup.sh`。
2. 补一份 manifest：列出本次备份包含哪些目录/文件。
3. 对敏感字段做脱敏展示，不把明文凭据直接带进实验产物。

验收：
- 备份目录生成成功。
- manifest 可读。
- 不修改原始配置。

### P3：safe_update plan → prepare → test 实验
目标：验证“安全更新前三段”能独立跑通，且不越界到 restart/rollback。

建议动作：
1. 只允许执行：
   - `scripts/safe_update.sh plan`
   - `scripts/safe_update.sh prepare`
   - `scripts/safe_update.sh test`
2. 不执行 `apply/restart/rollback`。
3. 收集 run_dir 内的 `plan.json`、`safe_update.log`、测试输出。
4. 形成一份“变更前证据包样例”。

验收：
- `plan.json` 生成。
- `prepare` 成功完成备份与 doctor。
- `test` 成功跑完编译/测试。
- 无服务重启。
- 无数据库写入。

### P4：autopsy / stalled 草稿实验
目标：做一版“不回写任务”的 autopsy 草稿器。

建议动作：
1. 不直接调用现有 `cmd_autopsy()` 作用于在线任务。
2. 先做一个旁路版本：
   - 输入：历史任务快照 / 样本 JSON
   - 输出：Markdown 或 JSON 草稿
3. 只复用分类逻辑：
   - `STALL_REASON_LABELS`
   - `_infer_stall_reason(task)` 的判断思路
4. 不写 `tasks_source.json`
5. 不写 backend
6. 不发布 Redis 事件

验收：
- 产出草稿文件。
- 草稿含证据来源、分类、置信度、建议动作。
- 在线任务状态完全不变。

## 第一阶段不碰

- GenericAgent 主链接入。
- 自动重启。
- 自动回滚。
- 自动写库。
- 直接修改任务状态。
- 自动发布 Redis 状态变更事件。
- 直接把 `kanban_update_legacy.py cmd_autopsy()` 对在线任务开跑。

## 推荐顺序

1. doctor 诊断快照。
2. memory_backup 备份前置。
3. safe_update 的 plan → prepare → test。
4. autopsy / stalled 分类草稿。
5. 四项都跑出隔离样例后，再讨论吸收到正式主链。

## 当前总判断

这四个切口里，**最容易马上起实验的是前三个**，因为本机已有 `doctor_edict.sh`、`memory_backup.sh`、`safe_update.sh` 真实脚本基础；**最该谨慎的是 autopsy**，因为现有实现带回写副作用，必须先拆旁路版。

一句话：先做看得清、备得住、试得动、写草稿的部分；别一上来碰自动改状态和自动重启。
