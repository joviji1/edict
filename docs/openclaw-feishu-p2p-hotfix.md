# OpenClaw Feishu P2P 事件 hotfix 持久化说明

更新时间：2026-04-26 17:41（北京时间）

## 问题
OpenClaw 全局安装包 `@qingchencloud/openclaw-zh` 的当前运行构建中，`dist/monitor-BXs1Uex0.js` 的 `registerEventHandlers()` 漏注册了：

- `im.chat.access_event.bot_p2p_chat_entered_v1`

因此运行期会反复出现告警：

- `no im.chat.access_event.bot_p2p_chat_entered_v1 handle`

## 已落地修复

### 1. 运行包热修
已在下列文件补入轻量 handler：

- `/usr/lib/node_modules/@qingchencloud/openclaw-zh/dist/monitor-BXs1Uex0.js`

handler 行为：
- 记录 `chat_id`
- 记录 `operator_id.open_id`
- 记录 `last_message_id`
- 避免 SDK 再输出 `no ... handle`

### 2. 启动前自愈脚本
已新增：

- `/root/.openclaw/scripts/ensure_openclaw_feishu_p2p_hotfix.py`

作用：
- 启动前扫描 `/usr/lib/node_modules/@qingchencloud/openclaw-zh/dist/monitor-*.js`
- 如果发现目标事件 handler 缺失，则自动补丁
- 自动做备份到 `/root/.openclaw/backups/openclaw-feishu-p2p-autopatch-<timestamp>/`
- 对修改后的 js 执行 `node --check`
- 若已补过，则输出 `already_patched`

支持临时覆盖环境变量：
- `OPENCLAW_DIST_DIR`
- `OPENCLAW_BACKUP_DIR`

可用于本地 fixture 验证。

### 3. systemd 启动钩子
已新增 drop-in：

- `/root/.config/systemd/user/openclaw-gateway.service.d/10-feishu-p2p-hotfix.conf`

内容：

```ini
[Service]
ExecStartPre=/usr/bin/python3 /root/.openclaw/scripts/ensure_openclaw_feishu_p2p_hotfix.py
```

效果：
- 每次 `openclaw-gateway.service` 启动前都会先跑自愈脚本
- 即使后续 npm 升级把 `dist` 文件覆盖，下一次服务启动也会自动补回

## 备份

### 本次手工热修备份
- `/root/.openclaw/backups/openclaw-feishu-event-hotfix-20260426T090302Z/monitor-BXs1Uex0.js.bak`

### 本次持久化改动备份
- `/root/.openclaw/backups/openclaw-feishu-p2p-durable-20260426T091948Z/openclaw-gateway.service.bak`

## 验证结果

### 真实事件回归验证
用户与 taizi 私聊后，日志已出现真实命中：

- `2026-04-26T17:13:18.365+08:00`
- `2026-04-26T17:14:13.875+08:00`

日志特征：
- `feishu[default]: p2p chat entered ...`
- 后续还能看到 `received message` / `dispatching to agent` / `dispatch complete`

说明：
- 事件已被正确注册
- DM 消息主链正常

### 持久化钩子验证
`systemctl --user restart openclaw-gateway` 后，状态中已看到：

- `ExecStartPre=/usr/bin/python3 /root/.openclaw/scripts/ensure_openclaw_feishu_p2p_hotfix.py`
- `status=0/SUCCESS`
- 自愈输出：`OPENCLAW_FEISHU_P2P_AUTOPATCH ... monitor-BXs1Uex0.js:already_patched`

说明 drop-in 已生效。

### 4. 持续巡检守卫
已新增 Hermes cron 守卫：

- 名称：`openclaw-feishu-p2p-guard`
- job_id：`303f441dc499`
- 频率：`every 15m`

守卫采样脚本：
- `/root/.openclaw/scripts/check_openclaw_feishu_p2p_guard.py`

守卫职责：
- 检查 `openclaw-gateway.service` 是否为 active
- 检查 `ExecStartPre` 自愈钩子是否仍在
- 检查 `ensure_openclaw_feishu_p2p_hotfix.py` 是否能 `py_compile`
- 检查自愈脚本是否还能成功执行
- 检查当天日志里是否在 **当前服务启动之后** 又出现新的
  `no im.chat.access_event.bot_p2p_chat_entered_v1 handle`

告警策略：
- 正常时输出严格的 `[SILENT]`
- 只有确认回退时才回报 `OCLAW-FEISHU-EVENT-001` 告警

### 5. 巡检误报修正
首版守卫曾发生一次误报。根因不是热修失效，而是巡检口径写错：

- 错误口径：按**主机开机后**的历史坏事件统计
- 正确口径：只统计 `openclaw-gateway` **当前服务启动后**的新坏事件

因此，`17:21` 服务重启前留下的旧告警被首版守卫错误地当成“新回退”，造成一次假阳性。

现已修正为仅使用：

- `events.bad_since_service_start`

作为新回退证据；当前服务启动前的旧告警一律视为历史噪音，不再触发告警。

### 6. 巡检修正后的现场结果
2026-04-26 17:33 的最新 cron 会话已返回：

- `[SILENT]`

2026-04-26 17:41 现场再次手动执行守卫脚本，结果为：

- `service_active = true`
- `has_execstartpre = true`
- `py_compile.exit_code = 0`
- `ensure.exit_code = 0`
- `events.bad_since_service_start = []`
- `regression = false`

说明当前状态为：

- 热修仍在
- 自愈钩子仍在
- 巡检守卫已改为正确口径
- 当前没有新的回退证据

### 7. 回归测试补齐
已新增测试文件：

- `/root/.openclaw/workspace/edict/tests/test_openclaw_feishu_p2p_guard.py`

覆盖点：

- `parse_service_start()` 能正确提取 `openclaw-gateway.service` 当前启动时间
- `parse_log_events()` 不会把 **当前服务启动前** 的历史坏事件误判成新回退

本次执行结果：

- `pytest -q tests/test_openclaw_feishu_p2p_guard.py` → `2 passed`
- `python3 -m py_compile /root/.openclaw/scripts/check_openclaw_feishu_p2p_guard.py /root/.openclaw/workspace/edict/tests/test_openclaw_feishu_p2p_guard.py` → `exit_code=0`

说明这次“按主机开机时间误报”的坑，已经不只是口头修正，也有最小自动化回归兜底。

### 8. 统一体检入口已接入守卫
`scripts/doctor_edict.sh` 已接入 OpenClaw Feishu P2P 守卫检查。

当前 doctor 会额外执行：

- `/root/.openclaw/scripts/check_openclaw_feishu_p2p_guard.py`

并按以下规则收口：

- `regression = false` → 记为 `✅ OpenClaw Feishu P2P 守卫正常`
- `regression = true`、脚本缺失、执行失败、输出非法 → 记为 `❌` 并拉高 `FAIL`

本次现场执行：

- `bash scripts/doctor_edict.sh` → `PASS=31 WARN=1 FAIL=0`
- 新增 doctor 输出：
  - `✅ OpenClaw Feishu P2P 守卫正常: service_start=Sun 2026-04-26 17:21:08 CST; bad_since_service_start=0; good_since_service_start=0; auto_since_service_start=0`

说明这条热修链已经并入统一健康检查入口，不再只靠单独 cron 盯。

### 9. safe_update 联动验证通过
已验证 `scripts/safe_update.sh prepare` 仍可在接入新 doctor 后正常跑通。

本次执行方式：

- `EDICT_BACKUP_ROOT=$(mktemp -d ...) bash scripts/safe_update.sh prepare`

本次结果：

- `pytest -q tests/test_safe_update_script.py` → `4 passed`
- 真实 `prepare` 运行成功
- 预检阶段已调用新版 `bash scripts/doctor_edict.sh`
- doctor 期间已看到：
  - `✅ OpenClaw Feishu P2P 守卫正常 ...`
- 本次隔离输出目录：
  - `/tmp/edict-safe-update-KdJfql/safe-update-20260426-175123/`

说明现在这条链不光单独巡检正常，连上游安全更新管线也已经兼容这次守卫接入。

## 常用检查命令

```bash
systemctl --user status openclaw-gateway --no-pager -n 50
systemctl --user cat openclaw-gateway.service
grep -n "p2p chat entered\|no im.chat.access_event.bot_p2p_chat_entered_v1 handle" /tmp/openclaw/openclaw-$(date +%F).log | tail -20 || true
python3 /root/.openclaw/scripts/ensure_openclaw_feishu_p2p_hotfix.py
python3 /root/.openclaw/scripts/check_openclaw_feishu_p2p_guard.py
bash /root/.openclaw/workspace/edict/scripts/doctor_edict.sh
```

## 风险与说明
- 这是对 npm 安装包 `dist` 产物的运行时热修，不是 upstream 源码修复。
- 以后若包结构大改、anchor 文本变化，自愈脚本可能出现 `anchor_missing`，那时需要按新构建重新适配脚本。
- 当前脚本已经做成幂等：重复执行不会重复插入 handler。
