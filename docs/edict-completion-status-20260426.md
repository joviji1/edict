# edict / 三省六部完成度清单

更新时间：2026-04-26 18:00（北京时间）

## 1. 一句话结论

**没有“全部完成”。**

更准确的当前状态是：

- **三省六部治理主线：工程收口基本完成，但仍有运行态样本与个别链路收尾项。**
- **整个 edict 路线图：明显未全部完成，Phase 2 仍有尾项，Phase 3 还有较多扩展项目未做。**

---

## 2. 本次判断依据

### 2.1 主线收口文档
- `docs/closeout.md`
- `docs/governance-upgrade-map.md`

### 2.2 路线图
- `ROADMAP.md`

### 2.3 当前 live 台账
- `data/tasks_source.json`

---

## 3. 当前总判断

### A. 已完成
这些项目已有明确文档、代码或运行态证据，当前不应再按“未做”描述：

1. **三省六部治理主线核心能力**
   - 正式审稿稿、分工推进稿已补落盘
   - 12 面板现实口径已对齐
   - `PendingConfirm / gate_checks / templateId / templateParams / targetDept` 已做可逆 probe 验证
   - 尚书省“显式派给六部”链路已落地
   - doctor / memory backup / safe_update / session guard 已落地

2. **Roadmap Phase 1 核心架构**
   - 当前 `ROADMAP.md` 统计：**20/20 完成，0 项未完成**
   - 可视为当前 Phase 1 已完成

3. **Roadmap Phase 2 中已完成的制度项**
   - 御批模式核心闭环
   - 看板内审批面板
   - 审批通知（统一 notification channel 路径）
   - 功过簿基础统计、排行榜、趋势总览、能臣/需训练标签
   - 急递铺最小消息流面板
   - 国史馆最小检索闭环

### B. 基本完成，但仍需收尾
这些项目不能算“没做”，但也不适合说“彻底收口”：

1. **治理主线自然样本厚度**
   - `closeout.md` 当前明确结论：
     - **工程收口基本完成**
     - **生产运行态尚未出现新的治理类自然样本，不能说已有充分自然验证**
   - 这属于“能力闭环已成，线上样本仍薄”

2. **模型配置链路（后端/runtime 已闭环，前台登录态实测仍可再补）**
   - 本轮已拿到真实运行态证据：
     - `taizi` 已实测完成 `faker/gpt-5.4 -> longcat/LongCat-Flash-Chat -> faker/gpt-5.4` 双向切换
     - `openclaw.json` / `agent_config.json` / `last_model_change_result.json` 三处结果一致
     - Gateway PID 两次变化，说明重启链路真实发生，不再只是 UI 口径
   - 本轮又补了生产级根因修复：
     - 修正 `_agent_effective_model()` 误把“唯一 fallback”当成当前有效模型的问题
     - 修正 `apply_model_changes.py` 先原地改 `cfg`、再计算 `old_text`，导致真实变更被误判为 `writeSkipped` 的问题
     - 修正 loop / server / 手工执行可能并发触发 `apply_model_changes.py`，造成结果互相覆盖的问题（新增单实例锁）
     - 把 `apply_model_changes.py` 内部 restart timeout 提到 `60s`，并把 server / run_loop 的外层超时提到 `75s`
     - 回归验证已实跑：`4 passed`
   - 因此它现在更准确的状态是：
     - **后端 apply/restart/sync/persistence 链路已收口**
     - **若要补“前台点按钮”的 end-to-end 截图/录屏证据，还需带 dashboard 登录态再跑一遍**

3. **live 台账仍有 runtime 残留**
   - 当前 `data/tasks_source.json`：
     - 总数：14
     - `Done=10`
     - `Review=1`
     - `Next=3`
   - 当前 4 条非 Done 都是 `OC-*` runtime 会话映射：
     - `OC-taizi-*`
     - `OC-zhongshu-*`
     - `OC-shangshu-*`
     - `OC-menxia-*`
   - 这说明正式项目不算大量积压，但运行态会话还没完全归零

### C. 明确未完成
这些项目在 `ROADMAP.md` 中仍处于未勾选状态，不能说已完成：

#### C1. Phase 2 未完成项（4 项）
1. 急递铺：看板内实时连线动画（中书→门下→尚书→六部）
2. 急递铺：消息类型着色（派发 / 审议 / 回奏 / 封驳）
3. 急递铺：时间线回放模式
4. 国史馆：奏折引用溯源链

#### C2. Phase 3 未完成项（9 项）
1. Notion 适配器
2. Linear 适配器
3. GitHub Issues 双向同步
4. 移动端响应式布局
5. PWA 离线支持 + 推送通知
6. ClawHub 上架：核心 Skills 提交官方市场
7. ClawHub 上架：一键安装 Skill Pack
8. Agent 年度绩效报告
9. 年度复盘大屏

---

## 4. 路线图计数快照

根据本轮对 `ROADMAP.md` 的程序化提取：

- **Phase 1 — 核心架构：20 done / 0 todo**
- **Phase 2 — 制度深化：10 done / 4 todo**
- **Phase 3 — 生态扩展：3 done / 9 todo**

因此，如果问题是“**整个 edict 所有项目是否全部完成**”，答案只能是：

**没有。**

---

## 5. 推荐对外口径

### 5.1 如果问的是“三省六部治理主线”
建议回答：

> **主线工程收口基本完成了；运行自然样本仍待继续补厚，但模型配置后端链路这次已经收口。**

### 5.2 如果问的是“整个 edict 项目/路线图”
建议回答：

> **没有全部完成。Phase 1 已完成；Phase 2 仍有 4 个尾项；Phase 3 还有 9 个扩展项目未完成。**

---

## 6. 下一步优先级建议

### P1：先收尾，不要乱开新坑
1. 继续补治理类自然样本
2. 清理 `OC-*` runtime 残留会话带来的完成度噪音
3. 若要补前台模型切换证据，再走一遍带登录态的 `/api/set-model` 可视化实测

### P2：再补 Roadmap Phase 2 尾项
1. 急递铺实时连线动画
2. 消息类型着色
3. 时间线回放
4. 国史馆引用溯源链

### P3：最后做生态扩展
1. Notion / Linear / GitHub 适配器
2. 移动端 / PWA
3. ClawHub 上架
4. 年度大考大屏

---

## 7. 当前最准确结论

**主线不是没做完，而是“基本收口，仍有尾项”；整个路线图则明确还没有全部完成。**
