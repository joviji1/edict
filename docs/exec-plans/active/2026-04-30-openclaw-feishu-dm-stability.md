# 执行稿：OpenClaw feishu DM 稳定性收口

**执行编号**: EXEC-20260428-003
**状态**: 进行中
**创建时间**: 2026-04-30 16:45（北京时间）
**负责人**: 玄成（Hermes）

## 1. 目标
把 OpenClaw taizi 飞书直连 DM 从"完全断链 / 持续 524"收敛为"基本收口 / 转监控"状态，确保消息主链可稳定闭环（入站 → 派发 → 回复完成）。

## 2. 当前已完成

### 2.1 止血动作
- [x] agent 本地 provider 固定层清理：`custom-ai-dcvx-cn`、`faker` 已从各 agent `models.json` 清除
- [x] session 固定模型元数据批量去钉：`modelProvider`、`model`、`contextTokens`、`systemPromptReport.*` 已清空
- [x] 全局默认已切到：`agents.defaults.model.primary = windhub/gpt-5.4`、`contextTokens = 200000`
- [x] fallback 已恢复：`agents.defaults.model.fallbacks = ["longcat/LongCat-Flash-Chat"]`

### 2.2 旁路补偿方案
- [x] 补投递入口脚本：`scripts/openclaw_feishu_relay.py`（支持 probe/send/compensate 三种模式）
- [x] sessionKey 优先绑定：默认直指 `agent:taizi:feishu:direct:ou_ed2187f2ad27e0b7876913371e72c06a`
- [x] 运行手册：`docs/openclaw-feishu-bypass-compensation-runbook.md`
- [x] 值班模板：`docs/openclaw-feishu-bypass-duty-template.md`
- [x] 运行日志目录：`logs/feishu-relay/`

### 2.3 session 定向修复
- [x] taizi direct session 已多次定向旋转（旧脏 session → 新 session）
- [x] menxia:main 重入止血：dashboard 侧已补 main-session guard，不再重复投递
- [x] shangshu:main 重入止血：dashboard 侧已补同级 guard + 定点 session recovery
- [x] 飞书群会话隔离：两个人机共同飞书群已显式按发送人拆会话（`groupSessionScope = "group_sender"`）

### 2.4 真实闭环样本（曾拿到）
- [x] 重启后多次拿到 `p2p chat entered → received message → dispatching to agent → dispatch complete` 完整闭环
- [x] 旁路补偿方案 sessionKey 绑定验证：probe 已真实落在目标飞书直聊 transcript

## 3. 仍待补

- [ ] session 长跑问题：taizi direct session 反复出现长跑/持锁不释放，导致 `dispatch complete` 不稳定
- [ ] windhub/gpt-5.4 上游 524 系统性错误仍在发生（`fallbackConfigured=true` 后表象从"快速 524"转为"长跑无 final"）
- [ ] `lane wait exceeded` 并发压力信号仍需持续盯防
- [ ] `menxia:main` 的历史 lane wait / self-lock 噪声仍需并行盯防
- [ ] 主链稳定性：需要持续监控不再出现 `dispatch complete` 中断的情况
- [ ] 自动闭环升级：旁路补偿方案当前是补偿链路，不是主链修复；要升级为自动闭环必须另外补证据

## 4. 验收口径

- `p2p chat entered → received message → dispatching to agent → dispatch complete` 四段全链路在多个观测窗口持续出现
- 不是"重启后有一次闭环"就算恢复，要看连续稳定运行
- 当前已从 blocker 降级到"基本收口 / 转监控"，但监控不能撤
- 后续只要出现新 ingress 但没有 completion，就要立即把状态重新打回未收口 / blocker

## 5. 风险

- windhub/gpt-5.4 上游 524 属于系统性问题，非本方可独立修复
- 无实质可用的模型 fallback（`longcat/LongCat-Flash-Chat` 已配置但未观察到真实 fallback 成功样本）
- taizi direct session 长跑 + live gateway 持锁是当前主脏点，需要 Gateway 侧或 session 管理机制层面的改进
- 旁路补偿方案是人工介入链路，不能误报成"自动闭环已恢复"

## 6. 证据引用

- 进度主板 §0.1：`docs/current-progress-board.md` 第 27–43 行
- 进度主板 §4.2：`docs/current-progress-board.md` 第 932–934 行
- 进度主板 §4.2.4：`docs/current-progress-board.md` 第 1018–1034 行
- 进度主板 §4.2.5：`docs/current-progress-board.md` 第 1036–1054 行
- 进度主板 §4.3：`docs/current-progress-board.md` 第 1056–1059 行
- 进度主板 §4.4：`docs/current-progress-board.md` 第 1090–1123 行
- 进度主板 §7：`docs/current-progress-board.md` 第 1168–1242 行
- 旁路补偿运行手册：`docs/openclaw-feishu-bypass-compensation-runbook.md`
