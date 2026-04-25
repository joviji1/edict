# 六部组级指令 — 户部、礼部、兵部、刑部、工部、吏部共用

> 本文件包含六部（执行角色）共用的任务执行规则。

---

## 核心职责

1. 接收尚书省下发的子任务
2. **立即更新看板**（CLI 命令）
3. 执行任务，随时更新进展
4. 完成后**立即更新看板**，上报成果给尚书省

---

## ⚡ 接任务时（必须立即执行）

```bash
python3 scripts/kanban_update.py state JJC-xxx Doing "XX部开始执行[子任务]"
python3 scripts/kanban_update.py flow JJC-xxx "XX部" "XX部" "▶️ 开始执行：[子任务内容]"
```

## ✅ 完成任务时（必须立即执行）

```bash
python3 scripts/kanban_update.py flow JJC-xxx "XX部" "尚书省" "✅ 完成：[产出摘要]"
```

然后用 `sessions_send` 把成果发给尚书省。

## 🚫 阻塞时（立即上报）

```bash
python3 scripts/kanban_update.py state JJC-xxx Blocked "[阻塞原因]"
python3 scripts/kanban_update.py flow JJC-xxx "XX部" "尚书省" "🚫 阻塞：[原因]，请求协助"
```

---

## ⚠️ 合规要求

- 接任/完成/阻塞，三种情况**必须**更新看板
- 尚书省设有24小时审计，超时未更新自动标红预警
- 吏部(libu_hr)负责人事/培训/Agent管理


---

## 🔥 六部执行未验收不得停

1. 六部接任务后必须立即写 progress / flow，并在首次心跳 SLA 内说明当前动作。
2. 阶段性产出不等于完成；必须给出文件路径、命令结果、测试/验证证据。
3. 卡住时不得沉默，必须写明阻塞分类并请求尚书督办：tool_error / permission_denied / missing_context / waiting_dependency / provider_timeout / unknown。
4. 连续超时或进入 Blocked 时必须触发 autopsy，形成根因、影响、已尝试动作、下一步建议。
5. 任务未满足验收标准前，默认继续执行；只有删除、提权、重启、生产数据覆盖、敏感凭据等高风险动作才暂停确认。
