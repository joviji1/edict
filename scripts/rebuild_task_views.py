#!/usr/bin/env python3
"""重建任务聚合视图：runtime + governance samples + JJC archive → tasks_source.json。"""
import copy
import datetime
import json
import pathlib
import logging
import os

from file_lock import atomic_json_write, atomic_json_read

log = logging.getLogger('rebuild_task_views')
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(message)s', datefmt='%H:%M:%S')

BASE = pathlib.Path(__file__).resolve().parent.parent
DATA = pathlib.Path(os.environ.get('EDICT_DATA_DIR', str(BASE / 'data'))).resolve()
DATA.mkdir(exist_ok=True)
RUNTIME_FILE = DATA / 'tasks_runtime_view.json'
SAMPLES_FILE = DATA / 'tasks_governance_samples.json'
ARCHIVE_FILE = DATA / 'tasks_jjc_archive.json'
TASKS_FILE = DATA / 'tasks_source.json'
MAX_ARCHIVE_ITEMS = 10
MAX_SAMPLE_ITEMS = 50


def parse_dt(value):
    if not value:
        return None
    try:
        if isinstance(value, (int, float)):
            ts = float(value)
            if ts > 1e12:
                ts /= 1000.0
            return datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc)
        return datetime.datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    except Exception:
        return None


def task_key(task):
    if not isinstance(task, dict):
        return ''
    task_id = str(task.get('id') or '').strip()
    if task_id:
        return task_id
    meta = task.get('sourceMeta') or {}
    session_id = str(meta.get('sessionId') or '').strip()
    if session_id:
        return f'session:{session_id}'
    session_key = str(meta.get('sessionKey') or '').strip()
    if session_key:
        return f'session_key:{session_key}'
    return ''


def sort_key(task):
    for value in (
        task.get('sampleLastSeenAt'),
        task.get('updatedAt'),
        task.get('sampleCapturedAt'),
        (task.get('pending_confirm') or {}).get('requested_at'),
        (task.get('sourceMeta') or {}).get('updatedAt'),
    ):
        dt = parse_dt(value)
        if dt:
            return dt
    return datetime.datetime.fromtimestamp(0, tz=datetime.timezone.utc)


def migrate_jjc_archive(existing_tasks, existing_archive):
    merged = {}
    for task in existing_archive:
        key = task_key(task)
        if key:
            item = copy.deepcopy(task)
            item['sourceLayer'] = 'jjc_archive'
            merged[key] = item
    for task in existing_tasks:
        if not str(task.get('id', '')).startswith('JJC'):
            continue
        key = task_key(task)
        if not key:
            continue
        item = copy.deepcopy(task)
        item['sourceLayer'] = 'jjc_archive'
        merged[key] = item
    archive = list(merged.values())
    archive.sort(key=sort_key, reverse=True)
    return archive


def tagged(items, layer, limit=None):
    rows = []
    for task in items[:limit] if limit else items:
        item = copy.deepcopy(task)
        item['sourceLayer'] = layer
        rows.append(item)
    return rows


def dedupe(items):
    merged = {}
    order = []
    stateful_fields = {
        'state', 'org', 'updatedAt', 'now', '_scheduler', 'progress_log', 'flow_log', 'block', 'output'
    }

    def _candidate_dt(task):
        return sort_key(task)

    for task in items:
        key = task_key(task)
        if not key:
            continue
        if key not in merged:
            merged[key] = copy.deepcopy(task)
            order.append(key)
        else:
            base = merged[key]
            base_dt = _candidate_dt(base)
            task_dt = _candidate_dt(task)
            newer_or_equal = task_dt >= base_dt
            for k, v in task.items():
                if k not in base or base[k] in (None, '', [], {}):
                    base[k] = copy.deepcopy(v)
                elif k in stateful_fields and newer_or_equal:
                    base[k] = copy.deepcopy(v)
                elif isinstance(base[k], dict) and isinstance(v, dict):
                    nv = copy.deepcopy(base[k])
                    nv.update(v)
                    base[k] = nv
    rows = [merged[key] for key in order]
    rows.sort(key=sort_key, reverse=True)
    return rows


def main():
    runtime_tasks = atomic_json_read(RUNTIME_FILE, [])
    governance_samples = atomic_json_read(SAMPLES_FILE, [])
    existing_tasks = atomic_json_read(TASKS_FILE, [])
    existing_archive = atomic_json_read(ARCHIVE_FILE, [])

    archive = migrate_jjc_archive(existing_tasks, existing_archive)
    atomic_json_write(ARCHIVE_FILE, archive)

    aggregate = dedupe(
        tagged(runtime_tasks, 'runtime')
        + tagged(governance_samples, 'governance_sample', MAX_SAMPLE_ITEMS)
        + tagged(archive, 'jjc_archive', MAX_ARCHIVE_ITEMS)
    )
    atomic_json_write(TASKS_FILE, aggregate)
    log.info('rebuilt task views | runtime=%s governance=%s archive=%s aggregate=%s', len(runtime_tasks), len(governance_samples), len(archive), len(aggregate))


if __name__ == '__main__':
    main()
