#!/usr/bin/env python3
"""把 backend `/api/tasks` 导出为旧看板兼容的 `tasks_source.json`。"""

from __future__ import annotations

import copy
import datetime
import json
import logging
import os
import pathlib
import urllib.error
import urllib.parse
import urllib.request

from file_lock import atomic_json_write

log = logging.getLogger('export_backend_tasks_to_legacy_json')
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(message)s', datefmt='%H:%M:%S')

BASE = pathlib.Path(__file__).resolve().parent.parent
DATA = pathlib.Path(os.environ.get('EDICT_DATA_DIR', str(BASE / 'data'))).resolve()
DATA.mkdir(exist_ok=True)
TASKS_FILE = DATA / 'tasks_source.json'
EXPORT_META_FILE = DATA / 'tasks_backend_export_meta.json'
BACKEND_URL = os.environ.get('EDICT_BACKEND_URL', 'http://127.0.0.1:18000').rstrip('/')
LIST_LIMIT = int(os.environ.get('EDICT_BACKEND_EXPORT_LIMIT', '200'))
TIMEOUT = float(os.environ.get('EDICT_BACKEND_EXPORT_TIMEOUT', '10'))
ALLOW_EMPTY = str(os.environ.get('EDICT_BACKEND_EXPORT_ALLOW_EMPTY', '')).strip().lower() in {'1', 'true', 'yes', 'on'}
PROBE_TAG_PREFIXES = ('PROBE-',)
PROBE_TITLE_MARKERS = ('[probe]',)


def now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def fetch_backend_tasks() -> list[dict]:
    query = urllib.parse.urlencode({'limit': LIST_LIMIT})
    url = f'{BACKEND_URL}/api/tasks?{query}'
    req = urllib.request.Request(url, headers={'Accept': 'application/json', 'User-Agent': 'edict-backend-export/1.0'})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        payload = json.loads(resp.read().decode('utf-8'))
    tasks = payload.get('tasks')
    if not isinstance(tasks, list):
        raise RuntimeError(f'unexpected backend payload: {payload!r}')
    return tasks


def transform_task(task: dict) -> dict:
    row = copy.deepcopy(task)
    task_id = str(row.get('id') or row.get('task_id') or '').strip()
    scheduler = row.get('_scheduler') or row.get('scheduler') or {}
    row['id'] = task_id
    row['task_id'] = str(row.get('task_id') or task_id)
    row['org'] = row.get('org') or row.get('assignee_org') or '太子'
    row['official'] = row.get('official') or row.get('creator') or ''
    row['now'] = row.get('now') or row.get('description') or ''
    row['eta'] = row.get('eta') or row.get('updatedAt') or row.get('updated_at') or '-'
    row['block'] = row.get('block') or '无'
    row['flow_log'] = list(row.get('flow_log') or [])
    row['progress_log'] = list(row.get('progress_log') or [])
    row['todos'] = list(row.get('todos') or [])
    row['templateId'] = row.get('templateId') or row.get('template_id') or ''
    row['templateParams'] = dict(row.get('templateParams') or row.get('template_params') or {})
    row['ac'] = row.get('ac') or ''
    row['targetDept'] = row.get('targetDept') or row.get('target_dept') or ''
    row['_scheduler'] = copy.deepcopy(scheduler)
    row['pending_confirm'] = copy.deepcopy(row.get('pending_confirm') or row.get('pendingConfirm') or None)
    row['gate_checks'] = list(row.get('gate_checks') or row.get('gateChecks') or [])
    row['memory_extracted'] = copy.deepcopy(row.get('memory_extracted') or row.get('memoryExtracted') or {})
    row['createdAt'] = row.get('createdAt') or row.get('created_at') or ''
    row['updatedAt'] = row.get('updatedAt') or row.get('updated_at') or ''
    row['sourceLayer'] = 'backend_export'
    return row


def is_temporary_probe_task(task: dict) -> bool:
    tags = task.get('tags') or []
    for tag in tags:
        text = str(tag or '').strip().upper()
        if any(text.startswith(prefix) for prefix in PROBE_TAG_PREFIXES):
            return True

    title = str(task.get('title') or '').strip().lower()
    if any(marker in title for marker in PROBE_TITLE_MARKERS):
        return True

    meta = task.get('meta') or {}
    legacy_id = str(meta.get('legacy_id') or '').strip().upper()
    if any(legacy_id.startswith(prefix) for prefix in PROBE_TAG_PREFIXES):
        return True

    source = str(meta.get('source') or '').strip().lower()
    if source.endswith('.probe'):
        return True

    creator = str(task.get('creator') or '').strip().lower()
    if creator.endswith('-audit') and '[probe]' in title:
        return True

    return False


def build_export_meta(tasks: list[dict]) -> dict:
    return {
        'taskSource': 'backend_api_export',
        'backendUrl': BACKEND_URL,
        'count': len(tasks),
        'exportedAt': now_iso(),
        'tasksFile': str(TASKS_FILE),
    }


def main() -> int:
    try:
        raw_tasks = fetch_backend_tasks()
        tasks = [transform_task(task) for task in raw_tasks if not is_temporary_probe_task(task)]
    except Exception as exc:
        log.error('backend export failed: %s', exc)
        return 1

    if not tasks and not ALLOW_EMPTY:
        log.warning('backend export fetched 0 tasks; skip overwrite because ALLOW_EMPTY=false')
        return 2

    atomic_json_write(TASKS_FILE, tasks)
    atomic_json_write(EXPORT_META_FILE, build_export_meta(tasks))
    log.info('exported backend tasks -> %s | count=%s', TASKS_FILE, len(tasks))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
