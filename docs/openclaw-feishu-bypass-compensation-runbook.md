# OpenClaw 飞书旁路补偿方案运行手册

更新时间：2026-04-29 21:14（北京时间）

## 1. 这是什么

这是一套给 **OpenClaw / taizi 飞书私聊链路不稳定** 时使用的可运营旁路补偿方案。

目标不是伪装成“主链已经完全修好”，而是把现场收成一条**人能稳定执行、能留痕、能回溯、能解释边界**的补偿路径。

当前落地脚本：

- `/root/.openclaw/workspace/edict/scripts/openclaw_feishu_relay.py`

运行日志目录：

- `/root/.openclaw/workspace/edict/logs/feishu-relay/`

---

## 2. 适用场景

只在下面这些场景用：

1. **飞书私聊 access event 已到，但 live message event 没稳定进入 taizi handler**
2. 用户明确表示“阿爪没收到 / 没回 / 回复丢了”
3. 需要人工把一条消息补喂回 taizi，或者至少先把文本补送达给对方
4. 主链还没修好，但业务上不能继续空等

不适用场景：

1. 主链正常，只是回复质量差
2. 群聊上下文串线，实际是会话 scope 问题
3. 需要真正证明“taizi 已处理并产出了这条回复”——这套方案默认只能保证**补处理入口**或**补发送入口**，不能自动把两者混成一个已验收结论

---

## 3. 现阶段边界

先说结论：

- **内部入口有**：Gateway RPC `agent`
- **自动回投闭环未坐实**：当前不能把它当成“100% 自动回到飞书私聊”的正式结论
- **因此正式运营口径必须拆成两段**：
  - **补处理**：往 taizi 注入一轮文本
  - **补送达**：必要时手工旁路发飞书文本

换句话说：

- `probe` / `compensate` 里的 `agent` 步骤，解决的是“让 taizi 至少有机会处理”
- `send` 步骤，解决的是“让用户至少能收到一条明确反馈”

不要把“发送成功”包装成“taizi 已真实处理原消息”。这俩不是一回事。

---

## 4. 模式说明

### 4.1 `probe`

用途：

- 只验证内部 `agent` 入口是否还能打进去
- 适合低风险探针、验收、只想试入口不想直接人工补发时使用

特点：

- 会向 taizi 注入一轮文本
- 默认不做手工飞书补发
- 会写 JSONL 留痕

示例：

```bash
python3 /root/.openclaw/workspace/edict/scripts/openclaw_feishu_relay.py \
  probe \
  --message '系统旁路验收：请只回复“入口OK”' \
  --session-id 89f35078-bb0d-49c2-96bf-e250b69af111
```

---

### 4.2 `send`

用途：

- 直接手工补发飞书文本
- 用于“业务上先把话送到人，再说后面的处理链”

特点：

- 不进入 taizi 处理链
- 只是直发文本
- 最适合故障告知、临时说明、人工兜底

示例：

```bash
python3 /root/.openclaw/workspace/edict/scripts/openclaw_feishu_relay.py \
  send \
  --target user:ou_ed2187f2ad27e0b7876913371e72c06a \
  --text '阿爪刚才私聊链路异常，这条先人工补送达；主链仍在排查。'
```

---

### 4.3 `compensate`

用途：

- 正式运营补偿流程
- 先试图把文本补喂给 taizi
- 如果短时间内拿不到 final 成功，再手工补发给飞书

特点：

- 是当前最接近“可运营”的正式模式
- 会把两步都留痕
- 不会硬把“主链处理成功”和“人工补发成功”混成一个概念

示例：

```bash
python3 /root/.openclaw/workspace/edict/scripts/openclaw_feishu_relay.py \
  compensate \
  --message '用户原始问题：你看一下服务器现在的运行状况怎么样了' \
  --fallback-text '阿爪刚才私聊入口不稳定，这条先人工补送达：已收到你的问题，正在继续排查并补结果。' \
  --session-id 89f35078-bb0d-49c2-96bf-e250b69af111 \
  --source-message-id om_xxx
```

---

## 5. 推荐操作流程

### 5.1 最稳流程

1. **先查现场**
   - 原消息 id
   - 目标用户 / chat id
   - 是否已有对应 taizi session
2. **先 dry-run**
3. **再跑 `compensate`**
4. **看 JSON 输出和日志留痕**
5. 必要时再去 live log / session transcript 补证据

---

### 5.2 推荐命令模板

先预演：

```bash
python3 /root/.openclaw/workspace/edict/scripts/openclaw_feishu_relay.py \
  compensate \
  --message '用户原始问题：……' \
  --fallback-text '阿爪刚才私聊入口不稳定，这条先人工补送达：……' \
  --session-id 89f35078-bb0d-49c2-96bf-e250b69af111 \
  --source-message-id om_xxx \
  --dry-run
```

确认命令无误后正式执行：

```bash
python3 /root/.openclaw/workspace/edict/scripts/openclaw_feishu_relay.py \
  compensate \
  --message '用户原始问题：……' \
  --fallback-text '阿爪刚才私聊入口不稳定，这条先人工补送达：……' \
  --session-id 89f35078-bb0d-49c2-96bf-e250b69af111 \
  --source-message-id om_xxx
```

---

## 6. 返回状态怎么理解

### `dry_run`
只是预演，没有真正执行。

### `accepted_only`
`agent` 入口被网关接受了，但没等待 final。

### `accepted_but_no_final`
`agent` 入口大概率已接收，但在等待 final 的窗口里没有成功收回来。当前现场要把这类状态当成：

- **补处理入口命中了**
- **但不能宣称自动回投成功**

### `manual_sent`
手工补发成功。

### `agent_then_manual_send`
先补喂 taizi，再手工补发成功。当前这是最实用的运营闭环状态。

### `compensation_failed`
补处理没收住，手工补发也失败。此时不能再假装现场已兜住，必须升级处理。

---

## 7. 留痕与回溯

每次执行都会写到：

- `/root/.openclaw/workspace/edict/logs/feishu-relay/YYYY-MM-DD.jsonl`

至少会留下这些字段：

- 时间
- 模式
- sessionId
- target
- sourceMessageId（如果传了）
- agent 命令
- send 命令
- stdout / stderr
- 最终状态

这意味着后面回溯时，可以明确区分：

- 是不是试过补处理
- 是不是做过人工补发
- 人工补发发给了谁
- 当时返回的到底是 timeout、accepted、还是 send error

---

## 8. 风险提醒

1. **不要把人工补发伪装成 taizi 原始回复**
2. **不要默认 `expect-final` 就能收回 final**，当前现场已经证明它容易卡成 timeout
3. **不要把 send 成功当成问题已修复**
4. **不要一次连打很多 probe**，容易给 taizi 堆更多 running 状态
5. 当前这套是**旁路补偿方案**，不是主链修复结论

---

## 9. 当前推荐口径

对内：

> 现已具备可运营旁路补偿路径：`agent` 负责补处理入口，`send` 负责补送达入口，`compensate` 负责正式两段式补偿；但自动回投闭环尚未验收通过，仍按“补偿方案”而非“主链修复”管理。

对外（如果需要人工说明）：

> 刚才私聊链路有波动，这条先补送达给你；主链仍在排查中。

---

## 10. 配套模板

已补充值班模板与标准补发话术：

- `/root/.openclaw/workspace/edict/docs/openclaw-feishu-bypass-duty-template.md`

值班时优先按该模板收集现场、预演、执行补偿、记录状态与回写主板。

---

## 11. 当前默认值

脚本当前内置默认值：

- `agentId=taizi`
- `sessionId=89f35078-bb0d-49c2-96bf-e250b69af111`
- `target=user:ou_ed2187f2ad27e0b7876913371e72c06a`
- `accountId=default`

这些默认值是为了当前现场先能跑起来，不代表未来所有对象都该复用同一组值。若切换补偿对象，必须显式改 `sessionId / target / source-message-id`。
