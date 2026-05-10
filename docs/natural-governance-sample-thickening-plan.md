# edict 自然治理样本补厚改造方案

> 适用背景：`JJC-20260416-001` 主线已完成功能收口，但 `tasks_source.json` 中自然治理样本长期偏薄，导致“能力已实现”与“线上自然样本已充分验证”之间仍有断层。

**目标：** 让 `PendingConfirm / gate_checks / review_round / templateId / templateParams / targetDept` 等治理字段，能以**自然运行样本**而不是临时 probe 的形式，稳定进入当前看板数据面。

**当前判断：** 问题核心不在前端、不在刷新循环、不在字段实现本身，而在**任务源分层缺失**、**runtime 映射只保留瞬时活跃态**、以及**历史 `JJC-*` 旨意任务长期占据主任务面**。

---

## 1. 现状与根因

### 1.1 当前数据面现状
截至 2026-04-26 05:04（北京时间）现场实测：

- `data/tasks_source.json` 共 32 条
- `JJC = 32`
- `OTHER = 0`
- `Done = 32`
- `pending_confirm = 0`
- `gate_checks = 0`
- `review_round = 0`
- `templateId/templateParams/targetDept = 0`

这说明当前看板任务面几乎完全由**历史旨意任务**组成，自然运行中的治理样本没有稳定沉淀进去。

### 1.2 当前源码链路
关键链路：

1. `scripts/sync_from_openclaw_runtime.py`
   - 从 `~/.openclaw/agents/*/sessions/sessions.json` 读取 runtime session
   - 映射成临时 runtime 任务
   - 经 `should_keep_runtime_task()` 过滤，仅保留活跃/异常会话
   - 再把已有 `JJC-*` 任务无条件并回 `data/tasks_source.json`

2. `scripts/refresh_live_data.py`
   - 读取 `data/tasks_source.json`
   - 生成 `data/live_status.json`
   - 前端看板消费 `live_status.json`

### 1.3 根因拆解
当前自然样本薄，不是一个点的问题，是三个结构性问题叠加：

#### A. 任务源没有分层
现在 `tasks_source.json` 同时承担：
- 历史旨意台账
- runtime 活跃会话映射
- 看板主任务面

这三层混在一起，结果就是：
- 历史任务长期保留
- 运行时任务短暂且易被过滤
- 看板难以稳定看到“治理中”的样本

#### B. runtime 会话是瞬时映射，不是治理任务持久化
`sync_from_openclaw_runtime.py` 当前更像“会话镜像器”，不是“治理任务沉淀器”。
它能映射当前活跃态，却不会天然把带治理字段的任务作为长期样本保留下来。

#### C. `JJC-*` 回并策略太强
已有 `JJC-*` 会被无条件并回，且当前现场全是 Done 历史项。
这会造成：
- 主任务面长期被旧任务占住
- 自然治理样本即使短暂出现，也难成为稳定可观察主体

---

## 2. 改造目标

本轮改造不追求“重写任务系统”，只追求把自然治理样本稳定喂进当前看板。

### 2.1 必须达成
1. 自然运行中产生的治理任务，能在 `tasks_source.json` 或其替代持久层中保留一段时间
2. 看板主任务面不再被历史 `JJC-* Done` 任务长期压满
3. `PendingConfirm / gate_checks / review_round / template* / targetDept` 能自然进入前端展示
4. 不破坏现有 JJC 旨意留档价值
5. 整体方案可渐进落地，不要求一次推翻现有数据结构

### 2.2 明确不做
1. 不在本轮重写整个 kanban / worker 架构
2. 不在本轮引入数据库级新系统
3. 不为“样本好看”伪造长期假数据
4. 不把 probe 样本冒充自然线上样本

---

## 3. 推荐方案：三层任务面分离

这是我建议的主方案。核心思路：**把“历史台账”“运行态映射”“治理样本池”拆开，再在看板层汇总。**

### 3.1 新的数据分层

#### 层 1：历史旨意台账层
**文件：** `data/tasks_jjc_archive.json`

用途：
- 专门存放 `JJC-*` 历史旨意任务
- 保留长期审计价值
- 不再直接充当唯一主任务面

来源：
- 从当前 `tasks_source.json` 中迁移已有 `JJC-*`
- 后续 JJC 正式任务继续写入该层

#### 层 2：runtime 映射层
**文件：** `data/tasks_runtime_view.json`

用途：
- 保留 `sync_from_openclaw_runtime.py` 对 session 的实时映射结果
- 只承担“当前活跃/异常会话”的镜像视图
- 不要求长期保真

来源：
- 每轮 `sync_from_openclaw_runtime.py` 重建

#### 层 3：治理样本持久层
**文件：** `data/tasks_governance_samples.json`

用途：
- 持久保存自然运行中已经出现治理字段的任务样本
- 允许保留最近 N 天 / 最近 N 条
- 这是“自然样本补厚”的核心数据池

入池条件建议：
- 命中任一字段即入池：
  - `pending_confirm`
  - `gate_checks`
  - `review_round`
  - `templateId`
  - `templateParams`
  - `targetDept`
  - `autopsy`
  - `notifications`
- 同 task_id 更新时做 merge，不重复造副本
- 增加 `sampleCapturedAt` / `sampleLastSeenAt` 元数据

---

## 4. 看板聚合策略

### 4.1 新的主聚合顺序
建议由 `scripts/refresh_live_data.py` 或一个新的聚合脚本统一生成看板主任务面：

1. `tasks_runtime_view.json` 中当前活跃/异常任务
2. `tasks_governance_samples.json` 中最近仍值得观察的治理样本
3. `tasks_jjc_archive.json` 中少量高优先历史旨意（不是全量）

### 4.2 展示配额建议
为避免再次被历史任务淹没，建议引入配额：

- runtime 活跃层：优先全量展示
- 治理样本层：保留最近 30~50 条
- JJC 历史层：默认只展示最近 5~10 条，或单独放“历史旨意”面板

### 4.3 面板拆分建议
当前主面板职责太重，建议至少做展示逻辑拆分：

#### 主任务面板
展示：
- runtime 活跃/异常任务
- 最近治理样本

#### 历史旨意面板
展示：
- `JJC-*` 历史档案
- 允许单独检索/回查

#### 治理样本观察面板（可后续新增）
展示：
- `PendingConfirm`
- `gate_checks`
- `review_round`
- `template*`
- `autopsy`

这样主面板负责“现在在发生什么”，历史面板负责“以前发生过什么”。别再让两者打架。

---

## 5. 推荐实现顺序

### Phase 1：先拆数据，不改前端交互
目标：先把数据层分开，让自然样本有池子可落。

#### 任务 1
修改：`scripts/sync_from_openclaw_runtime.py`

动作：
- 不再直接把 runtime 映射结果与 JJC 全量混写成唯一 `tasks_source.json`
- 先单独输出 `data/tasks_runtime_view.json`
- 继续写 `sync_status.json`

#### 任务 2
新增：`scripts/sync_governance_samples.py`

动作：
- 从以下来源抽取治理样本：
  - `tasks_runtime_view.json`
  - `tasks_source.json`（迁移期兼容）
  - `mission_control_tasks.json`
  - `manual_parallel_tasks.json`
- 命中治理字段就写入 `data/tasks_governance_samples.json`
- 对同 `id` / 同 `sourceMeta.sessionId` 做 merge
- 淘汰过旧样本（如 14 天外）

#### 任务 3
新增：`scripts/rebuild_task_views.py`

动作：
- 汇总：
  - `tasks_runtime_view.json`
  - `tasks_governance_samples.json`
  - `tasks_jjc_archive.json`
- 生成新的 `data/tasks_source.json` 作为前端兼容出口

也就是说：
`tasks_source.json` 以后不再是“原始唯一事实源”，而是“给前端的聚合视图”。

### Phase 2：再改前端展示权重
目标：让前端真正把自然样本看见，而不是埋在历史 Done 里。

#### 任务 4
修改：`dashboard/server.py`

动作：
- 给 `/api/live-status` 或任务列表摘要增加来源标签：
  - `sourceLayer = runtime | governance_sample | jjc_archive`
- 暴露每层数量统计

#### 任务 5
修改前端任务列表 / 概览面板

动作：
- 默认按 `runtime > governance_sample > jjc_archive` 排序
- 对 `governance_sample` 增加视觉标记
- 对 `jjc_archive` 默认折叠或限量展示

### Phase 3：再补“样本形成机制”
目标：不是只靠过滤，而是主动让治理任务留下来。

#### 任务 6
在产生 `PendingConfirm` / `gate_checks` / `review_round` 的处理逻辑处，增加样本写入钩子

优先候选点：
- `dashboard/server.py` 中审批相关处理逻辑
- worker / kanban 更新链路里写入 `gate_checks`、`review_round` 的位置

动作：
- 一旦任务命中治理字段，就更新 `tasks_governance_samples.json`
- 避免只靠 session 映射层碰运气

这一步做完，样本才算真正“自然可持续”地产生。

---

## 6. 文件级改造建议

### 必改文件
- `scripts/sync_from_openclaw_runtime.py`
- `scripts/refresh_live_data.py`
- `dashboard/server.py`

### 建议新增文件
- `scripts/sync_governance_samples.py`
- `scripts/rebuild_task_views.py`

### 建议新增数据文件
- `data/tasks_jjc_archive.json`
- `data/tasks_runtime_view.json`
- `data/tasks_governance_samples.json`

---

## 7. 迁移策略

### 7.1 迁移原则
- 先兼容，后切换
- 先多写，后替换
- 全程可回滚

### 7.2 推荐迁移步骤
1. 备份当前 `data/tasks_source.json`
2. 抽取其中 `JJC-*` 到 `data/tasks_jjc_archive.json`
3. 保留当前 `tasks_source.json` 不动，先新增 `tasks_runtime_view.json`、`tasks_governance_samples.json`
4. 跑新聚合脚本生成候选版 `tasks_source.next.json`
5. 人工核对：
   - 是否还能看到历史 JJC
   - 是否开始出现治理样本
   - 是否没有把当前活跃任务吃掉
6. 确认后再切换正式输出

### 7.3 回滚策略
若新聚合效果不好：
- 恢复原 `tasks_source.json`
- 停用新脚本调用
- 保留新增样本文件供后续分析，不必立即删除

---

## 8. 验收标准

### 8.1 数据层验收
满足以下任意组合即算通过：
- `tasks_runtime_view.json` 稳定刷新
- `tasks_governance_samples.json` 可累计保留自然样本
- `tasks_source.json` 不再只有 `JJC Done` 一种结构

### 8.2 展示层验收
- 看板首页默认能看到 runtime 活跃项
- 最近治理样本能稳定看到
- 历史 JJC 不再霸占首屏

### 8.3 业务验收
至少出现以下任一自然样本并能稳定留存：
- `pending_confirm`
- `gate_checks`
- `review_round`
- `templateId`
- `autopsy`

### 8.4 口径验收
后续对外汇报时允许说：
- “自然治理样本已开始稳定沉淀”

在这之前，只能说：
- “能力已闭环，样本补厚方案已明确/已开始实施”

---

## 9. 风险与坑

### 风险 1：把历史层直接删掉
不行。那会丢审计价值。
正确做法是**分层，不是删除**。

### 风险 2：继续让 `tasks_source.json` 同时扮演所有角色
这就是现在的问题根。
如果不拆层，后面还会反复出现“为什么样本没有”“为什么首屏都是老任务”。

### 风险 3：只调排序，不改数据层
只能缓解，不能根治。
如果治理样本本身不被持久化，前端再会排版也没用。

### 风险 4：把 probe 样本混进自然样本池
不要这么干。
可以留测试痕迹，但必须标记 `sampleType = probe | natural`。
最好默认只把 `natural` 纳入主观察面。

---

## 10. 我的建议拍板
如果只选一个最值的切入点，我建议：

### 第一优先级
先做：
1. `tasks_jjc_archive.json`
2. `tasks_runtime_view.json`
3. `tasks_governance_samples.json`
4. `rebuild_task_views.py`

也就是先把**数据分层 + 聚合出口**搭起来。

### 第二优先级
再把治理字段命中时的写样本钩子补上。

### 第三优先级
最后再做前端独立“治理样本观察面板”。

原因很简单：
- 没数据池，前端改了也白改
- 没持久化，样本永远看天吃饭
- 没分层，历史任务永远挤占主面板

---

## 11. 建议产物清单
本方案对应的后续实际落地产物建议为：

- `docs/natural-governance-sample-thickening-plan.md`（本文）
- `scripts/sync_governance_samples.py`
- `scripts/rebuild_task_views.py`
- `tests/test_sync_governance_samples.py`
- `tests/test_rebuild_task_views.py`
- `docs/closeout.md` 中增加“方案已形成”记录

---

## 12. 一句话结论
**现在不是功能缺，而是数据面设计把自然治理样本饿死了。**

解决它，不靠继续等；
要靠把“历史台账、runtime 镜像、治理样本池”三层拆开，再统一聚合给看板看。
