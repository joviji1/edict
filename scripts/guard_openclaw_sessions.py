#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Tuple

OPENCLAW_HOME = Path('/root/.openclaw')
CONFIG_PATH = OPENCLAW_HOME / 'openclaw.json'
AGENTS_ROOT = OPENCLAW_HOME / 'agents'
OVERFLOW_RE = re.compile(r"longer than the model's context length|context limit exceeded", re.I)
CLEAR_FIELDS = [
    'modelProvider',
    'model',
    'inputTokens',
    'outputTokens',
    'totalTokens',
    'estimatedCostUsd',
    'cacheRead',
    'cacheWrite',
    'contextTokens',
    'systemPromptReport',
    'fallbackNoticeSelectedModel',
    'fallbackNoticeActiveModel',
    'fallbackNoticeReason',
]


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


def build_model_windows(cfg: Dict[str, Any]) -> Dict[str, int]:
    windows: Dict[str, int] = {}
    providers = ((cfg.get('models') or {}).get('providers') or {})
    for provider, pdata in providers.items():
        for model in pdata.get('models') or []:
            model_id = model.get('id') or model.get('name')
            ctx = model.get('contextWindow')
            if model_id and isinstance(ctx, int):
                windows[f'{provider}/{model_id}'] = ctx
    return windows


def read_tail_text(path: Path, max_bytes: int = 131072) -> str:
    with path.open('rb') as fh:
        fh.seek(0, 2)
        size = fh.tell()
        fh.seek(max(0, size - max_bytes))
        data = fh.read()
    return data.decode('utf-8', 'replace')


def resolve_model_window(entry: Dict[str, Any], cfg: Dict[str, Any], windows: Dict[str, int]) -> Tuple[int | None, str | None]:
    candidates: List[str] = []
    provider = entry.get('modelProvider')
    model = entry.get('model')
    if provider and model:
        candidates.append(f'{provider}/{model}')
    primary = (((cfg.get('agents') or {}).get('defaults') or {}).get('model') or {}).get('primary')
    if primary:
        candidates.append(str(primary))
    for ref in candidates:
        if ref in windows:
            return windows[ref], ref
    return None, None


def detect_entry_issues(
    session_key: str,
    entry: Dict[str, Any],
    cfg: Dict[str, Any],
    windows: Dict[str, int],
    sessions_dir: Path,
    main_only: bool,
) -> Dict[str, Any] | None:
    if main_only and not session_key.endswith(':main'):
        return None

    session_id = str(entry.get('sessionId') or '').strip()
    session_file_raw = str(entry.get('sessionFile') or '').strip()
    if session_file_raw:
        session_file = Path(session_file_raw)
    elif session_id:
        session_file = sessions_dir / f'{session_id}.jsonl'
    else:
        session_file = sessions_dir / 'unknown.jsonl'

    reasons: List[str] = []
    if session_id and session_file.suffix == '.jsonl' and session_file.stem != session_id:
        reasons.append('session_id_file_mismatch')

    model_window, model_ref = resolve_model_window(entry, cfg, windows)
    context_tokens = entry.get('contextTokens')
    context_window_warning = None
    if isinstance(context_tokens, int) and model_window:
        if context_tokens > model_window:
            context_window_warning = f'{context_tokens}>{model_window}:{model_ref}'
        elif context_tokens < model_window:
            reasons.append('stale_context_window_metadata')
            context_window_warning = f'{context_tokens}<{model_window}:{model_ref}'

    if session_file.exists():
        tail = read_tail_text(session_file)
        if OVERFLOW_RE.search(tail):
            reasons.append('transcript_context_overflow')
    else:
        reasons.append('missing_transcript_file')

    if entry.get('status') == 'failed' and any('overflow' in reason for reason in reasons):
        reasons.append('failed_status_with_overflow')

    if not reasons:
        return None

    issue = {
        'sessionKey': session_key,
        'sessionId': session_id,
        'sessionFile': str(session_file),
        'reasons': reasons,
    }
    if context_window_warning:
        issue['contextWindowWarning'] = context_window_warning
    return issue


def rotate_entry(entry: Dict[str, Any], sessions_dir: Path) -> Dict[str, Any]:
    next_id = str(uuid.uuid4())
    next_file = sessions_dir / f'{next_id}.jsonl'
    next_file.parent.mkdir(parents=True, exist_ok=True)
    next_file.touch(exist_ok=True)
    next_entry = dict(entry)
    next_entry['sessionId'] = next_id
    next_entry['sessionFile'] = str(next_file)
    next_entry['updatedAt'] = int(time.time() * 1000)
    next_entry['systemSent'] = False
    next_entry['abortedLastRun'] = False
    next_entry['totalTokensFresh'] = False
    for field in ['status', 'startedAt', 'endedAt']:
        next_entry.pop(field, None)
    for field in CLEAR_FIELDS:
        next_entry.pop(field, None)
    return next_entry


def backup_issue(backup_root: Path, agent_id: str, sessions_file: Path, transcript_file: Path | None) -> None:
    agent_dir = backup_root / agent_id
    agent_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(sessions_file, agent_dir / 'sessions.json')
    if transcript_file and transcript_file.exists():
        shutil.copy2(transcript_file, agent_dir / transcript_file.name)


def process_agent(
    agent_dir: Path,
    cfg: Dict[str, Any],
    windows: Dict[str, int],
    backup_root: Path,
    apply: bool,
    main_only: bool,
) -> Dict[str, Any]:
    sessions_dir = agent_dir / 'sessions'
    sessions_file = sessions_dir / 'sessions.json'
    if not sessions_file.exists():
        return {'agent': agent_dir.name, 'checked': 0, 'repairs': 0, 'issues': []}

    store = load_json(sessions_file)
    issues = []
    repairs = 0
    changed = False

    for session_key, entry in store.items():
        if not isinstance(entry, dict):
            continue
        issue = detect_entry_issues(session_key, entry, cfg, windows, sessions_dir, main_only)
        if not issue:
            continue
        issues.append(issue)
        if apply:
            transcript = Path(issue['sessionFile'])
            backup_issue(backup_root, agent_dir.name, sessions_file, transcript if transcript.exists() else None)
            store[session_key] = rotate_entry(entry, sessions_dir)
            repairs += 1
            changed = True

    if apply and changed:
        sessions_file.write_text(json.dumps(store, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    return {
        'agent': agent_dir.name,
        'checked': len(store),
        'repairs': repairs,
        'issues': issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Guard and rotate broken OpenClaw sessions before they wedge long-lived agents.'
    )
    parser.add_argument('--apply', action='store_true', help='Write repairs back to sessions.json')
    parser.add_argument('--all-sessions', action='store_true', help='Check all session keys, not only :main sessions')
    parser.add_argument('--backup-root', default='', help='Optional explicit backup directory root')
    args = parser.parse_args()

    cfg = load_json(CONFIG_PATH)
    windows = build_model_windows(cfg)
    ts = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
    backup_root = Path(args.backup_root) if args.backup_root else OPENCLAW_HOME / 'backups' / f'session-guard-{ts}'

    results = []
    for agent_dir in sorted(path for path in AGENTS_ROOT.iterdir() if path.is_dir()):
        results.append(process_agent(agent_dir, cfg, windows, backup_root, args.apply, not args.all_sessions))

    summary = {
        'apply': args.apply,
        'backupRoot': str(backup_root),
        'results': results,
        'totalRepairs': sum(result['repairs'] for result in results),
        'totalIssues': sum(len(result['issues']) for result in results),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
