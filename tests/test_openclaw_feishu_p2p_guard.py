from datetime import datetime
import importlib.util
from pathlib import Path


SCRIPT_PATH = Path('/root/.openclaw/scripts/check_openclaw_feishu_p2p_guard.py')


def _load_guard_module():
    spec = importlib.util.spec_from_file_location('check_openclaw_feishu_p2p_guard', SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_parse_service_start_extracts_current_service_start_time():
    guard = _load_guard_module()
    status_text = '''● openclaw-gateway.service - OpenClaw Gateway
     Loaded: loaded (/root/.config/systemd/user/openclaw-gateway.service; enabled; preset: enabled)
     Active: active (running) since Sun 2026-04-26 17:21:08 CST; 20min ago
       Docs: https://example.invalid
    '''

    raw, dt = guard.parse_service_start(status_text)

    assert raw == 'Sun 2026-04-26 17:21:08 CST'
    assert dt == datetime(2026, 4, 26, 17, 21, 8)


def test_parse_log_events_ignores_historical_bad_event_before_current_service_start():
    guard = _load_guard_module()
    service_start = datetime(2026, 4, 26, 17, 21, 8)
    lines = [
        '{"time":"2026-04-26T17:07:57.014+08:00","msg":"no im.chat.access_event.bot_p2p_chat_entered_v1 handle"}',
        '{"time":"2026-04-26T17:14:13.875+08:00","msg":"feishu[default]: p2p chat entered chat=oc_x operator=ou_x last_message=om_x"}',
        '{"time":"2026-04-26T17:25:08.000+08:00","msg":"OPENCLAW_FEISHU_P2P_AUTOPATCH dist= /usr/lib/node_modules/@qingchencloud/openclaw-zh/dist backup= - results= monitor-BXs1Uex0.js:already_patched"}',
    ]

    events = guard.parse_log_events(lines, service_start)

    assert events['bad_count_total'] == 1
    assert events['good_count_total'] == 1
    assert events['auto_count_total'] == 1
    assert events['bad_since_service_start'] == []
    assert events['good_since_service_start'] == []
    assert len(events['auto_since_service_start']) == 1
    assert events['latest_bad_total']['time'] == '2026-04-26T17:07:57.014000'
    assert events['latest_auto_total']['time'] == '2026-04-26T17:25:08'
