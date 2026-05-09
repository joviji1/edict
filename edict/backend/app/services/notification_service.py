from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from urllib.parse import quote

from ..channels import get_channel
from ..config import get_settings

log = logging.getLogger('edict.notification_service')

_DASHBOARD_PORT = 7892


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _resolve_data_dir(base_dir: str | Path | None = None) -> Path:
    if base_dir:
        return Path(base_dir)

    settings = get_settings()
    candidates: list[Path] = []

    edict_home = str(os.environ.get('EDICT_HOME') or '').strip()
    if edict_home:
        home = Path(edict_home)
        candidates.extend([home / 'data', home])

    project_dir = str(getattr(settings, 'openclaw_project_dir', '') or '').strip()
    if project_dir:
        root = Path(project_dir)
        candidates.extend([root / 'data', root])

    candidates.append(_repo_root() / 'data')

    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            return candidate

    return candidates[0]


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {}


def load_notification_settings(base_dir: str | Path | None = None) -> dict | None:
    base = _resolve_data_dir(base_dir)
    cfg = _read_json(base / 'morning_brief_config.json')
    notification = cfg.get('notification', {})
    if not notification and cfg.get('feishu_webhook'):
        notification = {'enabled': True, 'channel': 'feishu', 'webhook': cfg['feishu_webhook']}
    if not notification.get('enabled', True):
        return None

    webhook = str(notification.get('webhook', '')).strip()
    if not webhook:
        return None

    channel_type = str(notification.get('channel', 'feishu')).strip() or 'feishu'
    channel_cls = get_channel(channel_type)
    if not channel_cls:
        log.warning('未知的通知渠道: %s', channel_type)
        return None
    if not channel_cls.validate_webhook(webhook):
        log.warning('%s Webhook URL 不合法: %s', channel_cls.label, webhook)
        return None
    return {'channel_cls': channel_cls, 'webhook': webhook}


def send_custom_notification(title: str, content: str, url: str | None = None, base_dir: str | Path | None = None) -> bool:
    settings = load_notification_settings(base_dir)
    if not settings:
        return False
    try:
        return bool(settings['channel_cls'].send(settings['webhook'], title, content, url))
    except Exception as exc:
        log.warning('发送通知失败: %s', exc)
        return False


def task_notification_url(task_id: str) -> str:
    return f'http://127.0.0.1:{_DASHBOARD_PORT}/?taskId={quote(str(task_id))}'


def _task_meta(task) -> dict:
    meta = task.meta or {}
    if not isinstance(meta, dict):
        meta = {}
    return meta


def _task_notifications(task) -> dict:
    meta = _task_meta(task)
    notifications = meta.get('notifications') or {}
    if not isinstance(notifications, dict):
        notifications = {}
    meta['notifications'] = notifications
    task.meta = meta
    return notifications


def send_pending_confirm_notification(task, *, source_state: str = '', target_state: str = '', base_dir: str | Path | None = None) -> bool:
    notifications = _task_notifications(task)
    if notifications.get('pending_confirm_sent'):
        return False

    meta = _task_meta(task)
    pending = meta.get('pending_confirm') or {}
    gate_checks = list(meta.get('gate_checks') or [])
    gate_from = source_state or (gate_checks[-1].get('from') if gate_checks else '') or pending.get('source_state') or 'Unknown'
    gate_to = target_state or pending.get('target_state') or 'Unknown'

    title = f'⏳ 待审批 · {task.title or str(task.task_id)}'
    content = (
        f'任务：{task.task_id}\n'
        f'标题：{task.title or "-"}\n'
        f'当前状态：PendingConfirm\n'
        f'风险门禁：{gate_from} → {gate_to}\n'
        f'申请部门：{pending.get("requested_by") or task.org or "-"}\n'
        f'审批人：{pending.get("confirm_by") or "-"}\n'
        f'说明：{task.now or "待门禁审批"}'
    )
    if not send_custom_notification(title, content, task_notification_url(str(task.task_id)), base_dir=base_dir):
        return False

    notifications['pending_confirm_sent'] = True
    notifications['pending_confirm_sent_at'] = task.updated_at.isoformat() if task.updated_at else ''
    meta['notifications'] = notifications
    task.meta = meta
    return True


def send_review_result_notification(task, *, action: str, comment: str = '', base_dir: str | Path | None = None) -> bool:
    notifications = _task_notifications(task)
    if notifications.get('review_result_sent') == action:
        return False

    label = '已准奏' if action == 'approve' else '已封驳'
    title = f'📣 审批结果 · {task.title or str(task.task_id)}'
    content = (
        f'任务：{task.task_id}\n'
        f'标题：{task.title or "-"}\n'
        f'审批结果：{label}\n'
        f'当前状态：{task.state.value if hasattr(task.state, "value") else task.state}\n'
        f'当前说明：{task.now or "-"}\n'
        f'批注：{comment or "无"}'
    )
    if not send_custom_notification(title, content, task_notification_url(str(task.task_id)), base_dir=base_dir):
        return False

    notifications['review_result_sent'] = action
    notifications['review_result_sent_at'] = task.updated_at.isoformat() if task.updated_at else ''
    meta = _task_meta(task)
    meta['notifications'] = notifications
    task.meta = meta
    return True