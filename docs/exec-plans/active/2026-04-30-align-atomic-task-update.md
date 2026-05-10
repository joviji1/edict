# 执行稿：align-atomic-task-update 原子更新扩面

**执行编号**: EXEC-20260429-002
**状态**: 进行中
**创建时间**: 2026-04-30 16:45（北京时间）
**负责人**: 阿爪（执行）/ 玄成（验收）

## 1. 目标
把 `dashboard/server.py` 中剩余仍走 `load_tasks() + save_tasks()` 的写口，逐步迁入 `modify_task()` / `modify_tasks()` 原子更新框架，减少 TOCTOU 竞争、并发写冲突与状态不一致风险。

## 2. 当前已完成

### 2.1 第一轮收口（2026-04-29）
- [x] `handle_archive_task` → 已迁入 `modify_task()` / `modify_tasks()`
- [x] `handle_review_action` → 已迁入 `modify_task()`（状态推进、pending_confirm 清理、gate_checks 回写、flow_log 追加）
- [x] `handle_repair_flow_order` → 已迁入 `modify_tasks()`
- [x] `handle_create_task` JSON fallback 写链 → 已迁入 `modify_tasks()`
- [x] 代码提交：`53bf28e`（`Expand atomic task updates in dashboard server`）
- [x] 语法校验通过：`python3 -m py_compile dashboard/server.py`

### 2.2 第二轮收口（2026-04-30）
- [x] `adopt_court_conclusion` → 已迁入 `modify_tasks()`（todo 追加、COURT-* 任务插入、updatedAt 回写）
- [x] `_startup_recover_queued_dispatches` → 已按"两段式"拆开（先 `modify_tasks()` 做原子状态修正，写后再执行 `dispatch_for_state()`）
- [x] 运行态验证已通过：最小 Python 运行态脚本实跑，不只是 py_compile
- [x] 副作用已移出写锁：`dispatch_for_state()` 不再塞在 `modify_tasks()` 闭包内

### 2.3 backend create 一致性前推（2026-04-30）
- [x] `handle_create_task` 去掉了固定传 `legacy_id=f'JJC-{today}-PENDING'` 的写法
- [x] 改为先基于当前任务快照计算 `candidate_task_id`，backend create 直接带真实当日流水号
- [x] 新增 `_next_legacy_task_id(tasks, today, preferred=None)` 统一候选号生成逻辑
- [x] fallback 回退链：backend 失败且候选号已被占用时，本地 `modify_tasks()` 会重新计算实际可用号
- [x] 运行态验证：dual/backend 成功链与 fallback 回退链均已实跑通过

## 3. 仍待补

- [ ] `handle_scheduler_scan` 相关写链：扫描后仍残留的 `load_tasks() + save_tasks()` 口之一，需评估是否涉及写操作
- [ ] 更厚的自然业务样本验证：当前验证主要基于最小运行态脚本与 probe，需等待真实任务流转产生自然样本
- [ ] backend create 主链完整验收：legacy_id / 当日流水号口径已收紧，但更复杂并发场景下序号漂移/重复号仍需自然样本验证
- [ ] 创建任务路径在 dual/api 模式下 backend create 与本地 JSON 流水号的一致性仍需后续单独收口
- [ ] 不得把通知、派发、恢复性外部动作粗暴塞进 `modify_tasks()` / `modify_task()` 闭包（持续遵守）

## 4. 验收口径

- 不是"改了代码"就算完成，必须有运行态证据（不只是 py_compile）
- 至少给出 1 次真实改动后的运行态证据
- 至少明确"改了哪个函数、去掉了哪段 `load_tasks()+save_tasks()`、副作用如何移到写后"
- 若动到启动恢复/派发链，必须额外说明：有没有新增重复派发、锁等待、状态错乱风险
- 自然样本厚度必须达到"不只是 probe 证据"的程度

## 5. 风险

- 两段式拆分后，若 `modify_tasks()` 闭包外的 `dispatch_for_state()` 出现异常，可能导致状态已写但派发未执行
- backend create 与本地 JSON fallback 的并发竞态在高负载场景下可能暴露新问题
- 不允许把"fallback 已原子化"误报成"backend create 也完全收口"

## 6. 证据引用

- 进度主板 §2.5：`docs/current-progress-board.md` 第 418–500 行
- 进度主板 §2.5.1：`docs/current-progress-board.md` 第 501–528 行
- 进度主板 §2.5.2：`docs/current-progress-board.md` 第 530–564 行
- 进度主板 §2.5.3：`docs/current-progress-board.md` 第 566–595 行
- 代码提交：`53bf28e`
