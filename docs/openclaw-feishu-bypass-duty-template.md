# OpenClaw 飞书旁路补偿值班模板

更新时间：2026-04-29 21:20（北京时间）

## 1. 适用条件

当出现下面任一情况时，值班人可直接套这个模板：

- 用户反馈：阿爪没收到 / 没回复 / 回复丢了
- 已确认是飞书私聊链路波动
- 需要先把消息补喂 taizi，或至少先把话补送达给用户

---

## 2. 值班操作单

### Step 1：补齐现场信息

按下面表填：

- 原消息时间：
- 原消息 message_id：
- 目标对象：
- 目标 target（如 `user:ou_xxx`）：
- 对应 taizi sessionId：
- 原始问题原文：
- 本轮值班人：
- 是否已做 dry-run：是 / 否

---

### Step 2：先 dry-run 预演

```bash
python3 /root/.openclaw/workspace/edict/scripts/openclaw_feishu_relay.py \
  compensate \
  --message '用户原始问题：……' \
  --fallback-text '阿爪刚才私聊入口不稳定，这条先人工补送达：……' \
  --session-id <SESSION_ID> \
  --target <TARGET> \
  --source-message-id <MESSAGE_ID> \
  --dry-run
```

检查点：

- sessionId 对不对
- target 对不对
- fallback-text 有没有说人话
- 有没有误把“人工补发”写成“阿爪已处理完成”

---

### Step 3：正式补偿

```bash
python3 /root/.openclaw/workspace/edict/scripts/openclaw_feishu_relay.py \
  compensate \
  --message '用户原始问题：……' \
  --fallback-text '阿爪刚才私聊入口不稳定，这条先人工补送达：……' \
  --session-id <SESSION_ID> \
  --target <TARGET> \
  --source-message-id <MESSAGE_ID>
```

---

### Step 4：记结果

把返回 JSON 里的这些字段记下来：

- `status`
- `sessionId`
- `target`
- `sourceMessageId`
- `logPath`
- `agentStatus`（如果有）

并同步回：

- `/root/.openclaw/workspace/edict/docs/current-progress-board.md`

---

## 3. 状态判读

### `agent_final_only`
- taizi 入口成功，且收到了 final
- 这是最好结果
- 但仍建议补查一下用户端是否真看到消息

### `agent_then_manual_send`
- taizi 补处理试过了
- 最终靠人工补发送达兜住
- 当前最实用，也最符合现状

### `accepted_only`
- taizi 入口被接受
- 但没有 final
- 不能当成已闭环

### `accepted_but_no_final`
- 和上面一样，但更明确说明是超时没等回 final
- 应按“未证明自动回投成功”处理

### `manual_sent`
- 只做了人工补发
- 不代表 taizi 处理过原消息

### `compensation_failed`
- taizi 没收住，人工补发也失败
- 需要升级处理，不能继续装作已送达

---

## 4. 标准补发话术模板

## 4.1 通用兜底版

```text
阿爪刚才私聊入口有波动，这条先人工补送达给你：
【这里补正文】
主链仍在排查中。
```

### 4.2 已收到问题，稍后补结果

```text
阿爪刚才私聊入口有波动，这条先人工补送达：已收到你的问题，正在继续排查并补结果。
```

### 4.3 只做故障告知

```text
阿爪刚才私聊链路不稳定，你前一条消息可能没有完整进入处理链。这条先人工补送达，主链仍在排查中。
```

### 4.4 已有人工结论，需要先送达

```text
阿爪刚才私聊入口有波动，这条先人工补送达结论：
【这里写结论】
后续主链恢复后再继续归并。
```

### 4.5 明确不冒充自动回复

```text
这条是人工补送达，不代表阿爪刚才已经完整处理到上一条原消息；主链还在继续排查。
```

---

## 5. 值班禁忌

- 不要把人工补发写成“阿爪已正常回复”
- 不要把 send 成功写成“问题已修复”
- 不要省略 `source-message-id`
- 不要做完补偿不回写主板
- 不要在没核对 target/sessionId 的情况下直接发

---

## 6. 值班汇报模板

```text
【旁路补偿执行】
- 时间：
- message_id：
- target：
- sessionId：
- 执行模式：probe / send / compensate
- 返回状态：
- 是否已人工补发送达：是 / 否
- 日志：
- 备注风险：
```
