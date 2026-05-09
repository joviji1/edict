# D2 长文回正包（2026-05-09 14:56）

## 结论

这轮先把 **D2「主线收口标准」对应的长文回正面** 从大队列里单独拆出来，当前建议按 **7+1** 口径处理：

- **正式纳入 D2 长文回正包：7 项**
  1. `.gitignore`
  2. `README.md`
  3. `docs/closeout.md`
  4. `docs/governance-upgrade-map.md`
  5. `docs/review-correction-notes.md`
  6. `docs/task-dispatch-architecture.md`
  7. `docs/state/d2-longform-correction-package-20260509.md`（本说明）
- **过程板单列，不并入 D2 正式回正包：1 项**
  - `docs/current-progress-board.md`

核心判断：
- D2 要解决的是**长文口径回正**，不是再造一份运行态方案。
- `current-progress-board.md` 仍然是过程板 / 值守板，应该继续单列；否则会把“正式回正文档”和“现场持续日志”重新混回一起。

---

## 为什么是这 7 项

### 1. `.gitignore`
不是业务文档，但这轮回正里它承担了**文档收口卫生前置**作用：
- 把 `.cron_*`、`logs/`、`isolation/`、`.venv-*` 等现场噪音排除出提交视野；
- 避免后续把运行态残留误判成 D2 正式交付物。

### 2. `README.md`
承担对外/对内入口口径回正：
- 把“应用后自动重启 Gateway（~5 秒生效）”收紧成“触发 Gateway 重启，生效时延以运行态为准”；
- 把 `scheduler-scan` 从“裸 curl 可直打”回正为“当前受 dashboard 认证保护，默认由内部线程巡检”。

### 3. `docs/closeout.md`
这是 D2 长文回正的主正文之一：
- 已把 backend dual/export 过渡态、前台关键写链 smoke、systemd 最小回滚演练、自然样本厚度边界重新压成正式收口结论；
- 现在它承担的是“长版正式结论”，不是过程板摘要。

### 4. `docs/governance-upgrade-map.md`
承担治理映射口径回正：
- 把“尚书显式派部”“backend host-native 过渡态”“自然样本厚度”“回滚演练证据”这些条目回正到当前真实阶段；
- 作用是把治理升级映射表从旧阶段判断拉回当前事实面。

### 5. `docs/review-correction-notes.md`
承担“复查结论定稿化”回正：
- 已从 600+ 行首轮混排笔记收成“正式结论正文 + 证据附录”；
- 正文只保留当前仍成立的根因链与值守口径，附录保留追溯价值但不再冒充当前结论。

### 6. `docs/task-dispatch-architecture.md`
承担架构说明微回正：
- 把 scheduler 描述从“每 60 秒”回正成“当前由 dashboard 内部线程每 120 秒执行 `handle_scheduler_scan(threshold_sec=180)`”；
- 这是小改动，但属于 D2 长文口径回正链的一环。

### 7. `docs/state/d2-longform-correction-package-20260509.md`
这是本轮新增的包说明文件：
- 用来把 D2 回正范围、边界、纳入项、排除项、验证面一次说清；
- 避免后续又把 D2 长文回正包和 A/B/C 包、主板过程稿混在一起。

---

## 为什么 `current-progress-board.md` 不并进 D2 正式包

`current-progress-board.md` 这轮当然有关联，但它不适合和 D2 长文回正包一起算“正式定稿面”。原因有三条：

1. **角色不同**
   - `closeout / governance-upgrade-map / review-correction-notes / architecture / README` 是定稿型或准定稿型文本；
   - `current-progress-board.md` 是滚动值守板。

2. **更新节奏不同**
   - D2 回正包适合一次性收成一个明确提交面；
   - 主板会继续滚动追加，不该绑进这次定稿提交边界。

3. **风险不同**
   - 如果把主板也并进 D2，后面很容易再把过程噪音、跨域条目、临时执行记录一起带进正式回正包。

所以本轮更稳的边界是：

> **D2 正式包收长文定稿；主板只做挂账与引用，不并入正式回正包。**

---

## 当前文件面快照

按当前 `git diff` 直读，D2 关联文件规模如下：

| 文件 | 变化摘要 |
|---|---|
| `.gitignore` | 10 insertions / 1 deletion |
| `README.md` | 10 insertions / 6 deletions |
| `docs/closeout.md` | 142 insertions / 26 deletions |
| `docs/governance-upgrade-map.md` | 12 insertions / 5 deletions |
| `docs/review-correction-notes.md` | 174 insertions / 1618 deletions |
| `docs/task-dispatch-architecture.md` | 1 insertion / 1 deletion |
| `docs/current-progress-board.md` | 过程板，已滚动记录，不纳入本包 |

额外说明：
- `docs/review-correction-notes.md` 的大幅缩减不是丢信息，而是把“中间轮次判断”下沉到附录，正文回到正式定稿口径。
- `docs/closeout.md` 与 `docs/governance-upgrade-map.md` 这轮都已把“前台关键写链 smoke / systemd 回滚演练已补齐，当前尾项转为最终验收与自然样本观察”写明。

---

## 建议的 stage 面

### 正式 D2 长文回正包

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

### 明确先不并进这个包的文件

```bash
# 过程板单列
# 先不要并进 D2 正式回正包
docs/current-progress-board.md
```

---

## 推荐提交标题

```text
docs(D2): 回正主线收口长文口径
```

## 推荐提交正文

```text
- 回正 README、closeout、治理映射、review notes 与调度架构文档的当前口径
- 把 backend dual/export 过渡态、前台关键写链 smoke、systemd 最小回滚演练与自然样本边界压回正式文本
- 单列 D2 长文回正包边界，明确主板继续作为过程板，不并入本次正式定稿面
```

---

## 当前风险

1. **`current-progress-board.md` 仍在滚动更新**
   - 如果后面又把主板一起 stage，很容易重新把 D2 定稿包污染成过程包。

2. **`README.md` 与长文之间仍需继续防漂移**
   - 这轮已把关键口径拉齐，但后续若运行态再变，README 最容易先漂。

3. **D2 只解决长文口径，不替代最终验收**
   - 文档已回正，不等于 backend dual/export 过渡态已经完成最终验收。

---

## 本轮定性

当前可以把这轮动作定性成：

> **D2 长文回正包已经拆出来了，正式包建议只收 7 项定稿面；`current-progress-board.md` 继续单列做过程挂账，不混进本轮正式包。**
