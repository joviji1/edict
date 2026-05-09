#!/usr/bin/env python3
"""旁路版 autopsy / stalled 草稿器。

只读取 tasks_source.json 或单个任务快照，产出 Markdown/JSON 草稿。
不会写回 tasks_source.json，不会写 backend，不会发布事件。
"""
import argparse
import json
import os
import pathlib
import re
import sys
from datetime import datetime, timezone

BASE = pathlib.Path(os.environ['EDICT_HOME']) if 'EDICT_HOME' in os.environ else pathlib.Path(__file__).resolve().parent.parent
TASKS_FILE = BASE / 'data' / 'tasks_source.json'
TASK_PY = BASE / 'edict' / 'backend' / 'app' / 'models' / 'task.py'
DEFAULT_OUT = BASE / 'isolation' / 'danghuangshang' / 'autopsy-drafts'

STALL_REASON_LABELS = {
    'no_heartbeat': '目标 Agent 无心跳',
    'dispatch_failed': '派发命令失败',
    'provider_timeout': '模型/API 超时',
    'tool_error': '工具调用失败',
    'permission_denied': '权限/状态机拦截',
    'missing_context': '上下文不足',
    'waiting_human': '等待人工确认',
    'dependency_blocked': '外部依赖未满足',
    'loop_detected': '重复派发/消息循环',
    'unknown': '未分类',
}


def now_iso():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return default


def load_canonical_transitions():
    if not TASK_PY.exists():
        return None
    source = TASK_PY.read_text(encoding='utf-8')
    m = re.search(r"STATE_TRANSITIONS\s*=\s*\{", source)
    if not m:
        return None
    start = m.start()
    depth = 0
    end = start
    for i, ch in enumerate(source[start:], start):
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    block = source[start:end]
    cleaned = re.sub(r"TaskState\.(\w+)", r'"\1"', block)
    cleaned = cleaned.replace('STATE_TRANSITIONS =', '_result =')
    ns = {}
    exec(cleaned, {}, ns)  # noqa: S102
    return ns['_result']


def infer_stall_reason(task):
    sched = task.get('_scheduler') or task.get('scheduler') or {}
    explicit = sched.get('stallReason') or sched.get('stalledReason') or task.get('stallReason')
    if explicit:
        return explicit if explicit in STALL_REASON_LABELS else 'unknown', 0.95, ['scheduler.stallReason']
    text_sources = [
        ('block', task.get('block', '')),
        ('now', task.get('now', '')),
    ]
    flow_log = task.get('flow_log', [])[-5:]
    progress_log = task.get('progress_log', [])[-5:]
    for idx, e in enumerate(flow_log, 1):
        text_sources.append((f'flow_log[-{len(flow_log)-idx+1}].remark', e.get('remark', '')))
    for idx, e in enumerate(progress_log, 1):
        text_sources.append((f'progress_log[-{len(progress_log)-idx+1}].text', e.get('text', '')))
    text = ' '.join(str(v) for _, v in text_sources).lower()
    patterns = [
        ('provider_timeout', ('timeout', 'timed out', '超时', '模型', 'provider', 'api')),
        ('dispatch_failed', ('dispatch failed', '派发失败', '无法派发', 'subagent')),
        ('permission_denied', ('permission', 'denied', '越权', '无权', '权限')),
        ('tool_error', ('tool error', '工具', 'exception', 'traceback', '报错')),
        ('missing_context', ('missing context', '上下文不足', '缺少上下文', '信息不足')),
        ('waiting_human', ('等待皇上', '等待人工', 'pendingconfirm', '待确认')),
        ('dependency_blocked', ('dependency', '依赖', '外部依赖')),
        ('loop_detected', ('loop', '重复派发', '消息循环')),
        ('no_heartbeat', ('heartbeat', '无心跳', '心跳')),
    ]
    for reason, keys in patterns:
        hit_sources = [src for src, value in text_sources if any(k in str(value).lower() for k in keys)]
        if hit_sources:
            return reason, 0.7, hit_sources
    return 'unknown', 0.3, [src for src, value in text_sources if value]


def suggest_actions(task, reason, transitions):
    state = task.get('state', '')
    sched = task.get('_scheduler') or task.get('scheduler') or {}
    suggestions = []
    if reason == 'provider_timeout':
        suggestions.append('先直测上游模型/接口，再判断是 provider 抖动还是路由失效。')
        suggestions.append('若只是瞬时超时，优先最小重试，不要直接改任务状态。')
    elif reason == 'dispatch_failed':
        suggestions.append('先查 dispatch payload、目标 agent 会话和最近错误日志。')
    elif reason == 'waiting_human':
        suggestions.append('补齐待确认问题与上下文，再由人工决定是否继续。')
    else:
        suggestions.append('先补现场证据，再决定是否进入人工处置或正式复盘。')
    allowed_next = []
    if transitions and state in transitions:
        allowed_next = sorted(transitions.get(state, []))
    if allowed_next:
        suggestions.append(f'当前状态 `{state}` 的权威可转移目标：{", ".join(allowed_next)}。草稿阶段不自动执行。')
    retry_count = sched.get('retryCount', sched.get('stall_count', 0))
    escalation = sched.get('escalationLevel', sched.get('escalation_level', 0))
    suggestions.append(f'当前调度摘要：retryCount={retry_count}，escalationLevel={escalation}。')
    return suggestions


def find_task(task_id):
    tasks = load_json(TASKS_FILE, [])
    if isinstance(tasks, dict):
        tasks = tasks.get('tasks', [])
    task = next((t for t in tasks if t.get('id') == task_id), None)
    if not task:
        raise SystemExit(f'task not found: {task_id}')
    return task


def build_report(task, reason, confidence, evidence_sources, transitions, output_path):
    sched = task.get('_scheduler') or task.get('scheduler') or {}
    flow_tail = task.get('flow_log', [])[-10:]
    progress_tail = task.get('progress_log', [])[-10:]
    lines = [
        f'# 任务旁路验尸草稿：{task.get("id", "")}',
        '',
        '> 旁路草稿。只读取证，不自动写回任务、不写 backend、不发 Redis 事件。',
        '',
        '## 基本信息',
        '',
        f'- 任务标题: {task.get("title", "")}',
        f'- 当前状态: {task.get("state", "")}',
        f'- 当前部门: {task.get("org", "")}',
        f'- 阻塞描述: {task.get("block", "")}',
        f'- 分类: `{reason}`（{STALL_REASON_LABELS.get(reason, "未分类")}）',
        f'- 置信度: {confidence:.2f}',
        f'- 生成时间: {now_iso()}',
        f'- 输出文件: `{output_path}`',
        '',
        '## 证据来源',
        '',
    ]
    if evidence_sources:
        for src in evidence_sources:
            lines.append(f'- {src}')
    else:
        lines.append('- 无显式命中证据，当前仅为弱推断。')
    lines.extend([
        '',
        '## 调度器摘要',
        '',
        f'- retryCount: {sched.get("retryCount", sched.get("stall_count", 0))}',
        f'- escalationLevel: {sched.get("escalationLevel", sched.get("escalation_level", 0))}',
        f'- lastProgressAt: {sched.get("lastProgressAt", sched.get("last_updated", ""))}',
        '',
        '## 最近流转记录',
        '',
    ])
    for e in flow_tail:
        lines.append(f'- {e.get("at", "")} | {e.get("from", "")} → {e.get("to", "")} | {e.get("remark", e.get("reason", ""))}')
    lines.extend(['', '## 最近进展记录', ''])
    for e in progress_tail:
        lines.append(f'- {e.get("at", "")} | {e.get("agent", e.get("agentLabel", ""))} | {e.get("text", "")}')
    lines.extend(['', '## 建议动作（草稿）', ''])
    for item in suggest_actions(task, reason, transitions):
        lines.append(f'- {item}')
    lines.extend([
        '',
        '## 边界',
        '',
        '- 本草稿不自动写回任务。',
        '- 本草稿不自动修改 `tasks_source.json`。',
        '- 本草稿不自动写 backend。',
        '- 本草稿不自动发布 Redis 事件。',
    ])
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description='只读旁路 autopsy 草稿器')
    parser.add_argument('task_id')
    parser.add_argument('--output-dir', default=str(DEFAULT_OUT))
    parser.add_argument('--format', choices=['md', 'json'], default='md')
    parser.add_argument('--reason', choices=sorted(STALL_REASON_LABELS), help='显式停滞原因；提供后覆盖自动推断')
    args = parser.parse_args()

    before = TASKS_FILE.read_text(encoding='utf-8') if TASKS_FILE.exists() else ''
    task = find_task(args.task_id)
    transitions = load_canonical_transitions() or {}
    reason, confidence, evidence_sources = infer_stall_reason(task)
    if args.reason:
        reason, confidence, evidence_sources = args.reason, 1.0, ['cli.--reason']
    out_dir = pathlib.Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / f'{args.task_id}.{"md" if args.format == "md" else "json"}'

    payload = {
        'task_id': args.task_id,
        'title': task.get('title', ''),
        'state': task.get('state', ''),
        'org': task.get('org', ''),
        'reason': reason,
        'label': STALL_REASON_LABELS.get(reason, '未分类'),
        'confidence': round(confidence, 2),
        'evidence_sources': evidence_sources,
        'suggested_actions': suggest_actions(task, reason, transitions),
        'report_path': str(output_path),
        'generated_at': now_iso(),
        'mutated_task_source': False,
        'mode': 'bypass-draft',
    }

    if args.format == 'json':
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    else:
        output_path.write_text(build_report(task, reason, confidence, evidence_sources, transitions, output_path), encoding='utf-8')

    after = TASKS_FILE.read_text(encoding='utf-8') if TASKS_FILE.exists() else ''
    payload['mutated_task_source'] = before != after
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
