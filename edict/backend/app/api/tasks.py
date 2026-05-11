"""Tasks API — 任务的 CRUD 和状态流转。"""
from __future__ import annotations

import uuid
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models.task import TaskState
from ..services.event_bus import EventBus, get_event_bus
from ..services.task_service import TaskService

log = logging.getLogger("edict.api.tasks")
router = APIRouter()


# ── Schemas ──

class TaskCreate(BaseModel):
    title: str
    description: str = ""
    priority: str = "中"
    assignee_org: str | None = None
    creator: str = "emperor"
    tags: list[str] = []
    meta: dict | None = None
    templateId: str = ""
    templateParams: dict | None = None
    targetDept: str = ""
    pending_confirm: dict | None = None
    notifications: dict | None = None
    gate_checks: list[dict] | None = None


class TaskTransition(BaseModel):
    new_state: str
    agent: str = "system"
    reason: str = ""


class TaskProgress(BaseModel):
    agent: str
    content: str


class TaskTodoUpdate(BaseModel):
    todos: list[dict]


class TaskSchedulerUpdate(BaseModel):
    scheduler: dict


class TaskReviewAction(BaseModel):
    action: str
    comment: str = ""
    agent: str = "menxia"


class TaskOut(BaseModel):
    task_id: str
    trace_id: str
    title: str
    description: str
    priority: str
    state: str
    assignee_org: str | None
    creator: str
    tags: list[str]
    flow_log: list
    progress_log: list
    todos: list
    scheduler: dict | None
    created_at: str
    updated_at: str

    model_config = ConfigDict(from_attributes=True)


# ── 依赖注入 helper ──

async def get_task_service(
    db: AsyncSession = Depends(get_db),
) -> TaskService:
    bus = await get_event_bus()
    return TaskService(db, bus)


# ── Endpoints ──

@router.get("")
async def list_tasks(
    state: str | None = None,
    assignee_org: str | None = None,
    priority: str | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    svc: TaskService = Depends(get_task_service),
):
    """获取任务列表。"""
    task_state = TaskState(state) if state else None
    tasks = await svc.list_tasks(
        state=task_state,
        assignee_org=assignee_org,
        priority=priority,
        limit=limit,
        offset=offset,
    )
    return {"tasks": [t.to_dict() for t in tasks], "count": len(tasks)}


@router.get("/live-status")
async def live_status(svc: TaskService = Depends(get_task_service)):
    """兼容旧 live_status.json 格式的全局状态。"""
    return await svc.get_live_status()


@router.get("/stats")
async def task_stats(svc: TaskService = Depends(get_task_service)):
    """任务统计。"""
    stats = {}
    for s in TaskState:
        stats[s.value] = await svc.count_tasks(s)
    total = sum(stats.values())
    return {"total": total, "by_state": stats}


@router.post("", status_code=201)
async def create_task(
    body: TaskCreate,
    svc: TaskService = Depends(get_task_service),
):
    """创建新任务。"""
    task_meta = dict(body.meta or {})
    if body.templateId:
        task_meta["templateId"] = body.templateId
    if body.templateParams:
        task_meta["templateParams"] = body.templateParams
    if body.targetDept:
        task_meta["targetDept"] = body.targetDept
    if body.pending_confirm:
        task_meta["pending_confirm"] = body.pending_confirm
    if body.notifications:
        task_meta["notifications"] = body.notifications
    if body.gate_checks:
        task_meta["gate_checks"] = body.gate_checks
    assignee_org = body.assignee_org or body.targetDept or None
    task = await svc.create_task(
        title=body.title,
        description=body.description,
        priority=body.priority,
        assignee_org=assignee_org,
        creator=body.creator,
        tags=body.tags,
        meta=task_meta,
    )
    return {"task_id": str(task.task_id), "trace_id": str(task.trace_id), "state": task.state.value}


@router.get("/{task_id}")
async def get_task(
    task_id: uuid.UUID,
    svc: TaskService = Depends(get_task_service),
):
    """获取任务详情。"""
    try:
        task = await svc.get_task(task_id)
        return task.to_dict()
    except ValueError:
        raise HTTPException(status_code=404, detail="Task not found")


@router.post("/{task_id}/transition")
async def transition_task(
    task_id: uuid.UUID,
    body: TaskTransition,
    svc: TaskService = Depends(get_task_service),
):
    """执行状态流转。"""
    try:
        new_state = TaskState(body.new_state)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid state: {body.new_state}")

    try:
        task = await svc.transition_state(
            task_id=task_id,
            new_state=new_state,
            agent=body.agent,
            reason=body.reason,
        )
        return {"task_id": str(task.task_id), "state": task.state.value, "message": "ok"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{task_id}/dispatch")
async def dispatch_task(
    task_id: uuid.UUID,
    agent: str = Query(description="目标 agent"),
    message: str = Query(default="", description="派发消息"),
    svc: TaskService = Depends(get_task_service),
):
    """手动派发任务给指定 agent。"""
    try:
        await svc.request_dispatch(task_id, agent, message)
        return {"message": "dispatch requested", "agent": agent}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{task_id}/review-action")
async def review_action(
    task_id: uuid.UUID,
    body: TaskReviewAction,
    svc: TaskService = Depends(get_task_service),
):
    try:
        task = await svc.review_action(task_id, action=body.action, comment=body.comment, agent=body.agent)
        data = task.to_dict()
        return {
            "ok": True,
            "task_id": str(task.task_id),
            "state": data["state"],
            "review_round": data.get("review_round", 0),
            "message": f'{data["id"]} {"已准奏" if body.action == "approve" else "已封驳"}',
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{task_id}/progress")
async def add_progress(
    task_id: uuid.UUID,
    body: TaskProgress,
    svc: TaskService = Depends(get_task_service),
):
    """添加进度记录。"""
    try:
        await svc.add_progress(task_id, body.agent, body.content)
        return {"message": "ok"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{task_id}/todos")
async def update_todos(
    task_id: uuid.UUID,
    body: TaskTodoUpdate,
    svc: TaskService = Depends(get_task_service),
):
    """更新任务 TODO 清单。"""
    try:
        await svc.update_todos(task_id, body.todos)
        return {"message": "ok"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{task_id}/scheduler")
async def update_scheduler(
    task_id: uuid.UUID,
    body: TaskSchedulerUpdate,
    svc: TaskService = Depends(get_task_service),
):
    """更新任务排期信息。"""
    try:
        await svc.update_scheduler(task_id, body.scheduler)
        return {"message": "ok"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
