# edict backend host-native 生产化方案

更新时间：2026-04-26 21:17（北京时间）

## 当前结论

这条线已经**正式落地**，不是停在方案层。

当前生产化形态是：

1. **infra 走 compose**
   - `edict-postgres`
   - `edict-redis`
   - 只绑定 `127.0.0.1`
2. **backend / worker 走 host-native systemd**
   - `edict-backend-api.service`
   - `edict-backend-outbox-relay.service`
   - `edict-backend-orchestrator.service`
   - `edict-backend-dispatch.service`
3. **端口避开 8000**
   - backend 正式监听 `127.0.0.1:18000`
4. **运行时依赖独立 venv**
   - `/root/.openclaw/workspace/edict/.venv-edict-backend`

## 已正式落地的文件 / 单元

### 脚本

- `scripts/setup_backend_runtime.sh`
- `scripts/run_backend_component.sh`
- `scripts/check_backend_prereqs.sh`
- `scripts/manage_backend_infra.sh`
- `scripts/run_backend_migrations.sh`

### 配置

- `/etc/edict/backend.env`
- `deploy/backend/backend.env.example`
- `deploy/backend/docker-compose.infra.yml`

### systemd

- `edict-backend-infra.service`
- `edict-backend-api.service`
- `edict-backend-outbox-relay.service`
- `edict-backend-orchestrator.service`
- `edict-backend-dispatch.service`

## 现场事实

- `edict-dashboard.service`：active
- `edict-loop.service`：active
- `edict-backend-infra.service`：enabled / active (exited)
- `edict-backend-api.service`：enabled / active (running)
- `edict-backend-outbox-relay.service`：enabled / active (running)
- `edict-backend-orchestrator.service`：enabled / active (running)
- `edict-backend-dispatch.service`：enabled / active (running)
- `edict-postgres`：healthy，监听 `127.0.0.1:5432`
- `edict-redis`：healthy，监听 `127.0.0.1:6379`
- backend API：监听 `127.0.0.1:18000`
- 现网 `8000` 仍由别的 grok 容器占用，因此 backend 没去碰它

## 本轮实际执行过的动作

### 1. 运行时准备

- 建立 backend 专用 venv：
  - `/root/.openclaw/workspace/edict/.venv-edict-backend`
- 安装 backend 依赖
- 补齐 `alembic`

### 2. 正式 env 落地

- 写入 `/etc/edict/backend.env`
- 权限收为 `600 root:root`
- env 内已包含：
  - backend 端口
  - Postgres 凭据
  - Redis 地址
  - OpenClaw / EDICT 路径

### 3. infra 正式启动

通过 `edict-backend-infra.service` 拉起：

- `edict-postgres`
- `edict-redis`

### 4. schema 正式落盘

已执行：

```bash
bash /root/.openclaw/workspace/edict/scripts/run_backend_migrations.sh
```

实际包含：

- `001_initial`
- `002_add_outbox_events`

其中 `002_add_outbox_events` 就是这轮补的 fresh deploy 首个 schema 坑修复。

### 5. backend 正式启动

已启动：

- API
- outbox relay
- orchestrator
- dispatch

### 6. 真写路径烟测

不是只看 `/health`。

这轮实际做了真实 API 写入：

- `POST /api/tasks` → **201**
- `POST /api/tasks/by-legacy/.../progress` → **200**
- `PUT /api/tasks/by-legacy/.../todos` → **200**
- `POST /api/tasks/by-legacy/.../transition` → **200**
- `GET /api/tasks/by-legacy/...` → **200**

烟测任务曾从：

- `Taizi -> Zhongshu`

并成功读回完整任务详情。

为避免 smoke 任务真被 dispatch 派出，本轮是：

1. 临时停 `outbox-relay / orchestrator / dispatch`
2. 只保留 API 做真写路径验证
3. 测完后直接从 Postgres 清掉 smoke 任务和对应 outbox 记录
4. 再把 3 个 worker 拉回

所以这轮验证**既是真写**，也**没污染正式任务流**。

## 当前验证结果

### 健康检查

```bash
curl -s http://127.0.0.1:18000/health
curl -s http://127.0.0.1:18000/api/admin/health/deep
curl -s http://127.0.0.1:18000/api/admin/config
```

当前结果：

- `/health` → 200
- `/api/admin/health/deep` → 200
- `postgres=true`
- `redis=true`
- backend config 显示端口为 `18000`

### 日志噪音处理

worker 初始 journal 有 `runpy RuntimeWarning`。

根因是：
- `app/workers/__init__.py` 预先 import 了 worker 子模块
- 又用 `python -m app.workers.xxx` 启动
- 导致 runpy 报重复装载 warning

本轮已修：
- `edict/backend/app/workers/__init__.py` 改为**无副作用包初始化**
- 重启后 warning 已消失

## 回滚

### 停 backend 常驻

```bash
sudo systemctl disable --now \
  edict-backend-dispatch.service \
  edict-backend-orchestrator.service \
  edict-backend-outbox-relay.service \
  edict-backend-api.service \
  edict-backend-infra.service
```

### 仅停 worker，保留 API

```bash
sudo systemctl stop \
  edict-backend-dispatch.service \
  edict-backend-orchestrator.service \
  edict-backend-outbox-relay.service
```

### 收掉 infra 容器

```bash
sudo systemctl stop edict-backend-infra.service
```

## 运维常用命令

### 看状态

```bash
systemctl status --no-pager \
  edict-backend-infra.service \
  edict-backend-api.service \
  edict-backend-outbox-relay.service \
  edict-backend-orchestrator.service \
  edict-backend-dispatch.service
```

### 看容器

```bash
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | grep -E 'edict-|NAMES'
```

### 看 API 健康

```bash
curl -s http://127.0.0.1:18000/health
curl -s http://127.0.0.1:18000/api/admin/health/deep
```

### 只读前置检查

```bash
cd /root/.openclaw/workspace/edict
bash scripts/check_backend_prereqs.sh
```

## 仍需注意的点

1. 现网 dashboard / loop 还没有改成走 backend 主链
   - 现在 backend 是**正式常驻好了**
   - 但 edict 现有主现场仍大量依赖 JSON 看板链路
2. `8000` 不是安全端口
   - 即便某次检查里它暂时没暴露，也不要把 backend 改回 8000
   - 当前稳定口径还是 `18000`
3. smoke 数据已清理
   - 这次验证没留下正式任务污染

## 最终状态

**backend host-native 常驻：已落地。**

不是只修了代码，也不是只补了文档，
而是已经完成了：

- infra 常驻
- env 落地
- migration 落地
- systemd 落地
- 开机自启
- 真写路径验收
- smoke 清理回收
