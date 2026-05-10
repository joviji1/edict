# EDICT dual/export systemd 回滚演练 runbook（2026-04-30）

> 适用任务：`EDICT-BACKEND-CUTOVER-001`
> 目的：补齐 **真实 systemd 回滚演练证据**，验证当前生产 dual/export 过渡态可以通过 systemd 环境变量做最小面回退与回切。
> 当前北京时间：2026-04-30 05:33（北京时间） / system `date`：2026-04-30 05:33:11 CST (+0800)

---

## 1. 先说结论

这次演练要验证的是：

1. `edict-loop.service` 去掉 `EDICT_ENABLE_BACKEND_EXPORT=true` 后，服务仍可启动，且不会把 `data/tasks_source.json` 清空。
2. `edict-dashboard.service` 把 `EDICT_TASK_WRITE_MODE=dual` 临时改回 `json` 后，服务仍可启动，前台健康仍可达。
3. 演练完成后，再把两项配置恢复到当前生产默认值，能重新回到 `backend_api_export` 口径。

**这不是代码回滚，也不是数据回滚。**

禁止把这次演练做成：
- 跑 `scripts/safe_update.sh rollback` 恢复整包 `data/`
- 回滚源码
- 切 `EDICT_KANBAN_ENTRY_MODE`
- 在回退态长时间停留

---

## 2. 风险控制原则

1. **只改 systemd unit 环境变量，不改源码。**
2. **只验证“可退可回”，不验证业务新功能。**
3. **先退 loop，再退 dashboard；先回 dashboard，再回 loop。**
4. **任何异常优先立即回切，不在回退态硬扛。**
5. **不动 `data/` 内容，不跑整包 rollback。**

---

## 3. 演练前必须备份的东西

## 3.1 systemd unit 文件

备份到：`/root/.hermes/backups/`

- `/etc/systemd/system/edict-dashboard.service`
- `/etc/systemd/system/edict-loop.service`

建议命名：
- `/root/.hermes/backups/edict-dashboard.service.before-rollback-drill-20260430-053311`
- `/root/.hermes/backups/edict-loop.service.before-rollback-drill-20260430-053311`

## 3.2 数据面快照（只作证据留档，不用于本次整包恢复）

- `/root/.openclaw/workspace/edict/data/live_status.json`
- `/root/.openclaw/workspace/edict/data/tasks_backend_export_meta.json`
- `/root/.openclaw/workspace/edict/data/tasks_source.json`

## 3.3 服务与接口基线

记录：
- `systemctl show edict-dashboard.service -p Environment -p ActiveEnterTimestamp`
- `systemctl show edict-loop.service -p Environment -p ActiveEnterTimestamp`
- `http://127.0.0.1:18000/health`
- `http://127.0.0.1:18000/api/admin/health/deep`
- `http://127.0.0.1:18000/api/tasks?limit=10`
- `bash scripts/doctor_edict.sh`

---

## 4. 演练前基线验收

开始前，至少确认下面这些都成立：

- `systemctl is-active edict-dashboard.service` = `active`
- `systemctl is-active edict-loop.service` = `active`
- `live_status.json.taskSource = backend_api_export`
- `tasks_backend_export_meta.json` 存在
- `tasks_source.json` 非空
- `doctor_edict.sh` 未出现新的 `FAIL`
- backend `/health` 与 `/api/admin/health/deep` 返回 `200`

如果这里就不稳，**直接取消演练**。

---

## 5. Phase A：先演练 loop 回退（风险较小）

## 5.1 动作

把 `/etc/systemd/system/edict-loop.service` 中这行临时去掉：

```ini
Environment=EDICT_ENABLE_BACKEND_EXPORT=true
```

然后执行：

```bash
systemctl daemon-reload
systemctl restart edict-loop.service
```

## 5.2 预期

- `edict-loop.service` 仍为 `active`
- export 兼容层停止刷新
- `tasks_source.json` 不能被清空
- doctor 不应新增致命故障

## 5.3 验收点

依次检查：

```bash
systemctl is-active edict-loop.service
bash scripts/doctor_edict.sh
python3 - <<'PY'
import json, pathlib
for path in ['data/live_status.json','data/tasks_backend_export_meta.json','data/tasks_source.json']:
    p=pathlib.Path(path)
    print('FILE', path, 'exists=', p.exists())
    if not p.exists():
        continue
    obj=json.loads(p.read_text(encoding='utf-8'))
    if path.endswith('live_status.json'):
        print({'taskSource': obj.get('taskSource'), 'taskSourceMeta': obj.get('taskSourceMeta')})
    elif path.endswith('tasks_source.json'):
        print('tasks_source_count=', len(obj) if isinstance(obj, list) else 'non-list')
    else:
        print(obj)
PY
```

## 5.4 Phase A 失败即止损条件

出现任一项，立即进入回切：

- `edict-loop.service` 起不来
- `doctor_edict.sh` 出现新的 `FAIL`
- `tasks_source.json` 被清空或异常缩成 0
- dashboard `healthz` 明显异常

---

## 6. Phase B：再演练 dashboard 回退

## 6.1 动作

把 `/etc/systemd/system/edict-dashboard.service` 中：

```ini
Environment=EDICT_TASK_WRITE_MODE=dual
```

临时改成：

```ini
Environment=EDICT_TASK_WRITE_MODE=json
```

然后执行：

```bash
systemctl daemon-reload
systemctl restart edict-dashboard.service
```

## 6.2 预期

- `edict-dashboard.service` 仍为 `active`
- `http://127.0.0.1:7892/healthz` 仍可达
- backend 18000 health 仍可达
- doctor 不新增致命故障

## 6.3 验收点

```bash
systemctl is-active edict-dashboard.service
bash scripts/doctor_edict.sh
python3 - <<'PY'
import urllib.request
for url in [
    'http://127.0.0.1:7892/healthz',
    'http://127.0.0.1:18000/health',
    'http://127.0.0.1:18000/api/admin/health/deep',
]:
    print('URL', url)
    with urllib.request.urlopen(url, timeout=5) as r:
        print('STATUS', r.status)
        print(r.read().decode('utf-8','replace')[:500])
        print('---')
PY
```

## 6.4 Phase B 失败即止损条件

出现任一项，立即回切：

- `edict-dashboard.service` 起不来
- `healthz` 不可达
- `doctor_edict.sh` 出现新的 `FAIL`
- 前台明显不可用

**不要在回退态继续做 create/review/dispatch smoke。**
这一步只验证 systemd 回退是否可执行，不做业务功能验收。

---

## 7. 回切顺序（必须做）

演练成功后，不要在回退态停留太久。建议 1~3 分钟内完成观察后立即回切。

## 7.1 先回 dashboard

把 `/etc/systemd/system/edict-dashboard.service` 改回：

```ini
Environment=EDICT_TASK_WRITE_MODE=dual
```

执行：

```bash
systemctl daemon-reload
systemctl restart edict-dashboard.service
```

## 7.2 再回 loop

把 `/etc/systemd/system/edict-loop.service` 改回：

```ini
Environment=EDICT_ENABLE_BACKEND_EXPORT=true
```

执行：

```bash
systemctl daemon-reload
systemctl restart edict-loop.service
```

---

## 8. 回切后最终验收

必须重新确认：

```bash
systemctl is-active edict-dashboard.service edict-loop.service
bash scripts/doctor_edict.sh
python3 - <<'PY'
import json, pathlib, urllib.request
for path in ['data/live_status.json','data/tasks_backend_export_meta.json','data/tasks_source.json']:
    p=pathlib.Path(path)
    print('FILE', path, 'exists=', p.exists())
    if not p.exists():
        continue
    obj=json.loads(p.read_text(encoding='utf-8'))
    if path.endswith('live_status.json'):
        print({'taskSource': obj.get('taskSource'), 'taskSourceMeta': obj.get('taskSourceMeta')})
    elif path.endswith('tasks_source.json'):
        print('tasks_source_count=', len(obj) if isinstance(obj, list) else 'non-list')
    else:
        print(obj)
    print('---')
for url in [
    'http://127.0.0.1:18000/health',
    'http://127.0.0.1:18000/api/admin/health/deep',
    'http://127.0.0.1:18000/api/tasks?limit=10',
    'http://127.0.0.1:7892/healthz',
]:
    print('URL', url)
    with urllib.request.urlopen(url, timeout=5) as r:
        print('STATUS', r.status)
        print(r.read().decode('utf-8','replace')[:800])
        print('---')
PY
```

## 回切成功标准

- `edict-dashboard.service` = `active`
- `edict-loop.service` = `active`
- `doctor_edict.sh` 无新增 `FAIL`
- `live_status.json.taskSource = backend_api_export`
- `tasks_backend_export_meta.json` 存在且 count 合理
- `tasks_source.json` 未丢空
- backend `/api/tasks?limit=10` 继续正常
- dashboard `/healthz` 正常

---

## 9. 需要留档的证据

演练完成后，至少把这些写回主板：

1. 演练开始/结束北京时间
2. 演练前两份 unit 备份路径
3. Phase A（loop 回退）结果
4. Phase B（dashboard 回退）结果
5. 回切结果
6. 演练过程中 `taskSource` 如何变化
7. 是否出现异常、如何止损
8. 最终是否证明“systemd 级回退可执行且可回切”

---

## 10. 最终口径

如果演练成功，建议统一写成：

**“已完成一次最小面 systemd 回滚演练：dashboard `dual -> json`、loop 去掉 backend export 后服务仍可启动，回切后 `backend_api_export` 与双服务健康均恢复；当前已拿到真实可逆演练证据。”**

如果演练中途止损，也要老实写：

**“systemd 回退路径设计存在，但本轮实操在某一步触发异常，已立即回切；当前仍只能算‘有方案/有脚本，未完成可逆实操收口’。”**

---

## 11. 现场可复制命令清单

> 说明：下面命令默认在 `/root/.openclaw/workspace/edict` 执行；涉及 `/etc/systemd/system/*.service` 修改，需要人工确认后执行。

### 11.1 演练前备份与基线

```bash
cd /root/.openclaw/workspace/edict
STAMP=20260430-053642
mkdir -p /root/.hermes/backups/rollback-drill-$STAMP
cp -a /etc/systemd/system/edict-dashboard.service /root/.hermes/backups/rollback-drill-$STAMP/edict-dashboard.service
cp -a /etc/systemd/system/edict-loop.service /root/.hermes/backups/rollback-drill-$STAMP/edict-loop.service
cp -a data/live_status.json /root/.hermes/backups/rollback-drill-$STAMP/live_status.json
cp -a data/tasks_source.json /root/.hermes/backups/rollback-drill-$STAMP/tasks_source.json
if [ -f data/tasks_backend_export_meta.json ]; then cp -a data/tasks_backend_export_meta.json /root/.hermes/backups/rollback-drill-$STAMP/tasks_backend_export_meta.json; fi
systemctl show edict-dashboard.service -p Environment -p ActiveEnterTimestamp | tee /root/.hermes/backups/rollback-drill-$STAMP/dashboard.systemctl.txt
systemctl show edict-loop.service -p Environment -p ActiveEnterTimestamp | tee /root/.hermes/backups/rollback-drill-$STAMP/loop.systemctl.txt
bash scripts/doctor_edict.sh | tee /root/.hermes/backups/rollback-drill-$STAMP/doctor.before.txt
python3 - <<'PY' | tee /root/.hermes/backups/rollback-drill-$STAMP/http.before.txt
import urllib.request
for url in [
    'http://127.0.0.1:7892/healthz',
    'http://127.0.0.1:18000/health',
    'http://127.0.0.1:18000/api/admin/health/deep',
    'http://127.0.0.1:18000/api/tasks?limit=10',
]:
    print('URL', url)
    with urllib.request.urlopen(url, timeout=5) as r:
        print('STATUS', r.status)
        print(r.read().decode('utf-8','replace')[:1200])
        print('---')
PY
python3 - <<'PY' | tee /root/.hermes/backups/rollback-drill-$STAMP/data.before.txt
import json, pathlib
for path in ['data/live_status.json','data/tasks_backend_export_meta.json','data/tasks_source.json']:
    p=pathlib.Path(path)
    print('FILE', path, 'exists=', p.exists())
    if not p.exists():
        continue
    obj=json.loads(p.read_text(encoding='utf-8'))
    if path.endswith('live_status.json'):
        print({'taskSource': obj.get('taskSource'), 'taskSourceMeta': obj.get('taskSourceMeta')})
    elif path.endswith('tasks_source.json'):
        print('tasks_source_count=', len(obj) if isinstance(obj, list) else 'non-list')
    else:
        print(obj)
    print('---')
PY
```

### 11.2 Phase A：loop 回退

> 手工编辑 `/etc/systemd/system/edict-loop.service`，临时删掉这一行：
> `Environment=EDICT_ENABLE_BACKEND_EXPORT=true`

```bash
systemctl daemon-reload
systemctl restart edict-loop.service
systemctl is-active edict-loop.service
cd /root/.openclaw/workspace/edict
bash scripts/doctor_edict.sh | tee /root/.hermes/backups/rollback-drill-$STAMP/doctor.after-loop-rollback.txt
python3 - <<'PY' | tee /root/.hermes/backups/rollback-drill-$STAMP/data.after-loop-rollback.txt
import json, pathlib
for path in ['data/live_status.json','data/tasks_backend_export_meta.json','data/tasks_source.json']:
    p=pathlib.Path(path)
    print('FILE', path, 'exists=', p.exists())
    if not p.exists():
        continue
    obj=json.loads(p.read_text(encoding='utf-8'))
    if path.endswith('live_status.json'):
        print({'taskSource': obj.get('taskSource'), 'taskSourceMeta': obj.get('taskSourceMeta')})
    elif path.endswith('tasks_source.json'):
        print('tasks_source_count=', len(obj) if isinstance(obj, list) else 'non-list')
    else:
        print(obj)
    print('---')
PY
```

### 11.3 Phase B：dashboard 回退

> 手工编辑 `/etc/systemd/system/edict-dashboard.service`，把：
> `Environment=EDICT_TASK_WRITE_MODE=dual`
> 改成：
> `Environment=EDICT_TASK_WRITE_MODE=json`

```bash
systemctl daemon-reload
systemctl restart edict-dashboard.service
systemctl is-active edict-dashboard.service
cd /root/.openclaw/workspace/edict
bash scripts/doctor_edict.sh | tee /root/.hermes/backups/rollback-drill-$STAMP/doctor.after-dashboard-rollback.txt
python3 - <<'PY' | tee /root/.hermes/backups/rollback-drill-$STAMP/http.after-dashboard-rollback.txt
import urllib.request
for url in [
    'http://127.0.0.1:7892/healthz',
    'http://127.0.0.1:18000/health',
    'http://127.0.0.1:18000/api/admin/health/deep',
]:
    print('URL', url)
    with urllib.request.urlopen(url, timeout=5) as r:
        print('STATUS', r.status)
        print(r.read().decode('utf-8','replace')[:1200])
        print('---')
PY
```

### 11.4 回切 dashboard

> 手工把 `/etc/systemd/system/edict-dashboard.service` 改回：
> `Environment=EDICT_TASK_WRITE_MODE=dual`

```bash
systemctl daemon-reload
systemctl restart edict-dashboard.service
systemctl is-active edict-dashboard.service
```

### 11.5 回切 loop

> 手工把 `/etc/systemd/system/edict-loop.service` 改回：
> `Environment=EDICT_ENABLE_BACKEND_EXPORT=true`

```bash
systemctl daemon-reload
systemctl restart edict-loop.service
systemctl is-active edict-loop.service
```

### 11.6 回切后最终验收

```bash
cd /root/.openclaw/workspace/edict
systemctl is-active edict-dashboard.service edict-loop.service
bash scripts/doctor_edict.sh | tee /root/.hermes/backups/rollback-drill-$STAMP/doctor.final.txt
python3 - <<'PY' | tee /root/.hermes/backups/rollback-drill-$STAMP/http.final.txt
import urllib.request
for url in [
    'http://127.0.0.1:7892/healthz',
    'http://127.0.0.1:18000/health',
    'http://127.0.0.1:18000/api/admin/health/deep',
    'http://127.0.0.1:18000/api/tasks?limit=10',
]:
    print('URL', url)
    with urllib.request.urlopen(url, timeout=5) as r:
        print('STATUS', r.status)
        print(r.read().decode('utf-8','replace')[:1200])
        print('---')
PY
python3 - <<'PY' | tee /root/.hermes/backups/rollback-drill-$STAMP/data.final.txt
import json, pathlib
for path in ['data/live_status.json','data/tasks_backend_export_meta.json','data/tasks_source.json']:
    p=pathlib.Path(path)
    print('FILE', path, 'exists=', p.exists())
    if not p.exists():
        continue
    obj=json.loads(p.read_text(encoding='utf-8'))
    if path.endswith('live_status.json'):
        print({'taskSource': obj.get('taskSource'), 'taskSourceMeta': obj.get('taskSourceMeta')})
    elif path.endswith('tasks_source.json'):
        print('tasks_source_count=', len(obj) if isinstance(obj, list) else 'non-list')
    else:
        print(obj)
    print('---')
PY
```

### 11.7 任一步异常时的立刻止损

```bash
cp -a /root/.hermes/backups/rollback-drill-$STAMP/edict-dashboard.service /etc/systemd/system/edict-dashboard.service
cp -a /root/.hermes/backups/rollback-drill-$STAMP/edict-loop.service /etc/systemd/system/edict-loop.service
systemctl daemon-reload
systemctl restart edict-dashboard.service
systemctl restart edict-loop.service
cd /root/.openclaw/workspace/edict
systemctl is-active edict-dashboard.service edict-loop.service
bash scripts/doctor_edict.sh
```

> 注意：止损阶段默认**只恢复 unit 文件**，不恢复 `data/`。除非确认数据被异常破坏，否则不要把这次演练扩大成整包数据回滚。
