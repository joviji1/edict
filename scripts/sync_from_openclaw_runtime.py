#!/usr/bin/env python3
import json
import pathlib
import time
import datetime
import traceback
import logging
import re
from file_lock import atomic_json_write, atomic_json_read
from utils import get_openclaw_home

log = logging.getLogger('sync_runtime')
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(message)s', datefmt='%H:%M:%S')

BASE = pathlib.Path(__file__).resolve().parent.parent
DATA = BASE / 'data'
DATA.mkdir(exist_ok=True)
SYNC_STATUS = DATA / 'sync_status.json'
SESSIONS_ROOT = get_openclaw_home() / 'agents'
RUNTIME_VIEW = DATA / 'tasks_runtime_view.json'
ARCHIVE_FILE = DATA / 'tasks_jjc_archive.json'
AGGREGATE_FILE = DATA / 'tasks_source.json'


def write_status(**kwargs):
    atomic_json_write(SYNC_STATUS, kwargs)


def _to_timestamp_ms(value):
    if value in (None, '', 0):
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return 0
        try:
            return int(float(text))
        except Exception:
            pass
        try:
            dt = datetime.datetime.fromisoformat(text.replace('Z', '+00:00'))
            return int(dt.timestamp() * 1000)
        except Exception:
            return 0
    return 0


def ms_to_str(ts_ms):
    ts_ms = _to_timestamp_ms(ts_ms)
    if not ts_ms:
        return '-'
    try:
        return datetime.datetime.fromtimestamp(ts_ms / 1000).strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        return '-'


def state_from_session(age_ms, aborted):
    if aborted:
        return 'Blocked'
    if age_ms <= 2 * 60 * 1000:
        return 'Doing'
    if age_ms <= 60 * 60 * 1000:
        return 'Review'
    return 'Next'


def detect_official(agent_id):
    mapping = {
        'main':    ('储君', '太子'),        # legacy id for taizi
        'taizi':   ('储君', '太子'),
        'zhongshu': ('中书令', '中书省'),
        'menxia':  ('侍中', '门下省'),
        'shangshu': ('尚书令', '尚书省'),
        'hubu':    ('户部尚书', '户部'),
        'libu':    ('礼部尚书', '礼部'),
        'bingbu':  ('兵部尚书', '兵部'),
        'xingbu':  ('刑部尚书', '刑部'),
        'gongbu':  ('工部尚书', '工部'),
        'libu_hr': ('吏部尚书', '吏部'),
        'zaochao': ('钦天监', '钦天监'),
    }
    return mapping.get(agent_id, ('尚书令', '尚书省'))


def load_activity(session_file, limit=12):
    p = pathlib.Path(session_file or '')
    if not p.exists():
        return []
    rows = []
    try:
        lines = p.read_text(errors='ignore').splitlines()
    except Exception:
        return []

    # Read all valid JSON lines first
    events = []
    for ln in lines:
        try:
            item = json.loads(ln)
            events.append(item)
        except:
            continue

    # Process events to extract meaningful activity
    # We want to show what the agent is *thinking* or *doing*
    for item in reversed(events):
        msg = item.get('message') or {}
        role = msg.get('role')
        ts = item.get('timestamp') or ''

        if role == 'toolResult':
            tool = msg.get('toolName', '-')
            details = msg.get('details') or {}
            # If tool output is short, show it
            content = msg.get('content', [{'text': ''}])[0].get('text', '')
            if len(content) < 50:
                text = f"Tool '{tool}' returned: {content}"
            else:
                text = f"Tool '{tool}' finished"
            rows.append({'at': ts, 'kind': 'tool', 'text': text, 'rawText': content})

        elif role == 'assistant':
            text = ''
            for c in msg.get('content', []):
                if c.get('type') == 'text' and c.get('text'):
                    raw_text = c.get('text').strip()
                    # Clean up common prefixes
                    clean_text = raw_text.replace('[[reply_to_current]]', '').strip()
                    if clean_text:
                        text = clean_text
                    break
            if text:
                # Prioritize showing the "thought" - usually the first few sentences
                summary = text.split('\n')[0]
                if len(summary) > 200:
                    summary = summary[:200] + '...'
                rows.append({'at': ts, 'kind': 'assistant', 'text': summary, 'rawText': text})
                
        elif role == 'user':
             # Also show what user asked, can be context relevant
             text = ''
             for c in msg.get('content', []):
                if c.get('type') == 'text':
                     text = c.get('text', '')[:100]
             if text:
                 rows.append({'at': ts, 'kind': 'user', 'text': f"User: {text}...", 'rawText': text})

        if len(rows) >= limit:
            break

    # Re-order to chronological for display if needed, but the caller usually takes the first (latest)
    return rows


def extract_task_id_from_activity(activity):
    if not isinstance(activity, list):
        return ''
    patterns = [
        re.compile(r'任务ID[:：]\s*([0-9a-fA-F-]{36})'),
        re.compile(r'\b([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})\b'),
    ]
    for item in activity:
        text = str(item.get('rawText') or item.get('text') or '')
        for pattern in patterns:
            m = pattern.search(text)
            if m:
                return m.group(1)
    return ''


def infer_governance_state_from_activity(activity):
    if not isinstance(activity, list):
        return '', ''
    transition_re = re.compile(r'状态更新[:：]\s*([A-Za-z]+)\s*[→\-]+\s*([A-Za-z]+)')
    state_org_map = {
        'Taizi': '太子',
        'Zhongshu': '中书省',
        'Menxia': '门下省',
        'Assigned': '尚书省',
        'Review': '尚书省',
        'PendingConfirm': '尚书省',
        'Doing': '执行中',
        'Next': '尚书省',
        'Done': '完成',
        'Blocked': '阻塞',
    }
    text_rules = [
        ('中书省', ('已在中书省', '转交中书省', '中书省起草', 'Zhongshu')),
        ('门下省', ('已在门下省', '转交门下省', '门下省审议', 'Menxia')),
        ('尚书省', ('已在尚书省', '转交尚书省', '尚书省派发', 'Assigned')),
    ]
    for item in activity:
        text = str(item.get('rawText') or item.get('text') or '')
        m = transition_re.search(text)
        if m:
            state = m.group(2)
            return state, state_org_map.get(state, '')
        for org, needles in text_rules:
            if any(needle in text for needle in needles):
                if org == '中书省':
                    return 'Zhongshu', org
                if org == '门下省':
                    return 'Menxia', org
                if org == '尚书省':
                    return 'Assigned', org
    return '', ''


def build_task(agent_id, session_key, row, now_ms):
    session_id = row.get('sessionId') or session_key
    updated_at_raw = row.get('updatedAt')
    updated_at = _to_timestamp_ms(updated_at_raw)
    age_ms = max(0, now_ms - updated_at) if updated_at else 99 * 24 * 3600 * 1000
    aborted = bool(row.get('abortedLastRun'))
    state = state_from_session(age_ms, aborted)

    official, org = detect_official(agent_id)
    channel = row.get('lastChannel') or (row.get('origin') or {}).get('channel') or '-'
    session_file = row.get('sessionFile', '')
    
    # 尝试从 activity 获取更有意义的当前状态描述
    latest_act = '等待指令'
    acts = load_activity(session_file, limit=12)
    linked_task_id = extract_task_id_from_activity(acts) if ':edict-dispatch' in session_key else ''
    bridged_state, bridged_org = infer_governance_state_from_activity(acts) if ':edict-dispatch' in session_key else ('', '')
    if bridged_state:
        state = bridged_state
    if bridged_org:
        org = bridged_org
    
    # If the absolute latest is a tool result, look for the preceding assistant thought
    # because that explains *why* the tool was called.
    if acts:
        first_act = acts[0]
        if first_act['kind'] == 'tool' and len(acts) > 1:
            # Look for next assistant message (which is actually previous in time)
            for next_act in acts[1:]:
                if next_act['kind'] == 'assistant':
                    latest_act = f"正在执行: {next_act['text'][:80]}"
                    break
            else:
                latest_act = first_act['text'][:60]
        elif first_act['kind'] == 'assistant':
             latest_act = f"思考中: {first_act['text'][:80]}"
        else:
             latest_act = acts[0]['text'][:60]
    
    title_label = (row.get('origin') or {}).get('label') or session_key
    # 清洗会话标题：agent:xxx:cron:uuid → 定时任务, agent:xxx:subagent:uuid → 子任务
    import re
    if re.match(r'agent:\w+:cron:', title_label):
        title = f"{org}定时任务"
    elif re.match(r'agent:\w+:subagent:', title_label):
        title = f"{org}子任务"
    elif title_label == 'heartbeat' and session_key.endswith(':main'):
        title = f"{org}会话"
    elif title_label == session_key or len(title_label) > 40:
        title = f"{org}会话"
    else:
        title = f"{title_label}"
    runtime_task_id = linked_task_id or f"OC-{agent_id}-{str(session_id)[:8]}"
    
    return {
        'id': runtime_task_id,
        'title': title,
        'official': official,
        'org': org,
        'state': state,
        'now': latest_act,
        'eta': ms_to_str(updated_at),
        'block': '上次运行中断' if aborted else '无',
        'output': session_file,
        'flow': {
            'draft': f"agent={agent_id}",
            'review': f"updatedAt={ms_to_str(updated_at)}",
            'dispatch': f"sessionKey={session_key}",
        },
        'ac': '来自 OpenClaw runtime sessions 的实时映射',
        'activity': acts,
        'sourceMeta': {
            'agentId': agent_id,
            'sessionKey': session_key,
            'sessionId': session_id,
            'taskId': linked_task_id,
            'updatedAt': updated_at,
            'ageMs': age_ms,
            'systemSent': bool(row.get('systemSent')),
            'abortedLastRun': aborted,
            'inputTokens': row.get('inputTokens'),
            'outputTokens': row.get('outputTokens'),
            'totalTokens': row.get('totalTokens'),
        }
    }


def should_keep_runtime_task(task, now_ms):
    """Return True if a runtime-mapped task should stay in tasks_source.json."""
    if str(task.get('id', '')).startswith('JJC'):
        return True

    source_meta = task.get('sourceMeta') or {}
    updated = _to_timestamp_ms(source_meta.get('updatedAt', 0))
    title = task.get('title', '')
    state = task.get('state')
    session_key = source_meta.get('sessionKey', '')
    one_day_ago = now_ms - 24 * 3600 * 1000

    # 1. 排除太旧的 (超过24小时)
    if updated < one_day_ago:
        return False

    # edict dispatch 会话是治理链实时面板，不应因为已推进到 Zhongshu / Menxia / Assigned 就被误删。
    if ':edict-dispatch' in session_key:
        activity = task.get('activity') or []
        has_real_signal = bool(source_meta.get('taskId')) or bool(activity)
        if not has_real_signal:
            return False
        return bool(source_meta.get('taskId')) or state in ('Taizi', 'Zhongshu', 'Menxia', 'Assigned', 'Review', 'PendingConfirm', 'Doing', 'Blocked')

    # 2. 排除纯后台 cron / subagent 任务，除非它们正在报错
    if '定时任务' in title or '子任务' in title:
        return state == 'Blocked'

    # 3. 优先保留真实官方 main 会话；但过滤掉坏指针/引导噪音。
    title_lower = str(title).strip().lower()
    if session_key.endswith(':main'):
        output_path = str(task.get('output') or '').strip()
        if output_path and not pathlib.Path(output_path).exists():
            return False
        activity = task.get('activity') or []
        if not activity:
            return False
        latest = activity[0]
        latest_text = str(latest.get('text') or '').strip().upper()
        if latest.get('kind') == 'assistant' and latest_text in {'OK', 'HEARTBEAT_OK'}:
            assistant_texts = [
                str(item.get('text') or '').strip().upper()
                for item in activity
                if item.get('kind') == 'assistant'
            ]
            if assistant_texts and all(text in {'OK', 'HEARTBEAT_OK'} for text in assistant_texts) and len(activity) <= 3:
                return False
        return True
    if title_lower == 'heartbeat':
        return False
    if ':feishu:group:' in session_key or ':feishu:direct:' in session_key:
        return state == 'Blocked'

    # 保留 Doing（<2min）、Review（<60min）、Blocked（报错）
    return state in ('Doing', 'Review', 'Blocked')


def main():
    start = time.time()
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    now_ms = int(time.time() * 1000)

    try:
        tasks = []
        scan_files = 0

        if SESSIONS_ROOT.exists():
            for agent_dir in sorted(SESSIONS_ROOT.iterdir()):
                if not agent_dir.is_dir():
                    continue
                agent_id = agent_dir.name
                sessions_file = agent_dir / 'sessions' / 'sessions.json'
                if not sessions_file.exists():
                    continue
                scan_files += 1

                try:
                    raw = json.loads(sessions_file.read_text())
                except Exception:
                    continue

                if not isinstance(raw, dict):
                    continue

                for session_key, row in raw.items():
                    if not isinstance(row, dict):
                        continue
                    tasks.append(build_task(agent_id, session_key, row, now_ms))

        # merge mission control tasks (最小接入)
        mc_tasks_file = DATA / 'mission_control_tasks.json'
        if mc_tasks_file.exists():
            try:
                mc_tasks = json.loads(mc_tasks_file.read_text())
                if isinstance(mc_tasks, list):
                    tasks.extend(mc_tasks)
            except Exception:
                pass

        # merge manual parallel tasks (用于军机处并行看板展示)
        manual_tasks_file = DATA / 'manual_parallel_tasks.json'
        if manual_tasks_file.exists():
            try:
                manual_tasks = json.loads(manual_tasks_file.read_text())
                if isinstance(manual_tasks, list):
                    tasks.extend(manual_tasks)
            except Exception:
                pass

        tasks.sort(key=lambda x: _to_timestamp_ms(x.get('sourceMeta', {}).get('updatedAt', 0)), reverse=True)

        # 去重（同一 id 只保留第一个=最新的）
        seen_ids = set()
        deduped = []
        for t in tasks:
            if t['id'] not in seen_ids:
                seen_ids.add(t['id'])
                deduped.append(t)
        tasks = deduped

        # ── 过滤掉非 JJC 且非活跃的系统会话，防止看板噪音 ──
        # 保留：24 小时内的真实活跃/异常 runtime 会话；排除：heartbeat、静默 cron/subagent、非报错的普通群聊/私聊映射。
        tasks = [t for t in tasks if should_keep_runtime_task(t, now_ms)]

        # runtime 层单独落盘，避免与 JJC 历史台账混写。
        atomic_json_write(RUNTIME_VIEW, tasks)

        # 迁移期兼容：把现有 tasks_source.json 中的 JJC 任务沉淀到 archive，
        # 由后续 rebuild_task_views.py 再聚合成前端兼容视图。
        existing_tasks_file = AGGREGATE_FILE
        existing_archive = atomic_json_read(ARCHIVE_FILE, [])
        archive_map = {
            str(item.get('id', '')): item
            for item in existing_archive
            if isinstance(item, dict) and str(item.get('id', '')).startswith('JJC')
        }
        if existing_tasks_file.exists():
            try:
                existing = json.loads(existing_tasks_file.read_text())
                for task in existing:
                    task_id = str(task.get('id', ''))
                    if task_id.startswith('JJC'):
                        archive_map[task_id] = task
            except Exception as e:
                log.error(f'merge existing JJC tasks failed: {e}')
        archive = list(archive_map.values())
        archive.sort(key=lambda x: x.get('updatedAt') or x.get('createdAt') or '', reverse=True)
        atomic_json_write(ARCHIVE_FILE, archive)

        duration_ms = int((time.time() - start) * 1000)
        write_status(
            ok=True,
            lastSyncAt=now,
            durationMs=duration_ms,
            source='openclaw_runtime_sessions',
            recordCount=len(tasks),
            scannedSessionFiles=scan_files,
            missingFields={},
            error=None,
        )
        log.info(f'synced {len(tasks)} tasks from openclaw runtime in {duration_ms}ms')

    except Exception as e:
        duration_ms = int((time.time() - start) * 1000)
        write_status(
            ok=False,
            lastSyncAt=now,
            durationMs=duration_ms,
            source='openclaw_runtime_sessions',
            recordCount=0,
            missingFields={},
            error=f'{type(e).__name__}: {e}',
            traceback=traceback.format_exc(limit=3),
        )
        raise


if __name__ == '__main__':
    main()
