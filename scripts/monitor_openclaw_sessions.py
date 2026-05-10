#!/usr/bin/env python3
"""OpenClaw session 健康监控脚本。

检测以下异常：
1. stale_running: session status=running 但最后活动超过阈值
2. aborted_last: session abortedLastRun=True
3. empty_transcript: session 有记录但 transcript 文件为空
4. long_running: session 运行时间超过阈值
5. model_error: 最后一条消息是 error/aborted

输出 JSON 报告，可接入 cron 或 guard 链。
"""
from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

OPENCLAW_HOME = Path(os.environ.get('OPENCLAW_HOME', '/root/.openclaw'))
AGENTS_ROOT = OPENCLAW_HOME / 'agents'

# 阈值（秒）
DEFAULT_STALE_THRESHOLD = 3600      # 1 小时无活动视为 stale
DEFAULT_LONG_RUNNING_THRESHOLD = 1800  # 30 分钟视为长跑


def load_sessions(agent_id: str) -> dict:
    path = AGENTS_ROOT / agent_id / 'sessions' / 'sessions.json'
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding='utf-8'))


def get_last_entries(session_file: Path, n: int = 3) -> list:
    """读取 transcript 最后 n 条记录。"""
    if not session_file.exists():
        return []
    lines = []
    with session_file.open('rb') as f:
        f.seek(0, 2)
        size = f.tell()
        # 从末尾读 64KB
        read_start = max(0, size - 65536)
        f.seek(read_start)
        data = f.read().decode('utf-8', 'replace')
        all_lines = data.strip().split('\n')
        # 跳过第一行（可能不完整）
        start = 1 if read_start > 0 and len(all_lines) > 1 else 0
        lines = all_lines[start:]
    
    entries = []
    for line in lines[-n:]:
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return entries



def coerce_epoch_ms(value) -> int:
    """Accept OpenClaw session timestamps as epoch-ms, epoch-sec, or ISO strings."""
    if value in (None, ''):
        return 0
    if isinstance(value, (int, float)):
        number = float(value)
    elif isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return 0
        try:
            number = float(stripped)
        except ValueError:
            try:
                parsed = datetime.fromisoformat(stripped.replace('Z', '+00:00'))
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                return int(parsed.timestamp() * 1000)
            except ValueError:
                return 0
    else:
        return 0
    if number <= 0:
        return 0
    return int(number * 1000) if number < 10_000_000_000 else int(number)


def check_session(key: str, entry: dict, now_ms: int,
                  stale_threshold: int, long_running_threshold: int) -> list:
    """检查单个 session，返回问题列表。"""
    issues = []
    sid = entry.get('sessionId', '')
    status = entry.get('status', '')
    updated = coerce_epoch_ms(entry.get('updatedAt', 0))
    started = coerce_epoch_ms(entry.get('startedAt', 0))
    aborted = entry.get('abortedLastRun', False)
    session_file = Path(entry.get('sessionFile', ''))
    age_sec = (now_ms - updated) / 1000 if updated else float('inf')

    # 1. stale running
    if status == 'running' and age_sec > stale_threshold:
        issues.append({
            'type': 'stale_running',
            'severity': 'high',
            'session_key': key,
            'session_id': sid[:16],
            'age_minutes': round(age_sec / 60),
            'message': f'session 已 running {round(age_sec/60)} 分钟无活动'
        })

    # 2. aborted
    if aborted and status != 'running':
        issues.append({
            'type': 'aborted_last_run',
            'severity': 'medium',
            'session_key': key,
            'session_id': sid[:16],
            'message': '上次运行被中止'
        })

    # 3. empty transcript
    if session_file.exists() and session_file.stat().st_size == 0:
        issues.append({
            'type': 'empty_transcript',
            'severity': 'low',
            'session_key': key,
            'session_id': sid[:16],
            'message': 'transcript 文件为空'
        })

    # 3b. missing sessionFile
    if not session_file or not session_file.exists() or session_file.is_dir():
        if status == 'running':
            issues.append({
                'type': 'missing_transcript',
                'severity': 'medium',
                'session_key': key,
                'session_id': sid[:16],
                'message': 'running session 无 transcript 文件'
            })

    # 4. long running
    if status == 'running' and started:
        run_sec = (now_ms - started) / 1000
        if run_sec > long_running_threshold:
            issues.append({
                'type': 'long_running',
                'severity': 'medium',
                'session_key': key,
                'session_id': sid[:16],
                'run_minutes': round(run_sec / 60),
                'message': f'session 已运行 {round(run_sec/60)} 分钟'
            })

    # 5. model error in last entry
    if session_file and session_file.exists() and session_file.is_file() and session_file.stat().st_size > 0:
        last_entries = get_last_entries(session_file, 1)
        if last_entries:
            last = last_entries[0]
            if last.get('type') == 'custom' and last.get('customType') == 'openclaw:prompt-error':
                err_data = last.get('data', {})
                issues.append({
                    'type': 'model_error',
                    'severity': 'medium',
                    'session_key': key,
                    'session_id': sid[:16],
                    'error': err_data.get('error', 'unknown'),
                    'provider': err_data.get('provider', '?'),
                    'model': err_data.get('model', '?'),
                    'message': f'最后一条是模型错误: {err_data.get("error", "unknown")}'
                })

    return issues


def run_check(agent_ids: list, stale_threshold: int, long_running_threshold: int) -> dict:
    now_ms = int(time.time() * 1000)
    all_issues = []
    sessions_checked = 0

    for agent_id in agent_ids:
        sessions = load_sessions(agent_id)
        for key, entry in sessions.items():
            if not isinstance(entry, dict):
                continue
            sessions_checked += 1
            issues = check_session(key, entry, now_ms,
                                   stale_threshold, long_running_threshold)
            all_issues.extend(issues)

    high = [i for i in all_issues if i['severity'] == 'high']
    medium = [i for i in all_issues if i['severity'] == 'medium']
    low = [i for i in all_issues if i['severity'] == 'low']

    return {
        'ok': len(high) == 0,
        'checked_at': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()),
        'sessions_checked': sessions_checked,
        'summary': {
            'high': len(high),
            'medium': len(medium),
            'low': len(low)
        },
        'issues': all_issues
    }


def main():
    parser = argparse.ArgumentParser(description='OpenClaw session 健康监控')
    parser.add_argument('--agents', nargs='+', default=['taizi', 'zhongshu', 'menxia', 'shangshu'],
                        help='要检查的 agent 列表')
    parser.add_argument('--stale-threshold', type=int, default=DEFAULT_STALE_THRESHOLD,
                        help='stale 判定阈值（秒）')
    parser.add_argument('--long-running-threshold', type=int, default=DEFAULT_LONG_RUNNING_THRESHOLD,
                        help='长跑判定阈值（秒）')
    parser.add_argument('--json', action='store_true', help='JSON 输出')
    args = parser.parse_args()

    report = run_check(args.agents, args.stale_threshold, args.long_running_threshold)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"检查时间: {report['checked_at']}")
        print(f"检查 session: {report['sessions_checked']}")
        print(f"高危: {report['summary']['high']}  中危: {report['summary']['medium']}  低危: {report['summary']['low']}")
        if report['ok']:
            print("✅ 无高危问题")
        else:
            print("❌ 存在高危问题")
        for issue in report['issues']:
            print(f"  [{issue['severity']}] {issue['type']}: {issue['message']}")

    return 0 if report['ok'] else 1


if __name__ == '__main__':
    exit(main())
