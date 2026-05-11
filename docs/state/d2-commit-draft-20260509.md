# D2 commit 草稿（2026-05-09 15:00）

## 推荐提交标题

```text
docs(D2): 回正主线收口长文口径
```

## 推荐提交正文

```text
- 回正文档入口与主线收口长文口径，统一 README、closeout、治理映射、review notes 与调度架构说明
- 明确 backend dual/export 处于生产过渡态，前台关键写链 smoke 与 systemd 最小回滚演练已有实操证据
- 单列 D2 长文回正包边界，主板继续作为过程挂账，不并入本次正式定稿面

验证：
- git diff --stat -- .gitignore README.md docs/closeout.md docs/governance-upgrade-map.md docs/review-correction-notes.md docs/task-dispatch-architecture.md docs/state/d2-longform-correction-package-20260509.md
- 复核 docs/plans/2026-04-26-backend-mainline-cutover.md 中 D2“主线收口标准”定义
- 复核 docs/current-progress-board.md 已回写 D2 包边界说明
```

## 推荐 stage 命令

```bash
git add \
  .gitignore \
  README.md \
  docs/closeout.md \
  docs/governance-upgrade-map.md \
  docs/review-correction-notes.md \
  docs/task-dispatch-architecture.md \
  docs/state/d2-longform-correction-package-20260509.md
```

## staged diff 预演摘要

### 纳入项
- `.gitignore`
- `README.md`
- `docs/closeout.md`
- `docs/governance-upgrade-map.md`
- `docs/review-correction-notes.md`
- `docs/task-dispatch-architecture.md`
- `docs/state/d2-longform-correction-package-20260509.md`

### 明确不纳入
- `docs/current-progress-board.md`

## 预演统计

按当前工作区直读：

- 已跟踪改动 6 个文件，合计：**349 insertions / 1657 deletions**
- 另有 1 个新增说明文件：`docs/state/d2-longform-correction-package-20260509.md`

逐文件概览：

| 文件 | 变化 |
|---|---|
| `.gitignore` | 10 insertions / 1 deletion |
| `README.md` | 10 insertions / 6 deletions |
| `docs/closeout.md` | 142 insertions / 26 deletions |
| `docs/governance-upgrade-map.md` | 12 insertions / 5 deletions |
| `docs/review-correction-notes.md` | 174 insertions / 1618 deletions |
| `docs/task-dispatch-architecture.md` | 1 insertion / 1 deletion |
| `docs/state/d2-longform-correction-package-20260509.md` | 新增 |

## 提交解释口径

这笔提交的重点不是“新增功能”，而是把 D2 对应的**正式长文口径**从旧阶段判断收回到当前真实阶段：

1. `README.md`
   - 回正 gateway restart 表述
   - 回正 scheduler-scan 的认证 / 内部定时线程口径

2. `docs/closeout.md`
   - 把主线收口结论明确压成“dual/export 过渡态 + 已补 smoke / 回滚演练证据 + 仍待最终验收”

3. `docs/governance-upgrade-map.md`
   - 把治理映射表里的 backend host-native、显式派部、自然样本厚度等状态回正到新阶段

4. `docs/review-correction-notes.md`
   - 从多轮混排复查笔记收成“正式正文 + 证据附录”

5. `docs/task-dispatch-architecture.md`
   - 修正 scheduler scan 周期表述

6. `.gitignore`
   - 清掉本地实验 / runtime 噪音对 D2 文档收口面的干扰

7. `docs/state/d2-longform-correction-package-20260509.md`
   - 单独固定 D2 包边界，防止后续再把主板或过程稿混回正式包

## 风险提醒

- `docs/current-progress-board.md` 目前已回写 D2 条目，但**不要顺手一起提交进 D2 包**。
- `docs/review-correction-notes.md` 缩减幅度很大，但本质是“正文定稿化 + 附录下沉”，不是内容丢失。
- 这笔提交是**文档口径回正**，不代表 backend dual/export 已完成最终验收。
