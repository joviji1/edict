# edict closeout

更新时间：2026-04-21 15:20（北京时间）

## 1. 当前主线状态

### 1.1 已确认落地
- React 看板已作为当前运行态前端入口；`dashboard/server.py` 实际提供 `dashboard/dist/` 构建产物，README/截图说明已同步到该现实。
- 看板当前按 12 个功能面板口径维护，README / ROADMAP 已写明 `待批专面板 / 急递铺 / 国史馆` 已进入真实运行态口径。
- `急递铺`、`国史馆`、`待批专面板` 的 README / ROADMAP 现实同步已完成，当前文档口径与代码口径基本一致。
- 模型配置面板当前并不是直接读取某个 `config.yaml`；它读取 `data/agent_config.json`，其中 `knownModels` / `defaultModel` 由 `scripts/sync_agent_config.py` 从 `/root/.openclaw/openclaw.json` 同步生成。

### 1.2 本轮模型配置核实结论
- 当前 OpenClaw 主配置文件：`/root/.openclaw/openclaw.json`
- 当前默认主模型：`longcat/LongCat-Flash-Chat`
- 当前默认回退模型：`faker/gpt-5.4`
- 当前 `agents.defaults.models` 已登记：
  - `longcat/LongCat-Flash-Chat`
  - `faker/gpt-5.4`
- 当前 `models.providers` 已配置 provider：
  - `longcat`
  - `faker`
- `scripts/sync_agent_config.py` 会：
  - 内置一批 `KNOWN_MODELS`
  - 再把 `openclaw.json` 里的 `defaults.model`、`defaults.models`、各 agent model、各 provider models` 合并进 `knownModels`
  - `agent_config.json` 中每个 agent 的当前 `model` 取自 `agents.list[*].model`，若该 agent 未单独覆写，则回落到 `agents.defaults.model.primary`
- `edict/frontend/src/components/ModelConfig.tsx` 优先读取 `agentConfig.knownModels`；只有接口没给值时才退回前端硬编码 `FALLBACK_MODELS`
- `dashboard/server.py::POST /api/set-model` 会把变更写入 `data/pending_model_changes.json`，异步执行 `scripts/apply_model_changes.py`，随后再跑 `scripts/sync_agent_config.py`
- `scripts/apply_model_changes.py` 会：
  - 备份 `/root/.openclaw/openclaw.json`
  - 把目标 agent 的 `model` 写入 `agents.list[*].model`（若设置值等于默认主模型，则删除该字段以回落默认）
  - 执行 `openclaw gateway restart`
  - 记录 `data/last_model_change_result.json` 与 `data/model_change_log.json`

### 1.3 当前实际数据快照
- 变更前：
  - `/root/.openclaw/openclaw.json` 中 `agents.defaults.model.primary = longcat/LongCat-Flash-Chat`
  - `taizi / zhongshu / menxia / shangshu` 等核心 agent 默认未单独写 `model` 字段，因此实际继承默认主模型
- 本轮已做一次真实链路验证：将 `taizi` 的 pending model change 写为 `faker/gpt-5.4` 后执行 `scripts/apply_model_changes.py`
  - `apply_model_changes.py` 日志显示：`taizi: longcat/LongCat-Flash-Chat → faker/gpt-5.4`
  - 同一脚本日志显示：`gateway restart rc=0`
  - `data/last_model_change_result.json` 写入：`gatewayRestarted = true`、`rolledBack = false`
- 随后重新执行 `scripts/sync_agent_config.py` 并核对：
  - `/root/.openclaw/openclaw.json` 中 `taizi` 条目最终**没有**保留单独 `model` 字段
  - `data/agent_config.json` 中 `taizi.model/defaultModel` 仍显示 `longcat/LongCat-Flash-Chat`
- 结论：**“写入 pending 变更 → 执行 apply_model_changes.py → 重启 gateway” 这条运行链路真实存在且本机返回成功；但本轮对 `taizi -> faker/gpt-5.4` 的实际配置写入结果与预期不一致，最终没有在 `openclaw.json` / `agent_config.json` 中保留该 agent 级模型变更。**
- 因此当前更准确的判断是：
  - “应用后会触发 gateway restart” 已拿到运行态证据
  - “每个 Agent 独立切换后会稳定持久写入并在面板反映” 仍需继续排查/修复，不能仅凭 UI 提示视为完全闭环
- 初步根因假设：`apply_model_changes.py` 的离线单测逻辑看起来能正确把 `agents.list[*].model` 写入 JSON；但生产现场 `openclaw.json` 最终仍无 `taizi.model`，说明**更可能是链路后段有别的进程/逻辑在 gateway restart 前后把 agent 级 model 覆盖回默认值**，而不是 `sync_agent_config.py` 只读同步本身直接改写了配置。

## 2. 关键文件定位
- 看板后端接口：`dashboard/server.py`
  - `GET /api/agent-config`
  - `POST /api/set-model`
- 模型配置前端：`edict/frontend/src/components/ModelConfig.tsx`
- 同步逻辑：`scripts/sync_agent_config.py`
- 应用模型变更：`scripts/apply_model_changes.py`
- 运行时主配置：`/root/.openclaw/openclaw.json`
- 面板消费数据：`data/agent_config.json`

## 3. 关于“是否可沿用当前 config.yaml”的明确结论
- **结论：不能表述为“沿用当前 config.yaml”。**
- 原因：edict 模型配置链路当前实际不依赖 repo 内某个 `config.yaml`；它依赖的是 `/root/.openclaw/openclaw.json -> scripts/sync_agent_config.py -> data/agent_config.json -> React ModelConfig`。
- 若后续文档要写准：
  - 应写“沿用当前 OpenClaw 运行配置（`/root/.openclaw/openclaw.json`）”
  - 不应写成“沿用当前 config.yaml”

## 4. 待继续推进事项
1. 扫描 README / ROADMAP / docs / deliverables 中仍把模型配置写成 `config.yaml` 来源的描述，并改成 `openclaw.json -> agent_config.json` 真实链路。
2. 继续做 `reality-sync-next-round`，重点扫：
   - deliverables 中仍可能残留的旧前端 / 旧模型链路表述
   - README / ROADMAP / 前端提示里关于模型切换“自动重启 Gateway（约5秒）”目前仅见 UI 与接口口径，若要写成运行态事实，仍应补 runtime 级验证证据
3. 如用户明确要把 edict 实际运行模型切到 gpt-5.4，再进入：
   - 调用 `/api/set-model` 或写 pending model change
   - 校验 `apply_model_changes.py`
   - 校验 `/root/.openclaw/openclaw.json` 与 `data/agent_config.json` 是否同步变更
   - 这是配置变更动作，不是本轮只读核实结论的一部分

## 5. 下一次中断后建议入口
- 先读本文件
- 再读：`docs/governance-upgrade-map.md`
- 再执行 reality sync 扫描关键词：
  - `config.yaml`
  - `openclaw.json`
  - `agent_config.json`
  - `LongCat`
  - `gpt-5.4`
  - `待批专面板`
  - `急递铺`
  - `国史馆`
