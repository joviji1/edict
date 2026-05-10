#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict

CONFIG_PATH = Path('/root/.openclaw/openclaw.json')
DEFAULT_AGENT = 'taizi'
DEFAULT_FEISHU_ACCOUNT = 'default'
DEFAULT_LOG_DIR = Path('/root/.openclaw/workspace/edict/logs/feishu-relay')
DEFAULT_SESSION_ID = '89f35078-bb0d-49c2-96bf-e250b69af111'
DEFAULT_SESSION_KEY = 'agent:taizi:feishu:direct:ou_ed2187f2ad27e0b7876913371e72c06a'
DEFAULT_TARGET = 'user:ou_ed2187f2ad27e0b7876913371e72c06a'

STATUS_ACCEPTED = 'accepted_only'
STATUS_TIMEOUT = 'accepted_but_no_final'
STATUS_SENT = 'manual_sent'
STATUS_DRY_RUN = 'dry_run'


def now_ts() -> str:
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def load_config() -> Dict[str, Any]:
    return json.loads(CONFIG_PATH.read_text(encoding='utf-8'))


def resolve_gateway_token(cfg: Dict[str, Any]) -> str:
    token = (((cfg.get('gateway') or {}).get('auth') or {}).get('token') or '').strip()
    if not token:
        raise RuntimeError('gateway.auth.token missing in /root/.openclaw/openclaw.json')
    return token


def append_log(record: Dict[str, Any], log_dir: Path) -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    day = time.strftime('%Y-%m-%d', time.gmtime())
    path = log_dir / f'{day}.jsonl'
    with path.open('a', encoding='utf-8') as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + '\n')
    return path


def run_command(cmd: list[str], timeout_s: int | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)


def build_agent_params(args: argparse.Namespace) -> Dict[str, Any]:
    params: Dict[str, Any] = {
        'message': args.message,
        'idempotencyKey': args.idempotency_key or str(uuid.uuid4()),
        'agentId': args.agent_id or DEFAULT_AGENT,
    }
    if getattr(args, 'session_key', ''):
        params['sessionKey'] = args.session_key
    if getattr(args, 'session_id', ''):
        params['sessionId'] = args.session_id
    return params


def build_agent_command(token: str, params: Dict[str, Any], timeout_ms: int, expect_final: bool) -> list[str]:
    cmd = [
        'openclaw', 'gateway', 'call', 'agent',
        '--json',
        '--timeout', str(timeout_ms),
        '--token', token,
        '--params', json.dumps(params, ensure_ascii=False),
    ]
    if expect_final:
        cmd.append('--expect-final')
    return cmd


def build_send_command(target: str, text: str, account_id: str, reply_to: str = '') -> list[str]:
    cmd = [
        'openclaw', 'message', 'send',
        '--channel', 'feishu',
        '--account', account_id,
        '--target', target,
        '--message', text,
        '--json',
    ]
    if reply_to:
        cmd.extend(['--reply-to', reply_to])
    return cmd


def classify_agent_result(proc: subprocess.CompletedProcess[str], expect_final: bool) -> str:
    combined = (proc.stdout or '') + (proc.stderr or '')
    if proc.returncode == 0:
        return STATUS_ACCEPTED if not expect_final else 'final_returned'
    if 'gateway timeout after' in combined.lower():
        return STATUS_TIMEOUT
    return 'agent_error'


def print_json(data: Dict[str, Any]) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def redact_command(cmd: list[str]) -> list[str]:
    """Return a display-safe command without leaking bearer/auth tokens."""
    redacted: list[str] = []
    hide_next = False
    for item in cmd:
        if hide_next:
            redacted.append('[REDACTED]')
            hide_next = False
            continue
        redacted.append(item)
        if item in {'--token', '--api-key', '--authorization'}:
            hide_next = True
    return redacted


def do_probe(args: argparse.Namespace, cfg: Dict[str, Any]) -> int:
    token = resolve_gateway_token(cfg)
    params = build_agent_params(args)
    cmd = build_agent_command(token, params, args.timeout_ms, args.expect_final)
    result = {
        'ts': now_ts(),
        'mode': 'probe',
        'status': STATUS_DRY_RUN,
        'sessionKey': getattr(args, 'session_key', ''),
        'sessionId': args.session_id,
        'target': args.target,
        'command': redact_command(cmd),
        'params': params,
        'note': 'Probe only. Does not send manual fallback.',
    }
    if args.dry_run:
        print_json(result)
        return 0
    try:
        proc = run_command(cmd, timeout_s=max(30, args.timeout_ms // 1000 + 10))
        result['status'] = classify_agent_result(proc, args.expect_final)
        result['returncode'] = proc.returncode
        result['stdout'] = proc.stdout
        result['stderr'] = proc.stderr
    except subprocess.TimeoutExpired as exc:
        result['status'] = STATUS_TIMEOUT
        result['returncode'] = 124
        result['stdout'] = exc.stdout or ''
        result['stderr'] = exc.stderr or ''
    log_path = append_log(result, Path(args.log_dir))
    result['logPath'] = str(log_path)
    print_json(result)
    return 0 if result['status'] in {STATUS_ACCEPTED, STATUS_TIMEOUT, 'final_returned'} else 1


def do_send(args: argparse.Namespace) -> int:
    cmd = build_send_command(args.target, args.text, args.account_id, args.reply_to)
    result = {
        'ts': now_ts(),
        'mode': 'send',
        'status': STATUS_DRY_RUN,
        'target': args.target,
        'text': args.text,
        'command': redact_command(cmd),
        'note': 'Manual fallback only. Does not prove taizi processed the source message.',
    }
    if args.dry_run:
        print_json(result)
        return 0
    proc = run_command(cmd, timeout_s=60)
    result['status'] = STATUS_SENT if proc.returncode == 0 else 'send_error'
    result['returncode'] = proc.returncode
    result['stdout'] = proc.stdout
    result['stderr'] = proc.stderr
    log_path = append_log(result, Path(args.log_dir))
    result['logPath'] = str(log_path)
    print_json(result)
    return 0 if proc.returncode == 0 else 1


def do_compensate(args: argparse.Namespace, cfg: Dict[str, Any]) -> int:
    token = resolve_gateway_token(cfg)
    params = build_agent_params(args)
    probe_cmd = build_agent_command(token, params, args.timeout_ms, args.expect_final)
    send_cmd = build_send_command(args.target, args.fallback_text, args.account_id, args.reply_to)
    result = {
        'ts': now_ts(),
        'mode': 'compensate',
        'status': STATUS_DRY_RUN,
        'sessionKey': getattr(args, 'session_key', ''),
        'sessionId': args.session_id,
        'target': args.target,
        'sourceMessageId': args.source_message_id,
        'agentCommand': redact_command(probe_cmd),
        'agentParams': params,
        'sendCommand': send_cmd,
        'policy': 'Try agent injection first; only send manual fallback when agent call does not return a final success in time.',
    }
    if args.dry_run:
        print_json(result)
        return 0

    try:
        probe_proc = run_command(probe_cmd, timeout_s=max(30, args.timeout_ms // 1000 + 10))
        probe_status = classify_agent_result(probe_proc, args.expect_final)
    except subprocess.TimeoutExpired as exc:
        probe_proc = subprocess.CompletedProcess(probe_cmd, 124, exc.stdout or '', exc.stderr or '')
        probe_status = STATUS_TIMEOUT

    result['agentStatus'] = probe_status
    result['agentReturncode'] = probe_proc.returncode
    result['agentStdout'] = probe_proc.stdout
    result['agentStderr'] = probe_proc.stderr

    if probe_status == 'final_returned' and not args.force_manual_send:
        result['status'] = 'agent_final_only'
        log_path = append_log(result, Path(args.log_dir))
        result['logPath'] = str(log_path)
        print_json(result)
        return 0

    send_proc = run_command(send_cmd, timeout_s=60)
    result['manualSendReturncode'] = send_proc.returncode
    result['manualSendStdout'] = send_proc.stdout
    result['manualSendStderr'] = send_proc.stderr
    if send_proc.returncode == 0:
        result['status'] = 'agent_then_manual_send' if probe_status != STATUS_DRY_RUN else STATUS_SENT
    else:
        result['status'] = 'compensation_failed'
    log_path = append_log(result, Path(args.log_dir))
    result['logPath'] = str(log_path)
    print_json(result)
    return 0 if send_proc.returncode == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Feishu bypass compensation for OpenClaw/taizi: keep a usable operator path when direct live inbound handling is unstable.'
    )
    parser.add_argument('--log-dir', default=str(DEFAULT_LOG_DIR), help='JSONL operation log directory')
    sub = parser.add_subparsers(dest='mode', required=True)

    probe = sub.add_parser('probe', help='Inject one text turn into taizi via Gateway agent RPC and record the result')
    probe.add_argument('--message', required=True, help='Text to inject into taizi')
    probe.add_argument('--agent-id', default=DEFAULT_AGENT)
    probe.add_argument('--session-key', default=DEFAULT_SESSION_KEY, help='Preferred target sessionKey for precise session binding')
    probe.add_argument('--session-id', default=DEFAULT_SESSION_ID, help='Optional legacy sessionId for traceability; not the primary binding key')
    probe.add_argument('--target', default=DEFAULT_TARGET, help='Expected Feishu delivery target for operator reference only')
    probe.add_argument('--idempotency-key', default='')
    probe.add_argument('--timeout-ms', type=int, default=20000)
    probe.add_argument('--expect-final', action='store_true', help='Wait for final response; usually not recommended for flaky live chains')
    probe.add_argument('--dry-run', action='store_true')

    send = sub.add_parser('send', help='Send a manual Feishu fallback message directly')
    send.add_argument('--target', default=DEFAULT_TARGET)
    send.add_argument('--text', required=True)
    send.add_argument('--account-id', default=DEFAULT_FEISHU_ACCOUNT)
    send.add_argument('--reply-to', default='')
    send.add_argument('--dry-run', action='store_true')

    compensate = sub.add_parser('compensate', help='Operational compensation: try agent injection, then manual fallback send')
    compensate.add_argument('--message', required=True, help='Text to inject into taizi first')
    compensate.add_argument('--fallback-text', required=True, help='Text to manually send if final reply is not confirmed in time')
    compensate.add_argument('--agent-id', default=DEFAULT_AGENT)
    compensate.add_argument('--session-key', default=DEFAULT_SESSION_KEY, help='Preferred target sessionKey for precise session binding')
    compensate.add_argument('--session-id', default=DEFAULT_SESSION_ID, help='Optional legacy sessionId for traceability; not the primary binding key')
    compensate.add_argument('--target', default=DEFAULT_TARGET)
    compensate.add_argument('--account-id', default=DEFAULT_FEISHU_ACCOUNT)
    compensate.add_argument('--reply-to', default='')
    compensate.add_argument('--source-message-id', default='', help='Original missing inbound message id, for traceability only')
    compensate.add_argument('--idempotency-key', default='')
    compensate.add_argument('--timeout-ms', type=int, default=20000)
    compensate.add_argument('--expect-final', action='store_true', help='If set, wait for final before deciding whether to manual-send')
    compensate.add_argument('--force-manual-send', action='store_true', help='Send manual fallback even if agent returns final')
    compensate.add_argument('--dry-run', action='store_true')

    args = parser.parse_args()
    cfg = load_config()
    if args.mode == 'probe':
        return do_probe(args, cfg)
    if args.mode == 'send':
        return do_send(args)
    return do_compensate(args, cfg)


if __name__ == '__main__':
    sys.exit(main())
