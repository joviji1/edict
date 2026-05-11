"""任务服务层 — CRUD + 状态机逻辑。

所有业务规则集中在此：
- 创建任务 → 事件写入 outbox 表（同一事务）
- 状态流转 → 校验合法性 + SELECT FOR UPDATE 防并发 + outbox 事件
- 查询、过滤、聚合

事件投递由 OutboxRelay worker 异步完成，保证 DB/Event 原子一致。
"""

import copy
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.outbox import OutboxEvent
from ..models.task import Task, TaskState, STATE_TRANSITIONS, TERMINAL_STATES
from .notification_service import send_pending_confirm_notification, send_review_result_notification
from .event_bus import (
    TOPIC_TASK_CREATED,
    TOPIC_TASK_STATUS,
    TOPIC_TASK_COMPLETED,
    TOPIC_TASK_DISPATCH,
)

log = logging.getLogger("edict.task_service")

_HIGH_RISK_TRANSITIONS = {
    (TaskState.Review, TaskState.Done),
    (TaskState.Doing, TaskState.Cancelled),
    (TaskState.Menxia, TaskState.Cancelled),
}

_CONFIRM_AUTHORITY = {
    TaskState.Review: "menxia",
    TaskState.Doing: "shangshu",
    TaskState.Menxia: "zhongshu",
}


class TaskService:
    def __init__(self, db: AsyncSession, event_bus=None):
        self.db = db
        # event_bus 保留用于 request_dispatch 等直接发布场景
        self.bus = event_bus

    @staticmethod
    def _summarize_text(text: str, limit: int = 240) -> str:
        """压缩多行文本为适合 progress_log / now 的短摘要。"""
        normalized = "\n".join(line.strip() for line in str(text or "").splitlines() if line.strip())
        if not normalized:
            return ""
        normalized = normalized.replace("\n", " / ")
        if len(normalized) <= limit:
            return normalized
        return normalized[: limit - 1].rstrip() + "…"

    # ── 创建 ──

    async def create_task(
        self,
        title: str,
        description: str = "",
        priority: str = "中",
        assignee_org: str | None = None,
        creator: str = "emperor",
        tags: list[str] | None = None,
        initial_state: TaskState = TaskState.Taizi,
        meta: dict | None = None,
    ) -> Task:
        """创建任务，事件写入 outbox 表（同一事务原子提交）。"""
        now = datetime.now(timezone.utc)
        trace_id = str(uuid.uuid4())
        target_org = Task.org_for_state(initial_state, assignee_org)
        task_meta = copy.deepcopy(meta or {})
        template_id = str(task_meta.get("templateId") or task_meta.get("template_id") or "")
        template_params = copy.deepcopy(task_meta.get("templateParams") or task_meta.get("template_params") or {})
        target_dept = str(task_meta.get("targetDept") or task_meta.get("target_dept") or assignee_org or "")
        if template_id:
            task_meta["templateId"] = template_id
        if template_params:
            task_meta["templateParams"] = template_params
        if target_dept:
            task_meta["targetDept"] = target_dept

        task = Task(
            trace_id=trace_id,
            title=title,
            description=description,
            priority=priority,
            state=initial_state,
            assignee_org=assignee_org,
            creator=creator,
            tags=tags or [],
            org=target_org,
            official=creator,
            now=description or "任务创建",
            target_dept=target_dept,
            flow_log=[
                {
                    "from": None,
                    "to": initial_state.value,
                    "agent": "system",
                    "reason": "任务创建",
                    "ts": now.isoformat(),
                }
            ],
            progress_log=[],
            todos=[],
            scheduler={},
            template_id=template_id,
            template_params=template_params,
            meta=task_meta,
        )
        self.db.add(task)
        await self.db.flush()

        # 事件写入 outbox — 与 task 同一事务，原子提交
        outbox = OutboxEvent(
            topic=TOPIC_TASK_CREATED,
            trace_id=trace_id,
            event_type="task.created",
            producer="task_service",
            payload={
                "task_id": str(task.task_id),
                "title": title,
                "state": initial_state.value,
                "priority": priority,
                "assignee_org": assignee_org,
            },
        )
        self.db.add(outbox)

        await self.db.commit()
        log.info(f"Created task {task.task_id}: {title} [{initial_state.value}]")
        return task

    # ── 状态流转 ──

    async def transition_state(
        self,
        task_id: uuid.UUID,
        new_state: TaskState,
        agent: str = "system",
        reason: str = "",
        skip_high_risk_gate: bool = False,
    ) -> Task:
        """执行状态流转。SELECT FOR UPDATE 防止并发 flow_log 丢失。"""
        # 行级排他锁 — 串行化同一任务的并发写入
        stmt = select(Task).where(Task.task_id == task_id).with_for_update()
        result = await self.db.execute(stmt)
        task = result.scalar_one_or_none()
        if task is None:
            raise ValueError(f"Task not found: {task_id}")

        old_state = task.state

        # 校验合法流转
        allowed = STATE_TRANSITIONS.get(old_state, set())
        if new_state not in allowed:
            raise ValueError(
                f"Invalid transition: {old_state.value} → {new_state.value}. "
                f"Allowed: {[s.value for s in allowed]}"
            )

        now = datetime.now(timezone.utc)
        meta = copy.deepcopy(task.meta or {})
        requested_target_state = (meta.get("pending_confirm") or {}).get("target_state")
        target_state = new_state

        if not skip_high_risk_gate and (old_state, new_state) in _HIGH_RISK_TRANSITIONS:
            task.state = TaskState.PendingConfirm
            task.org = Task.org_for_state(TaskState.PendingConfirm, task.assignee_org)
            task.now = reason or f"待确认: {old_state.value}→{new_state.value}"
            meta["pending_confirm"] = {
                "target_state": new_state.value,
                "source_state": old_state.value,
                "requested_by": agent,
                "requested_at": now.isoformat(),
                "confirm_by": _CONFIRM_AUTHORITY.get(old_state, "shangshu"),
                "risk_key": f"{old_state.value}->{new_state.value}",
                "status": "pending",
            }
            gate_checks = list(meta.get("gate_checks") or [])
            gate_checks.append(
                {
                    "at": now.isoformat(),
                    "gate": "high_risk_transition",
                    "from": old_state.value,
                    "to": new_state.value,
                    "confirm_by": _CONFIRM_AUTHORITY.get(old_state, "shangshu"),
                    "result": "pending",
                }
            )
            meta["gate_checks"] = gate_checks
            effective_new_state = TaskState.PendingConfirm
            effective_reason = task.now
        else:
            task.state = new_state
            task.org = Task.org_for_state(new_state, task.assignee_org)
            if reason:
                task.now = reason
            if old_state == TaskState.PendingConfirm:
                pending = meta.get("pending_confirm") or {}
                gate_checks = list(meta.get("gate_checks") or [])
                gate_from = gate_checks[-1].get("from") if gate_checks else pending.get("source_state", "PendingConfirm")
                gate_to = pending.get("target_state") or requested_target_state or new_state.value
                gate_checks.append(
                    {
                        "at": now.isoformat(),
                        "gate": "high_risk_transition",
                        "from": gate_from,
                        "to": gate_to,
                        "confirm_by": pending.get("confirm_by"),
                        "risk_key": pending.get("risk_key"),
                        "result": "approved" if (requested_target_state and new_state.value == requested_target_state) else "rejected",
                    }
                )
                meta["gate_checks"] = gate_checks
                meta.pop("pending_confirm", None)
            effective_new_state = new_state
            effective_reason = reason

        if effective_new_state in TERMINAL_STATES:
            memory_extracted = dict(meta.get("memory_extracted") or {})
            event_key = "done" if effective_new_state == TaskState.Done else "blocked"
            memory_extracted.setdefault(
                event_key,
                {
                    "at": now.isoformat(),
                    "agent": agent,
                    "source": "api-transition",
                },
            )
            meta["memory_extracted"] = memory_extracted

        task.meta = meta
        task.updated_at = now

        # 在行锁保护下安全追加 flow_log
        flow_entry = {
            "from": old_state.value,
            "to": effective_new_state.value,
            "agent": agent,
            "reason": effective_reason,
            "ts": now.isoformat(),
        }
        if task.flow_log is None:
            task.flow_log = []
        task.flow_log = [*task.flow_log, flow_entry]

        # 事件写入 outbox（同一事务）
        topic = TOPIC_TASK_COMPLETED if effective_new_state in TERMINAL_STATES else TOPIC_TASK_STATUS
        outbox = OutboxEvent(
            topic=topic,
            trace_id=str(task.trace_id),
            event_type=f"task.state.{effective_new_state.value}",
            producer=agent,
            payload={
                "task_id": str(task_id),
                "from": old_state.value,
                "to": effective_new_state.value,
                "reason": effective_reason,
                "assignee_org": task.assignee_org,
            },
        )
        self.db.add(outbox)

        await self.db.commit()
        if effective_new_state == TaskState.PendingConfirm:
            if send_pending_confirm_notification(task, source_state=old_state.value, target_state=target_state.value):
                meta = copy.deepcopy(task.meta or {})
                notifications = dict(meta.get("notifications") or {})
                notifications["pending_confirm_sent"] = True
                notifications["pending_confirm_sent_at"] = datetime.now(timezone.utc).isoformat()
                meta["notifications"] = notifications
                task.meta = meta
                task.updated_at = datetime.now(timezone.utc)
                await self.db.commit()
        elif old_state == TaskState.PendingConfirm:
            action = "approve" if (requested_target_state and effective_new_state.value == requested_target_state) else "reject"
            if send_review_result_notification(task, action=action, comment=reason):
                meta = copy.deepcopy(task.meta or {})
                notifications = dict(meta.get("notifications") or {})
                notifications["review_result_sent"] = action
                notifications["review_result_sent_at"] = datetime.now(timezone.utc).isoformat()
                meta["notifications"] = notifications
                task.meta = meta
                task.updated_at = datetime.now(timezone.utc)
                await self.db.commit()
        log.info(f"Task {task_id} state: {old_state.value} → {effective_new_state.value} by {agent}")
        return task

    async def review_action(
        self,
        task_id: uuid.UUID,
        action: str,
        comment: str = "",
        agent: str = "menxia",
    ) -> Task:
        action = str(action or "").strip().lower()
        if action not in {"approve", "reject"}:
            raise ValueError(f"Unknown review action: {action}")

        current = await self.get_task(task_id)
        if current.state not in {TaskState.Review, TaskState.Menxia, TaskState.PendingConfirm}:
            raise ValueError(f"Task {task_id} current state is {current.state.value}, review not allowed")

        old_state = current.state
        review_summary = self._summarize_text(comment)

        if action == "approve":
            if old_state == TaskState.PendingConfirm:
                pending = (current.meta or {}).get("pending_confirm") or {}
                target_name = str(pending.get("target_state") or TaskState.Done.value)
                try:
                    target_state = TaskState(target_name)
                except ValueError:
                    target_state = TaskState.Done
                task = await self.transition_state(task_id, target_state, agent=agent, reason=comment or "门禁确认通过")
                if target_state == TaskState.Done:
                    task.now = "御批通过，任务完成"
                elif target_state == TaskState.Cancelled:
                    task.now = "御批同意撤销"
                else:
                    task.now = f"御批通过，转入 {target_state.value}"
            elif old_state == TaskState.Menxia:
                task = await self.transition_state(task_id, TaskState.Assigned, agent=agent, reason=comment or "门下省审议通过")
                task.now = "门下省准奏，移交尚书省派发"
            else:
                task = await self.transition_state(task_id, TaskState.Done, agent=agent, reason=comment or "审查通过", skip_high_risk_gate=True)
                task.now = "御批通过，任务完成"
        else:
            round_num = int((current.meta or {}).get("review_round") or 0) + 1
            task = await self.transition_state(task_id, TaskState.Zhongshu, agent=agent, reason=comment or "需要修改")
            meta = copy.deepcopy(task.meta or {})
            meta["review_round"] = round_num
            task.meta = meta
            task.now = f"封驳退回中书省修订（第{round_num}轮）"

        if review_summary:
            progress_entry = {
                "agent": agent,
                "content": f"review:{action} · {review_summary}",
                "ts": datetime.now(timezone.utc).isoformat(),
            }
            if task.progress_log is None:
                task.progress_log = []
            task.progress_log = [*task.progress_log, progress_entry]
            if action == "approve" and task.state == TaskState.Done:
                task.output = comment

        task.updated_at = datetime.now(timezone.utc)
        await self.db.commit()

        if old_state != TaskState.PendingConfirm:
            if send_review_result_notification(task, action=action, comment=comment):
                meta = copy.deepcopy(task.meta or {})
                notifications = dict(meta.get("notifications") or {})
                notifications["review_result_sent"] = action
                notifications["review_result_sent_at"] = datetime.now(timezone.utc).isoformat()
                meta["notifications"] = notifications
                task.meta = meta
                task.updated_at = datetime.now(timezone.utc)
                await self.db.commit()

        return task

    # ── 派发请求 ──

    async def request_dispatch(
        self,
        task_id: uuid.UUID,
        target_agent: str,
        message: str = "",
    ):
        """发布 task.dispatch 事件到 outbox，由 OutboxRelay 投递后 DispatchWorker 消费。"""
        task = await self._get_task(task_id)
        data = task.to_dict()
        outbox = OutboxEvent(
            topic=TOPIC_TASK_DISPATCH,
            trace_id=str(task.trace_id),
            event_type="task.dispatch.request",
            producer="task_service",
            payload={
                "task_id": str(task_id),
                "agent": target_agent,
                "message": message,
                "state": task.state.value,
                "title": data.get("title", ""),
                "description": data.get("description", ""),
                "org": data.get("assignee_org") or data.get("org") or "",
                "priority": data.get("priority", "中"),
                "tags": data.get("tags", []),
                "todos": data.get("todos", []),
                "flow_log": (data.get("flow_log") or [])[-5:],
                "progress_log": (data.get("progress_log") or [])[-3:],
                "block": data.get("block", ""),
                "meta": data.get("meta", {}),
            },
        )
        self.db.add(outbox)
        await self.db.commit()
        log.info(f"Dispatch requested: task {task_id} → agent {target_agent}")

    # ── 进度/备注更新 ──

    async def add_progress(
        self,
        task_id: uuid.UUID,
        agent: str,
        content: str,
        resource: dict[str, Any] | None = None,
    ) -> Task:
        task = await self._get_task(task_id)
        summary = self._summarize_text(content)
        entry = {
            "agent": agent,
            "content": content,
            "text": summary,
            "ts": datetime.now(timezone.utc).isoformat(),
        }
        for key in ("tokens", "cost", "model", "elapsed", "usage"):
            value = (resource or {}).get(key)
            if value is not None:
                entry[key] = value
        if task.progress_log is None:
            task.progress_log = []
        task.progress_log = [*task.progress_log, entry]
        if summary:
            task.now = summary
        task.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        return task

    async def update_todos(
        self,
        task_id: uuid.UUID,
        todos: list[dict],
    ) -> Task:
        task = await self._get_task(task_id)
        task.todos = todos
        task.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        return task

    async def update_scheduler(
        self,
        task_id: uuid.UUID,
        scheduler: dict,
    ) -> Task:
        task = await self._get_task(task_id)
        task.scheduler = scheduler
        task.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        return task

    async def update_assignee_org(
        self,
        task_id: uuid.UUID,
        assignee_org: str,
        agent: str = "system",
        reason: str = "",
    ) -> Task:
        task = await self._get_task(task_id)
        now = datetime.now(timezone.utc)
        old_target = task.assignee_org or task.target_dept or task.org or ""
        new_target = str(assignee_org or "").strip()
        if not new_target:
            raise ValueError("assignee_org is required")

        task.assignee_org = new_target
        task.target_dept = new_target
        if task.state in {TaskState.Doing, TaskState.Next}:
            task.org = Task.org_for_state(task.state, new_target)

        meta = copy.deepcopy(task.meta or {})
        meta["targetDept"] = new_target
        task.meta = meta
        task.updated_at = now

        flow_entry = {
            "from": old_target or task.org or "",
            "to": new_target,
            "agent": agent,
            "reason": reason or f"改派至{new_target}",
            "ts": now.isoformat(),
        }
        if task.flow_log is None:
            task.flow_log = []
        task.flow_log = [*task.flow_log, flow_entry]

        await self.db.commit()
        return task

    # ── 查询 ──

    async def get_task(self, task_id: uuid.UUID) -> Task:
        return await self._get_task(task_id)

    async def list_tasks(
        self,
        state: TaskState | None = None,
        assignee_org: str | None = None,
        priority: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Task]:
        stmt = select(Task)
        conditions = []
        if state is not None:
            conditions.append(Task.state == state)
        if assignee_org is not None:
            conditions.append(Task.assignee_org == assignee_org)
        if priority is not None:
            conditions.append(Task.priority == priority)
        if conditions:
            stmt = stmt.where(and_(*conditions))
        stmt = stmt.order_by(Task.created_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_live_status(self) -> dict[str, Any]:
        """生成兼容旧 live_status.json 格式的全局状态。"""
        tasks = await self.list_tasks(limit=200)
        active_tasks = {}
        completed_tasks = {}
        for t in tasks:
            d = t.to_dict()
            if t.state in TERMINAL_STATES:
                completed_tasks[str(t.task_id)] = d
            else:
                active_tasks[str(t.task_id)] = d
        return {
            "tasks": active_tasks,
            "completed_tasks": completed_tasks,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

    async def count_tasks(self, state: TaskState | None = None) -> int:
        stmt = select(func.count(Task.task_id))
        if state is not None:
            stmt = stmt.where(Task.state == state)
        result = await self.db.execute(stmt)
        return result.scalar_one()

    # ── 内部 ──

    async def _get_task(self, task_id: uuid.UUID) -> Task:
        if isinstance(task_id, str):
            task_id = uuid.UUID(task_id)
        task = await self.db.get(Task, task_id)
        if task is None:
            raise ValueError(f"Task not found: {task_id}")
        return task
