"""Legacy 兼容路由 — 通过旧版 task_id (JJC-xxx) 操作任务。

旧版 kanban_update.py 使用自定义 ID (JJC-20260301-007)，
Edict 使用 UUID。此路由通过 tags 或 meta.legacy_id 映射。from __future__ import annotations"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models.task import Task, TaskState
from ..services.event_bus import get_event_bus
from ..services.task_service import TaskService

log = logging.getLogger("edict.api.legacy")
router = APIRouter()


async def _find_by_legacy_id(db: AsyncSession, legacy_id: str) -> Task | None:
    """通过旧版 ID 查找任务（优先 meta.legacy_id，其次 tags）。

    兼容 SQLite 测试环境，避免依赖 PostgreSQL JSON/ARRAY 专属操作符。
    """
    stmt = select(Task)
    result = await db.execute(stmt)
    for task in result.scalars().all():
        meta = task.meta or {}
        if isinstance(meta, dict) and str(meta.get("legacy_id") or "").strip() == legacy_id:
            return task
        tags = task.tags or []
        if isinstance(tags, list) and legacy_id in tags:
            return task
    return None


class LegacyTransition(BaseModel):
    new_state: str
    agent: str = "system"
    reason: str = ""


class LegacyProgress(BaseModel):
    agent: str
    content: str


class LegacyTodoUpdate(BaseModel):
    todos: list[dict]


class LegacyDispatchTarget(BaseModel):
    target_dept: str
    agent: str = "shangshu"
    reason: str = ""


class LegacyReviewAction(BaseModel):
    action: str
    comment: str = ""
    agent: str = "menxia"


@router.post("/by-legacy/{legacy_id}/transition")
async def legacy_transition(
    legacy_id: str,
    body: LegacyTransition,
    db: AsyncSession = Depends(get_db),
):
    task = await _find_by_legacy_id(db, legacy_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Legacy task not found: {legacy_id}")

    bus = await get_event_bus()
    svc = TaskService(db, bus)
    try:
        new_state = TaskState(body.new_state)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid state: {body.new_state}")

    try:
        t = await svc.transition_state(task.task_id, new_state, body.agent, body.reason)
        return {"task_id": str(t.task_id), "state": t.state.value}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/by-legacy/{legacy_id}/progress")
async def legacy_progress(
    legacy_id: str,
    body: LegacyProgress,
    db: AsyncSession = Depends(get_db),
):
    task = await _find_by_legacy_id(db, legacy_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Legacy task not found: {legacy_id}")

    bus = await get_event_bus()
    svc = TaskService(db, bus)
    await svc.add_progress(task.task_id, body.agent, body.content)
    return {"message": "ok"}


@router.put("/by-legacy/{legacy_id}/todos")
async def legacy_todos(
    legacy_id: str,
    body: LegacyTodoUpdate,
    db: AsyncSession = Depends(get_db),
):
    task = await _find_by_legacy_id(db, legacy_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Legacy task not found: {legacy_id}")

    bus = await get_event_bus()
    svc = TaskService(db, bus)
    await svc.update_todos(task.task_id, body.todos)
    return {"message": "ok"}


@router.post("/by-legacy/{legacy_id}/dispatch-target")
async def legacy_dispatch_target(
    legacy_id: str,
    body: LegacyDispatchTarget,
    db: AsyncSession = Depends(get_db),
):
    task = await _find_by_legacy_id(db, legacy_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Legacy task not found: {legacy_id}")

    bus = await get_event_bus()
    svc = TaskService(db, bus)
    updated = await svc.update_assignee_org(task.task_id, body.target_dept, body.agent, body.reason)
    return updated.to_dict()


@router.post("/by-legacy/{legacy_id}/review-action")
async def legacy_review_action(
    legacy_id: str,
    body: LegacyReviewAction,
    db: AsyncSession = Depends(get_db),
):
    task = await _find_by_legacy_id(db, legacy_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Legacy task not found: {legacy_id}")

    bus = await get_event_bus()
    svc = TaskService(db, bus)
    try:
        updated = await svc.review_action(task.task_id, action=body.action, comment=body.comment, agent=body.agent)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    data = updated.to_dict()
    return {
        "ok": True,
        "task_id": str(updated.task_id),
        "state": data["state"],
        "review_round": data.get("review_round", 0),
        "message": f'{legacy_id} {"已准奏" if body.action == "approve" else "已封驳"}',
    }


@router.get("/by-legacy/{legacy_id}")
async def legacy_get(
    legacy_id: str,
    db: AsyncSession = Depends(get_db),
):
    task = await _find_by_legacy_id(db, legacy_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Legacy task not found: {legacy_id}")
    return task.to_dict()
