#!/usr/bin/env python3
"""从多来源抽取治理样本，持久化到 data/tasks_governance_samples.json。"""
import copy
import datetime
import json
import pathlib
import logging
import os

from file_lock import atomic_json_write, atomic_json_read

log = logging.getLogger('governance_samples')
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(message)s', datefmt='%H:%M:%S')

BASE = pathlib.Path(__file__).resolve().parent.parent
DATA = pathlib.Path(os.environ.get('EDICT_DATA_DIR', str(BASE / 'data'))).resolve()
DATA.mkdir(exist_ok=True)
SAMPLES_FILE = DATA / 'tasks_governance_samples.json'
RUNTIME_FILE = DATA / 'tasks_runtime_view.json'
LEGACY_TASKS_FILE = DATA / 'tasks_source.json'
MISSION_FILE = DATA / 'mission_control_tasks.json'
MANUAL_FILE = DATA / 'manual_parallel_tasks.json'
MAX_AGE_DAYS = 14
PROBE_TAG_PREFIXES = ('PROBE-',)
PROBE_TITLE_MARKERS = ('[probe]',)
PROBE_TEXT_MARKERS = ('[probe]', 'PROBE-', '_probe_backups')

GOVERNANCE_FIELDS = (
    'pending_confirm',
    'gate_checks',
    'review_round',
    'templateId',
    'templateParams',
    'targetDept',
    'autopsy',
    'notifications',
)

CLEAR_WHEN_RESOLVED_RULES = {
    'pending_confirm': lambda task: str(task.get('state') or '').strip() not in ('', 'PendingConfirm'),
    'review_round': lambda task: str(task.get('state') or '').strip() in {'Done', 'Closed', 'Cancelled'},
    'autopsy': lambda task: str(task.get('state') or '').strip() in {'Done', 'Closed'},
}


def rj(path, default):
    try:
        return json.loads(pathlib.Path(path).read_text(encoding='utf-8'))
    except Exception:
        return default


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def parse_dt(value):
    if not value:
        return None
    try:
        if isinstance(value, (int, float)):
            ts = float(value)
            if ts > 1e12:
                ts /= 1000.0
            return datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc)
        text = str(value).strip()
        if not text:
            return None
        return datetime.datetime.fromisoformat(text.replace('Z', '+00:00'))
    except Exception:
        return None


def source_key(task):
    if not isinstance(task, dict):
        return ''
    task_id = str(task.get('id') or '').strip()
    if task_id:
        return task_id
    meta = task.get('sourceMeta') or {}
    for key in ('sessionId', 'sessionKey'):
        value = str(meta.get(key) or '').strip()
        if value:
            return f'{key}:{value}'
    return ''


def has_governance_markers(task):
    if not isinstance(task, dict):
        return False
    for field in GOVERNANCE_FIELDS:
        value = task.get(field)
        if value not in (None, '', [], {}, False):
            return True
    return False


def is_temporary_probe_task(task):
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


def entry_has_probe_text(entry):
    text = json.dumps(entry, ensure_ascii=False, sort_keys=True, default=str)
    lowered = text.lower()
    return any(marker.lower() in lowered for marker in PROBE_TEXT_MARKERS)


def sanitize_task_history(task):
    if not isinstance(task, dict):
        return task
    cleaned = copy.deepcopy(task)
    for field_name in ('progress_log', 'activity'):
        entries = cleaned.get(field_name)
        if isinstance(entries, list):
            cleaned[field_name] = [entry for entry in entries if not entry_has_probe_text(entry)]
    output = cleaned.get('output')
    if isinstance(output, str) and any(marker.lower() in output.lower() for marker in PROBE_TEXT_MARKERS):
        cleaned['output'] = ''
    return cleaned


def merge_values(old, new):
    if isinstance(old, dict) and isinstance(new, dict):
        merged = copy.deepcopy(old)
        for key, value in new.items():
            if key in merged:
                merged[key] = merge_values(merged[key], value)
            else:
                merged[key] = copy.deepcopy(value)
        return merged
    if isinstance(old, list) and isinstance(new, list):
        merged = copy.deepcopy(old)
        seen = {json.dumps(item, ensure_ascii=False, sort_keys=True, default=str) for item in merged}
        for item in new:
            marker = json.dumps(item, ensure_ascii=False, sort_keys=True, default=str)
            if marker not in seen:
                merged.append(copy.deepcopy(item))
                seen.add(marker)
        return merged
    return copy.deepcopy(new if new not in (None, '', [], {}, False) else old)


def should_clear_missing_field(old_task, new_task, field):
    if field in new_task or field not in old_task:
        return False
    rule = CLEAR_WHEN_RESOLVED_RULES.get(field)
    if not rule:
        return False
    try:
        return bool(rule(new_task))
    except Exception:
        return False


def merge_task(old, new, source_name, seen_at):
    stateful_fields = {
        'state', 'org', 'updatedAt', 'now', '_scheduler', 'progress_log', 'flow_log', 'block', 'output'
    }
    low_priority_state_sources = {'legacy_tasks_source'}
    new_seen = parse_dt(candidate_seen_at(new, seen_at)) or datetime.datetime.fromtimestamp(0, tz=datetime.timezone.utc)
    old_seen = parse_dt((old or {}).get('sampleLastSeenAt')) or parse_dt((old or {}).get('updatedAt')) or datetime.datetime.fromtimestamp(0, tz=datetime.timezone.utc)
    newer_or_equal = new_seen >= old_seen

    if not old:
        merged = copy.deepcopy(new)
        merged['sampleCapturedAt'] = seen_at
        merged['sampleSources'] = [source_name]
    else:
        merged = copy.deepcopy(old)
        for field in CLEAR_WHEN_RESOLVED_RULES:
            if should_clear_missing_field(merged, new, field):
                merged.pop(field, None)
        for key, value in new.items():
            if key in ('sampleCapturedAt', 'sampleLastSeenAt', 'sampleSources', 'sourceLayer'):
                continue
            if key in merged:
                if key in stateful_fields:
                    if source_name in low_priority_state_sources and not newer_or_equal:
                        continue
                    if newer_or_equal:
                        merged[key] = copy.deepcopy(value)
                    continue
                merged[key] = merge_values(merged[key], value)
            else:
                merged[key] = copy.deepcopy(value)
        merged.setdefault('sampleCapturedAt', seen_at)
        sources = list(merged.get('sampleSources') or [])
        if source_name not in sources:
            sources.append(source_name)
        merged['sampleSources'] = sources
    merged['sampleLastSeenAt'] = seen_at
    merged['sourceLayer'] = 'governance_sample'
    return sanitize_task_history(merged)


def candidate_seen_at(task, fallback):
    for value in (
        task.get('updatedAt'),
        (task.get('pending_confirm') or {}).get('requested_at'),
        task.get('sampleLastSeenAt'),
        task.get('sampleCapturedAt'),
        (task.get('sourceMeta') or {}).get('updatedAt'),
    ):
        dt = parse_dt(value)
        if dt:
            return dt.replace(microsecond=0).isoformat().replace('+00:00', 'Z')
    return fallback


def prune_samples(samples, now_dt):
    cutoff = now_dt - datetime.timedelta(days=MAX_AGE_DAYS)
    kept = []
    for task in samples:
        if is_temporary_probe_task(task):
            continue
        seen_dt = parse_dt(task.get('sampleLastSeenAt')) or parse_dt(task.get('updatedAt')) or parse_dt((task.get('sourceMeta') or {}).get('updatedAt'))
        if seen_dt and seen_dt < cutoff:
            continue
        kept.append(task)
    kept.sort(key=lambda item: parse_dt(item.get('sampleLastSeenAt')) or datetime.datetime.fromtimestamp(0, tz=datetime.timezone.utc), reverse=True)
    return kept


def load_sources():
    return [
        ('runtime_view', atomic_json_read(RUNTIME_FILE, [])),
        ('legacy_tasks_source', atomic_json_read(LEGACY_TASKS_FILE, [])),
        ('mission_control', atomic_json_read(MISSION_FILE, [])),
        ('manual_parallel', atomic_json_read(MANUAL_FILE, [])),
    ]


def main():
    now_dt = datetime.datetime.now(datetime.timezone.utc)
    seen_at = now_dt.replace(microsecond=0).isoformat().replace('+00:00', 'Z')
    existing = atomic_json_read(SAMPLES_FILE, [])
    merged = {}
    for item in existing:
        key = source_key(item)
        if key:
            merged[key] = copy.deepcopy(item)

    added = 0
    updated = 0
    for source_name, tasks in load_sources():
        if not isinstance(tasks, list):
            continue
        for task in tasks:
            if is_temporary_probe_task(task):
                continue
            if not has_governance_markers(task):
                continue
            key = source_key(task)
            if not key:
                continue
            before = merged.get(key)
            merged[key] = merge_task(before, task, source_name, candidate_seen_at(task, seen_at))
            if before is None:
                added += 1
            else:
                updated += 1

    payload = prune_samples(list(merged.values()), now_dt)
    atomic_json_write(SAMPLES_FILE, payload)
    log.info('governance samples updated | total=%s added=%s updated=%s', len(payload), added, updated)


if __name__ == '__main__':
    main()
