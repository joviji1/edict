import importlib.util
import pathlib

ROOT = pathlib.Path('/root/.openclaw/workspace/edict')


def _load_module(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_monitor_accepts_iso_string_timestamps_without_crashing():
    monitor = _load_module('monitor_openclaw_sessions_test', ROOT / 'scripts' / 'monitor_openclaw_sessions.py')
    now_ms = monitor.coerce_epoch_ms('2026-05-11T07:40:00Z')
    entry = {
        'sessionId': 'sid-iso-1',
        'status': 'running',
        'updatedAt': '2026-05-11T07:39:00Z',
        'startedAt': '2026-05-11T07:00:00Z',
        'sessionFile': '/tmp/nonexistent-session-file.jsonl',
    }

    issues = monitor.check_session('agent:test:iso', entry, now_ms, 3600, 1800)

    assert any(issue['type'] == 'long_running' for issue in issues)
    assert not any('unsupported operand' in issue.get('message', '') for issue in issues)


def test_monitor_accepts_epoch_seconds_and_milliseconds():
    monitor = _load_module('monitor_openclaw_sessions_time_test', ROOT / 'scripts' / 'monitor_openclaw_sessions.py')

    assert monitor.coerce_epoch_ms(1715400000) == 1715400000000
    assert monitor.coerce_epoch_ms(1715400000000) == 1715400000000
    assert monitor.coerce_epoch_ms('1715400000') == 1715400000000
    assert monitor.coerce_epoch_ms('1715400000000') == 1715400000000


def test_monitor_ignores_model_error_for_done_session_after_noise_clear(tmp_path):
    monitor = _load_module('monitor_openclaw_sessions_noise_test', ROOT / 'scripts' / 'monitor_openclaw_sessions.py')
    transcript = tmp_path / 'session.jsonl'
    transcript.write_text('{"type":"custom","customType":"openclaw:prompt-error","data":{"error":"aborted","provider":"windhub","model":"gpt-5.4"}}\n')
    entry = {
        'sessionId': 'sid-noise-cleared',
        'status': 'done',
        'updatedAt': '2026-05-11T09:00:00Z',
        'startedAt': '2026-05-11T08:00:00Z',
        'abortedLastRun': False,
        'sessionFile': str(transcript),
        'metadata': {'noiseClearedBy': 'hermes-operational-verification'},
    }
    now_ms = monitor.coerce_epoch_ms('2026-05-11T09:10:00Z')

    issues = monitor.check_session('agent:taizi:done-noise', entry, now_ms, 3600, 1800)

    assert not any(issue['type'] == 'model_error' for issue in issues)


def test_feishu_relay_redacts_gateway_token_in_display_command():
    relay = _load_module('openclaw_feishu_relay_test', ROOT / 'scripts' / 'openclaw_feishu_relay.py')
    cmd = ['openclaw', 'gateway', 'call', 'agent', '--token', 'secret-token-value', '--params', '{}']

    assert relay.redact_command(cmd) == [
        'openclaw', 'gateway', 'call', 'agent', '--token', '[REDACTED]', '--params', '{}'
    ]
    assert 'secret-token-value' not in ' '.join(relay.redact_command(cmd))
