# JJC-20260416-001 三省六部治理升级正式审稿稿

更新时间：2026-04-28 04:46（北京时间）
适用仓库：`/root/.openclaw/workspace/edict`

---

## 1. 审稿结论

本轮“三省六部治理升级”已经从概念性方案，推进到**可运行的主链路收口阶段**。

准确结论不是“已经彻底切完 backend 主链”，也不是“全部自然运行证据都很充足”，而是：

> **产品能力已闭环，代码/测试/运行服务已落地；但 backend host-native 生产默认值仍未切入，部分治理字段在当前生产数据中的自然样本也仍偏少，正式交付稿此前的路径漂移已补齐。**

---

## 2. 本轮已核实的硬证据

### 2.1 服务运行态
- `edict-dashboard.service`：active
- `edict-loop.service`：active
- Dashboard 进程当前由 systemd 托管，后端入口为：
  - `/usr/bin/python3 /root/.openclaw/workspace/edict/dashboard/server.py --host 127.0.0.1 --port 7892`

### 2.2 关键文件存在
- `dashboard/server.py`
- `dashboard/court_discuss.py`
- `scripts/doctor_edict.sh`
- `scripts/memory_backup.sh`
- `scripts/safe_update.sh`
- `data/tasks_source.json`
- `data/officials_stats.json`

### 2.3 编译 / 测试验证
已执行：

```bash
python3 -m py_compile dashboard/server.py dashboard/court_discuss.py scripts/sync_officials_stats.py scripts/export_backend_tasks_to_legacy_json.py scripts/rebuild_task_views.py scripts/sync_governance_samples.py
python3 -m pytest tests/test_server.py tests/test_sync_officials_stats.py tests/test_sync_governance_samples.py tests/test_rebuild_task_views.py tests/test_refresh_live_data_layers.py tests/test_sync_from_openclaw_runtime.py tests/test_guard_openclaw_sessions.py -q
```

结果：
- `56 passed`

说明：
- 待批专面板、PendingConfirm / gate_checks、审批通知、急递铺、朝堂议政、功过簿统计，以及 runtime/governance samples/backend export/refresh layer 相关主链条至少在目标测试层面是闭合的。

### 2.4 线上实际前端 bundle 验证
直接抓取 `http://127.0.0.1:7892/` 当前服务出的 JS bundle，已确认包含以下真实运行标签：

- `待批专面板`
- `急递铺 / 国史馆`
- `朝堂议政`
- `走势总览`
- `能臣`
- `需训练`
- `显式派给六部`

本轮 2026-04-28 04:46 再抓一次，当前 JS 路径为 `/assets/index-D01zPxfi.js`。

这说明相关 UI 不只是源码存在，而是**已进入当前被服务的前端产物**。

---

## 3. 分项审稿结论

### 3.1 御批模式 / 待批专面板
**结论：已完成产品级闭环。**

已确认：
- `PendingConfirm`、`pending_confirm`、`gate_checks` 的后端导出与处理逻辑存在
- `handle_review_action(...)` 已覆盖准奏 / 封驳
- `/api/approval-panel` 存在对应路由
- 看板中已有独立“待批专面板”口径
- 审批提醒 / 审批结果通知已有代码与测试覆盖

但要实话实说：
- 当前 `data/tasks_source.json` 中**自然生产样本**仍未出现 `pending_confirm` / `gate_checks`
- 所以能确认“功能已具备”，不能假装“线上自然业务样本已经很丰富”

### 3.2 功过簿
**结论：已落地，当前偏轻量运行态。**

已确认：
- `officials_stats.json` 已输出 success_rate / timeout_rate / retries / tokens / cost / elapsed / merit 等字段
- 前端 bundle 已含 `走势总览`、`能臣`、`需训练`
- 对应测试已覆盖标签与 merit_history 生成逻辑

当前运行态事实：
- `official_count = 11`
- `has_tags = 2`
- `has_merit_history = 3`

这说明：
- 页面与机制都在
- 但现网样本还不算“喂满”

### 3.3 急递铺 / 国史馆
**结论：最小闭环已落地。**

已确认：
- README / ROADMAP 口径与当前代码一致
- 前端 bundle 中已有 `急递铺 / 国史馆`
- 测试中已有事件摘要与审批统计聚合验证

当前仍未闭合项：
- 更强的实时动画 / 回放等增强能力仍属后续工作，不影响“最小可运行闭环已存在”的结论

### 3.4 朝堂议政
**结论：已落地。**

已确认：
- `dashboard/court_discuss.py` 存在
- 测试覆盖了 11 官员场景
- 线上 bundle 中已有 `朝堂议政`

---

## 4. 本轮发现并修正的漂移

### 4.1 交付物路径漂移
此前 `docs/governance-upgrade-map.md` 将以下文件记为“已完成”：

- `deliverables/JJC-20260416-001-sansheng-governance-executable-review.md`
- `deliverables/JJC-20260416-001-task-division-plan.txt`

但当前仓库中：
- 不存在 `deliverables/` 目录
- 也未找到上述文件

这属于**文档假账**，已修正为真实状态，并将对应交付物重建到 `docs/` 下可追踪路径。

### 4.2 能力完成 ≠ 自然样本充足
当前分层后的现场数据已继续更新（2026-04-28 04:46，北京时间）：

- `data/live_status.json.taskSource = "tasks_source.json"`
- `live_status.taskLayers.runtimeCount = 1`
- `live_status.taskLayers.governanceSampleCount = 1`
- `live_status.taskLayers.jjcArchiveCount = 34`
- `data/tasks_source.json` 当前共 `11` 条任务：`Review=1 / Done=10`
- 治理字段现场统计仍为：`pending_confirm=0 / gate_checks=0 / templateId=0 / templateParams=0 / targetDept=0 / autopsy=1`
- `data/tasks_backend_export_meta.json` 当前不存在，说明生产刷新链尚未进入 backend export 分支

这意味着：
- 功能能力已在
- 结构分层与兼容出口仍在工作
- 当前 runtime 面不再是大面积 OC 噪音残留问题，但也还不是完全归零的“理想空面”
- backend 常驻链健康，不等于生产默认值已切 backend 主链
- 自然触发的治理类样本依然偏薄

本轮另外确认并修掉两个真实 runtime 噪音来源：
- `scripts/sync_from_openclaw_runtime.py::should_keep_runtime_task()` 过去会把超过 60 分钟、状态进入 `Next` 的真实 `agent:*:main` 会话误当成普通冷却任务筛掉；现已改为仅保留 24h 窗口内且具备真实 activity 的 main session，heartbeat/bootstrap 回声与空白 session 会直接丢弃
- `scripts/guard_openclaw_sessions.py` 现已补上 `missing_transcript_file` 检测，并在 `rotate_entry()` 轮转后真实创建空 transcript 占位，避免 cron 反复轮转同一坏指针
- 对应回归已补并实跑：`pytest -q tests/test_sync_from_openclaw_runtime.py` -> `9 passed`，`pytest -q tests/test_guard_openclaw_sessions.py` -> `3 passed`

所以汇报时必须分开说：
- “runtime 结构分层 + 过滤修正已完成”
- “上游自然样本仍少，目前 runtime=0、治理样本=1”
- 不能混成一句“全都好了”

---

## 5. 当前主线判断

### 已可确认完成
- 核心治理功能已在代码层闭合
- 相关测试已过
- Dashboard / Loop 服务在线
- React 前端当前运行态已包含治理升级后的真实面板与标签
- 运维脚本（doctor / backup / safe update）已落地
- 主线映射总表中的虚假 deliverables 记录已被纠偏

### 尚未可宣称“完全自然运行收口”
- PendingConfirm / gate_checks / template 字段在真实生产任务中的自然样本仍稀少
- 功过簿真实页面仍会因样本不足出现部分空态
- 某些“能力已实现”的点，仍需要可逆 probe 或后续自然样本持续补证据

---

## 6. 审稿意见

建议将当前主线状态定性为：

> **P1 收口中，已过“功能是否存在”的争议阶段，进入“补正式交付物 + 补运行态证据 + 持续清理文档漂移”阶段。**

换句话说：
- 现在最不该做的是重复怀疑已经落地的功能
- 现在最该做的是把“能力存在”继续压实成“证据充足、文档一致、样本渐丰”

---

## 7. 后续建议

1. 继续做一轮**可逆运行 probe**：
   - `PendingConfirm`
   - `gate_checks`
   - `review_round`
   - `templateId / templateParams / targetDept`
2. 将 probe 结果回写到主线总表与收口文档
3. 后续再观察自然运行任务是否开始稳定产出这些字段

---

## 8. 本次产物
- 正式审稿稿：`docs/JJC-20260416-001-sansheng-governance-executable-review.md`
- 分工推进稿：`docs/JJC-20260416-001-task-division-plan.txt`
- 治理升级总表：`docs/governance-upgrade-map.md`
