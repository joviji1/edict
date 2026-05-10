# 执行稿：治理文档体系从骨架升级为实质

**执行编号**: EXEC-20260430-001
**状态**: 进行中
**创建时间**: 2026-04-30 07:20（北京时间）
**负责人**: 玄成（Hermes）

## 1. 目标
把上轮落盘的治理文档骨架（ARCHITECTURE / RELIABILITY / SECURITY / FRONTEND）和状态层文件（feature-status.json / verification-ledger.json）从"有壳"升级为"有实质内容"。

## 2. 当前已完成
- [x] ARCHITECTURE.md：57 行 → 303 行。补了真实端口、PID、systemd 服务表、11 个 agent 映射、5 条数据流链路、巡检与恢复表、插件集成
- [x] RELIABILITY.md：46 行 → 258 行。补了服务拓扑、5 步最小检查清单（带可复制命令）、6 个已知问题记录、回滚能力现状、P0/P1/P2 待补清单
- [x] SECURITY.md：45 行 → 118 行。补了 5 项高风险动作的真实后果、确认模板、配置变更协议、回滚能力验证表
- [x] FRONTEND.md：26 行 → 106 行。补了 dashboard 关键页面表、5 个已知前后端断层、端口速查、问题分类

## 3. 当前已完成（续）
- [x] feature-status.json 已从 3 条扩到 5 条（新增 `EDICT-ATOMIC-TASK-UPDATE-001`、`EDICT-GOVERNANCE-DOCS-001`）
- [x] verification-ledger.json 已从 2 条扩到 3 条（新增本轮治理文档实质升级验证记录）
- [x] active 目录已创建首份执行稿，不再是空壳

## 4. 仍待补
- [ ] feature-status.json 继续扩面：当前 5 条，应补入 backend cutover、OpenClaw DM 等能力项
- [ ] verification-ledger.json 继续扩面：当前 3 条，应补入 systemd 回滚演练、atomic task update 运行态验证等更多运行态证据
- [ ] 把四份治理文档互相链接起来，形成可导航的文档网
- [ ] 至少 1 条高频 runbook 与 ARCHITECTURE/RELIABILITY 互相引用
- [ ] active 执行稿持续从进度主板主线抽取（本轮已新增 3 份：atomic-task-update / backend-cutover / feishu-dm-stability）

## 5. 验收口径
- 不是"文件存在"就算完成，要看内容是否基于真实运行态数据
- 每份文档必须有可执行的检查命令或具体路径，不能只有抽象描述
- 四份文档之间的交叉引用要通，不能各说各话

## 6. 风险
- 文档内容会随系统变化过时，需要定期 review
- 不要把文档写得过于详细以至于没人读，保持"够用、准确、可执行"
