"""tests for dashboard/server.py route handling"""
import datetime
import json, pathlib, sys, threading, time
from http.client import HTTPConnection

# Add project paths
ROOT = pathlib.Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / 'dashboard'
SCRIPTS = ROOT / 'scripts'
sys.path.insert(0, str(DASHBOARD))
sys.path.insert(0, str(SCRIPTS))


def recent_iso(hours_ago=0):
    dt = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=hours_ago)
    return dt.replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def test_healthz(tmp_path):
    """GET /healthz returns 200 with status ok."""
    # Create minimal data dir
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    (data_dir / 'live_status.json').write_text('{}')
    (data_dir / 'agent_config.json').write_text('{}')

    # Import and patch server
    import server as srv
    srv.DATA = data_dir

    from http.server import HTTPServer
    port = 18971

    httpd = HTTPServer(('127.0.0.1', port), srv.Handler)
    t = threading.Thread(target=httpd.handle_request, daemon=True)
    t.start()

    time.sleep(0.1)
    conn = HTTPConnection('127.0.0.1', port, timeout=5)
    conn.request('GET', '/healthz')
    resp = conn.getresponse()
    body = json.loads(resp.read())
    conn.close()

    assert resp.status == 200
    assert body['status'] in ('ok', 'degraded')

    httpd.server_close()


def test_check_auth_verifier_exception_returns_401(tmp_path, monkeypatch):
    """verify_token 自身异常时，认证层应返回 401，而不是断开连接。"""
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    (data_dir / 'tasks_source.json').write_text('[]', encoding='utf-8')

    import server as srv
    srv.DATA = data_dir
    srv._ACTIVE_TASK_DATA_DIR = None
    monkeypatch.setattr(srv, 'requires_auth', lambda path: True)
    monkeypatch.setattr(srv, 'verify_token', lambda token: (_ for _ in ()).throw(RuntimeError('token verifier crashed')))

    from http.server import HTTPServer
    port = 18973
    httpd = HTTPServer(('127.0.0.1', port), srv.Handler)
    t = threading.Thread(target=httpd.handle_request, daemon=True)
    t.start()
    time.sleep(0.1)

    conn = HTTPConnection('127.0.0.1', port, timeout=5)
    conn.request('GET', '/api/live-status', headers={'Authorization': 'Bearer bad-token'})
    resp = conn.getresponse()
    body = json.loads(resp.read())
    conn.close()
    httpd.server_close()

    assert resp.status == 401
    assert body['ok'] is False
    assert '未登录' in body['error']


def test_check_auth_requires_auth_exception_returns_401(tmp_path, monkeypatch):
    """requires_auth 自身异常时，认证层应返回 401，而不是断开连接。"""
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    (data_dir / 'tasks_source.json').write_text('[]', encoding='utf-8')

    import server as srv
    srv.DATA = data_dir
    srv._ACTIVE_TASK_DATA_DIR = None
    monkeypatch.setattr(srv, 'requires_auth', lambda path: (_ for _ in ()).throw(RuntimeError('requires_auth crashed')))

    from http.server import HTTPServer
    port = 18976
    httpd = HTTPServer(('127.0.0.1', port), srv.Handler)
    t = threading.Thread(target=httpd.handle_request, daemon=True)
    t.start()
    time.sleep(0.1)

    conn = HTTPConnection('127.0.0.1', port, timeout=5)
    conn.request('GET', '/api/live-status', headers={'Authorization': 'Bearer bad-token'})
    resp = conn.getresponse()
    body = json.loads(resp.read())
    conn.close()
    httpd.server_close()

    assert resp.status == 401
    assert body['ok'] is False
    assert '未登录' in body['error']


def test_check_auth_extract_token_exception_returns_401(tmp_path, monkeypatch):
    """extract_token 自身异常时，认证层应返回 401，而不是断开连接。"""
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    (data_dir / 'tasks_source.json').write_text('[]', encoding='utf-8')

    import server as srv
    srv.DATA = data_dir
    srv._ACTIVE_TASK_DATA_DIR = None
    monkeypatch.setattr(srv, 'requires_auth', lambda path: True)
    monkeypatch.setattr(srv, 'extract_token', lambda headers: (_ for _ in ()).throw(RuntimeError('extract_token crashed')))

    from http.server import HTTPServer
    port = 18977
    httpd = HTTPServer(('127.0.0.1', port), srv.Handler)
    t = threading.Thread(target=httpd.handle_request, daemon=True)
    t.start()
    time.sleep(0.1)

    conn = HTTPConnection('127.0.0.1', port, timeout=5)
    conn.request('GET', '/api/live-status', headers={'Authorization': 'Bearer bad-token'})
    resp = conn.getresponse()
    body = json.loads(resp.read())
    conn.close()
    httpd.server_close()

    assert resp.status == 401
    assert body['ok'] is False
    assert '未登录' in body['error']


def test_remote_skills_api_lists_source_managed_skill(tmp_path):
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    (data_dir / 'live_status.json').write_text('{}', encoding='utf-8')
    (data_dir / 'agent_config.json').write_text(json.dumps({
        'agents': [{'id': 'zaochao', 'label': '钦天监', 'skills': [{'name': 'weather', 'description': '朝报天气'}]}]
    }, ensure_ascii=False), encoding='utf-8')

    oc_home = tmp_path / '.openclaw'
    skill_dir = oc_home / 'workspace-zaochao' / 'skills' / 'weather'
    skill_dir.mkdir(parents=True)
    (skill_dir / 'SKILL.md').write_text('# weather\n', encoding='utf-8')
    (skill_dir / '.source.json').write_text(json.dumps({
        'skillName': 'weather',
        'sourceUrl': 'https://example.com/weather/SKILL.md',
        'description': '朝报天气',
        'addedAt': '2026-04-21T06:00:00Z',
        'lastUpdated': '2026-04-21T06:05:00Z',
        'status': 'valid',
    }, ensure_ascii=False), encoding='utf-8')

    import server as srv
    srv.DATA = data_dir
    srv.OCLAW_HOME = oc_home

    from http.server import HTTPServer
    port = 18975
    httpd = HTTPServer(('127.0.0.1', port), srv.Handler)
    t = threading.Thread(target=httpd.handle_request, daemon=True)
    t.start()

    time.sleep(0.1)
    conn = HTTPConnection('127.0.0.1', port, timeout=5)
    conn.request('POST', '/api/remote-skills-list', body='{}', headers={'Content-Type': 'application/json'})
    resp = conn.getresponse()
    body = json.loads(resp.read())
    conn.close()

    assert resp.status == 200
    assert body['ok'] is True
    assert body['count'] == 1
    assert body['remoteSkills'][0]['agentId'] == 'zaochao'
    assert body['remoteSkills'][0]['skillName'] == 'weather'
    assert body['remoteSkills'][0]['sourceUrl'] == 'https://example.com/weather/SKILL.md'

    httpd.server_close()



def test_task_autopsy_get_returns_report(tmp_path):
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    report = data_dir / 'autopsy' / 'TEST-AUTOPSY-GET.md'
    report.parent.mkdir()
    report.write_text('# autopsy\nprovider_timeout\n', encoding='utf-8')
    (data_dir / 'tasks_source.json').write_text(json.dumps([{
        'id': 'TEST-AUTOPSY-GET',
        'state': 'Blocked',
        'autopsy': {'path': str(report), 'reason': 'provider_timeout', 'generatedAt': '2026-04-17T00:00:00Z'},
    }], ensure_ascii=False))

    import server as srv
    srv.DATA = data_dir
    srv._ACTIVE_TASK_DATA_DIR = None

    from http.server import HTTPServer
    port = 18972
    httpd = HTTPServer(('127.0.0.1', port), srv.Handler)
    t = threading.Thread(target=httpd.handle_request, daemon=True)
    t.start()
    time.sleep(0.1)

    conn = HTTPConnection('127.0.0.1', port, timeout=5)
    conn.request('GET', '/api/task-autopsy/TEST-AUTOPSY-GET')
    resp = conn.getresponse()
    body = json.loads(resp.read())
    conn.close()

    assert resp.status == 200
    assert body['ok'] is True
    assert body['exists'] is True
    assert body['autopsy']['reason'] == 'provider_timeout'
    assert 'provider_timeout' in body['content']

    httpd.server_close()



def test_scheduler_state_exposes_pending_confirm_and_gate_checks(tmp_path):
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    (data_dir / 'tasks_source.json').write_text(json.dumps([{
        'id': 'TEST-GATE-GET',
        'state': 'PendingConfirm',
        'org': '尚书省',
        '_scheduler': {'stallThresholdSec': 180, 'retryCount': 1},
        'pending_confirm': {
            'target_state': 'Done',
            'requested_by': 'shangshu',
            'requested_at': '2026-04-17T00:00:00Z',
            'confirm_by': 'menxia',
            'risk_key': 'Review->Done',
            'status': 'pending',
        },
        'gate_checks': [{
            'at': '2026-04-17T00:00:00Z',
            'gate': 'high_risk_transition',
            'from': 'Review',
            'to': 'Done',
            'confirm_by': 'menxia',
            'result': 'pending',
        }],
    }], ensure_ascii=False), encoding='utf-8')

    import server as srv
    srv.DATA = data_dir
    srv._ACTIVE_TASK_DATA_DIR = None

    body = srv.get_scheduler_state('TEST-GATE-GET')
    assert body['ok'] is True
    assert body['state'] == 'PendingConfirm'
    assert body['pendingConfirm']['risk_key'] == 'Review->Done'
    assert body['gateChecks'][0]['result'] == 'pending'


def test_review_action_approve_pending_confirm_updates_gate_resolution(tmp_path):
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    (data_dir / 'tasks_source.json').write_text(json.dumps([{
        'id': 'TEST-GATE-APPROVE',
        'title': '待门禁批准',
        'state': 'PendingConfirm',
        'org': '尚书省',
        'now': '待确认',
        'pending_confirm': {
            'target_state': 'Done',
            'requested_by': 'shangshu',
            'requested_at': '2026-04-17T00:00:00Z',
            'confirm_by': 'menxia',
            'risk_key': 'Review->Done',
            'status': 'pending',
        },
        'gate_checks': [{
            'at': '2026-04-17T00:00:00Z',
            'gate': 'high_risk_transition',
            'from': 'Review',
            'to': 'Done',
            'confirm_by': 'menxia',
            'risk_key': 'Review->Done',
            'result': 'pending',
        }],
        'flow_log': [],
        'updatedAt': '2026-04-17T00:00:00Z',
    }], ensure_ascii=False), encoding='utf-8')

    import server as srv
    srv.DATA = data_dir
    srv._ACTIVE_TASK_DATA_DIR = None

    result = srv.handle_review_action('TEST-GATE-APPROVE', 'approve', '准奏')
    assert result['ok'] is True

    tasks = json.loads((data_dir / 'tasks_source.json').read_text(encoding='utf-8'))
    task = tasks[0]
    assert task['state'] == 'Done'
    assert task['now'] == '御批通过，任务完成'
    assert 'pending_confirm' not in task
    assert task['gate_checks'][-1]['result'] == 'approved'
    assert task['gate_checks'][-1]['to'] == 'Done'
    assert any(item['remark'].startswith('✅') for item in task['flow_log'])


def test_review_action_reject_pending_confirm_returns_to_zhongshu(tmp_path):
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    (data_dir / 'tasks_source.json').write_text(json.dumps([{
        'id': 'TEST-GATE-REJECT',
        'title': '待门禁驳回',
        'state': 'PendingConfirm',
        'org': '尚书省',
        'now': '待确认',
        'pending_confirm': {
            'target_state': 'Cancelled',
            'requested_by': 'gongbu',
            'requested_at': '2026-04-17T00:00:00Z',
            'confirm_by': 'shangshu',
            'risk_key': 'Doing->Cancelled',
            'status': 'pending',
        },
        'gate_checks': [{
            'at': '2026-04-17T00:00:00Z',
            'gate': 'high_risk_transition',
            'from': 'Doing',
            'to': 'Cancelled',
            'confirm_by': 'shangshu',
            'risk_key': 'Doing->Cancelled',
            'result': 'pending',
        }],
        'flow_log': [],
        'updatedAt': '2026-04-17T00:00:00Z',
    }], ensure_ascii=False), encoding='utf-8')

    import server as srv
    srv.DATA = data_dir
    srv._ACTIVE_TASK_DATA_DIR = None

    result = srv.handle_review_action('TEST-GATE-REJECT', 'reject', '封驳')
    assert result['ok'] is True

    tasks = json.loads((data_dir / 'tasks_source.json').read_text(encoding='utf-8'))
    task = tasks[0]
    assert task['state'] == 'Zhongshu'
    assert task['review_round'] == 1
    assert 'pending_confirm' not in task
    assert task['gate_checks'][-1]['result'] == 'rejected'
    assert task['gate_checks'][-1]['to'] == 'Cancelled'
    assert '第1轮' in task['now']


def test_get_remote_skills_list_only_returns_source_managed_skills(tmp_path):
    import server as srv

    oc_home = tmp_path / '.openclaw'
    taizi_remote = oc_home / 'workspace-taizi' / 'skills' / 'elite-longterm-memory'
    taizi_remote.mkdir(parents=True)
    (taizi_remote / 'SKILL.md').write_text('---\nname: elite-longterm-memory\n---\n', encoding='utf-8')
    (taizi_remote / '.source.json').write_text(json.dumps({
        'skillName': 'elite-longterm-memory',
        'sourceUrl': 'https://example.com/elite-longterm-memory/SKILL.md',
        'description': 'remote skill',
        'addedAt': '2026-04-21T06:00:00Z',
        'lastUpdated': '2026-04-21T06:05:00Z',
    }, ensure_ascii=False), encoding='utf-8')

    libu_local = oc_home / 'workspace-libu' / 'skills' / 'summarize'
    libu_local.mkdir(parents=True)
    (libu_local / 'SKILL.md').write_text('---\nname: summarize\n---\n', encoding='utf-8')

    srv.OCLAW_HOME = oc_home

    result = srv.get_remote_skills_list()

    assert result['ok'] is True
    assert result['count'] == 1
    assert result['remoteSkills'][0]['agentId'] == 'taizi'
    assert result['remoteSkills'][0]['skillName'] == 'elite-longterm-memory'


def test_add_remote_skill_success_writes_source_metadata_and_resyncs_agent_config(tmp_path, monkeypatch):
    import server as srv

    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    (data_dir / 'agent_config.json').write_text(json.dumps({
        'agents': [
            {'id': 'zaochao'},
        ]
    }, ensure_ascii=False), encoding='utf-8')

    oc_home = tmp_path / '.openclaw'
    outside_source = tmp_path / 'remote-skill.md'
    outside_source.write_text('---\nname: weather\ndescription: weather skill\n---\n# weather\n', encoding='utf-8')
    source = oc_home / 'imports' / 'remote-skill.md'
    source.parent.mkdir(parents=True)
    source.write_text(outside_source.read_text(encoding='utf-8'), encoding='utf-8')

    sync_calls = []

    def fake_run(cmd, timeout=None, **kwargs):
        sync_calls.append({'cmd': cmd, 'timeout': timeout, 'kwargs': kwargs})
        return None

    srv.DATA = data_dir
    srv.OCLAW_HOME = oc_home
    monkeypatch.setattr(srv.subprocess, 'run', fake_run)

    result = srv.add_remote_skill('zaochao', 'weather', str(source), '朝报与天气')

    skill_dir = oc_home / 'workspace-zaochao' / 'skills' / 'weather'
    skill_md = skill_dir / 'SKILL.md'
    source_json = skill_dir / '.source.json'

    assert result['ok'] is True
    assert result['agentId'] == 'zaochao'
    assert result['skillName'] == 'weather'
    assert skill_md.exists()
    assert skill_md.read_text(encoding='utf-8') == source.read_text(encoding='utf-8')
    assert source_json.exists()

    source_info = json.loads(source_json.read_text(encoding='utf-8'))
    assert source_info['skillName'] == 'weather'
    assert source_info['sourceUrl'] == str(source)
    assert source_info['description'] == '朝报与天气'
    assert source_info['status'] == 'valid'
    assert source_info['checksum']
    assert source_info['addedAt']
    assert source_info['lastUpdated']

    assert sync_calls[-1] == {'cmd': [srv.python_bin(), str(srv.SCRIPTS / 'sync_agent_config.py')], 'timeout': 10, 'kwargs': {}}


def test_add_remote_skill_rejects_unknown_agent(tmp_path):
    import server as srv

    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    (data_dir / 'agent_config.json').write_text(json.dumps({'agents': []}, ensure_ascii=False), encoding='utf-8')

    source = tmp_path / 'remote-skill.md'
    source.write_text('---\nname: remote-skill\ndescription: test\n---\n# remote\n', encoding='utf-8')

    srv.DATA = data_dir

    result = srv.add_remote_skill('libu_hr', 'remote-skill', str(source), 'test skill')

    assert result['ok'] is False
    assert '不存在' in result['error']


def test_remove_remote_skill_deletes_workspace_and_resyncs_agent_config(tmp_path, monkeypatch):
    import server as srv

    oc_home = tmp_path / '.openclaw'
    skill_dir = oc_home / 'workspace-zaochao' / 'skills' / 'weather'
    skill_dir.mkdir(parents=True)
    (skill_dir / 'SKILL.md').write_text('---\nname: weather\n---\n', encoding='utf-8')
    (skill_dir / '.source.json').write_text(json.dumps({
        'skillName': 'weather',
        'sourceUrl': 'https://example.com/weather/SKILL.md',
        'description': '朝报与天气',
        'addedAt': '2026-04-21T06:00:00Z',
        'lastUpdated': '2026-04-21T06:05:00Z',
    }, ensure_ascii=False), encoding='utf-8')

    sync_calls = []

    def fake_run(cmd, timeout=None):
        sync_calls.append({'cmd': cmd, 'timeout': timeout})
        return None

    srv.OCLAW_HOME = oc_home
    monkeypatch.setattr(srv.subprocess, 'run', fake_run)

    result = srv.remove_remote_skill('zaochao', 'weather')

    assert result['ok'] is True
    assert not skill_dir.exists()
    assert sync_calls == [{'cmd': [srv.python_bin(), str(srv.SCRIPTS / 'sync_agent_config.py')], 'timeout': 10}]


def test_save_tasks_sends_pending_confirm_notification_once(tmp_path, monkeypatch):
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    (data_dir / 'morning_brief_config.json').write_text(json.dumps({
        'notification': {
            'enabled': True,
            'channel': 'feishu',
            'webhook': 'https://example.com/webhook/test'
        }
    }, ensure_ascii=False), encoding='utf-8')

    import server as srv
    srv.DATA = data_dir
    srv._ACTIVE_TASK_DATA_DIR = None

    sent = []

    class DummyChannel:
        label = '测试渠道'

        @classmethod
        def validate_webhook(cls, webhook):
            return True

        @classmethod
        def send(cls, webhook, title, content, url=None):
            sent.append({'webhook': webhook, 'title': title, 'content': content, 'url': url})
            return True

    monkeypatch.setattr(srv, 'get_channel', lambda channel_type: DummyChannel)

    tasks = [{
        'id': 'TEST-PENDING-NOTIFY',
        'title': '待审批通知测试',
        'state': 'PendingConfirm',
        'org': '尚书省',
        'now': '待确认：Review→Done',
        'pending_confirm': {
            'target_state': 'Done',
            'requested_by': 'shangshu',
            'requested_at': '2026-04-17T00:00:00Z',
            'confirm_by': 'menxia',
            'risk_key': 'Review->Done',
            'status': 'pending',
        },
        'gate_checks': [{
            'at': '2026-04-17T00:00:00Z',
            'gate': 'high_risk_transition',
            'from': 'Review',
            'to': 'Done',
            'confirm_by': 'menxia',
            'risk_key': 'Review->Done',
            'result': 'pending',
        }],
        'updatedAt': '2026-04-17T00:00:00Z',
    }]

    srv.save_tasks(tasks)
    saved = json.loads((data_dir / 'tasks_source.json').read_text(encoding='utf-8'))[0]
    assert len(sent) == 1
    assert '待审批' in sent[0]['title']
    assert 'TEST-PENDING-NOTIFY' in sent[0]['content']
    assert 'Review → Done' in sent[0]['content']
    assert saved.get('notifications', {}).get('pending_confirm_sent') is True

    srv.save_tasks(saved if isinstance(saved, list) else [saved])
    assert len(sent) == 1



def test_save_tasks_syncs_governance_samples_after_write(tmp_path, monkeypatch):
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    (data_dir / 'tasks_runtime_view.json').write_text('[]', encoding='utf-8')
    (data_dir / 'mission_control_tasks.json').write_text('[]', encoding='utf-8')
    (data_dir / 'manual_parallel_tasks.json').write_text('[]', encoding='utf-8')

    import server as srv
    srv.DATA = data_dir
    srv._ACTIVE_TASK_DATA_DIR = None

    real_run = srv.subprocess.run

    class DummyThread:
        def __init__(self, target=None, daemon=None):
            self.target = target
            self.daemon = daemon

        def start(self):
            return None

    def fake_run(cmd, timeout=None, **kwargs):
        if isinstance(cmd, list) and len(cmd) >= 2 and str(cmd[1]).endswith('sync_governance_samples.py'):
            return real_run(cmd, timeout=timeout, **kwargs)
        return type('Completed', (), {'returncode': 0})()

    monkeypatch.setattr(srv.subprocess, 'run', fake_run)
    monkeypatch.setattr(srv.threading, 'Thread', DummyThread)

    tasks = [{
        'id': 'TEST-SYNC-GOV-SAMPLES',
        'title': '样本同步测试',
        'state': 'PendingConfirm',
        'pending_confirm': {
            'target_state': 'Done',
            'requested_at': recent_iso(1),
        },
        'gate_checks': [{'result': 'pending'}],
        'updatedAt': recent_iso(),
    }]

    srv.save_tasks(tasks)

    payload = json.loads((data_dir / 'tasks_governance_samples.json').read_text(encoding='utf-8'))
    item = next(entry for entry in payload if entry['id'] == 'TEST-SYNC-GOV-SAMPLES')
    assert item['sourceLayer'] == 'governance_sample'
    assert item['pending_confirm']['target_state'] == 'Done'
    assert item['gate_checks'][0]['result'] == 'pending'
    assert 'legacy_tasks_source' in item['sampleSources']



def test_review_action_approve_pending_confirm_sends_approval_notification(tmp_path, monkeypatch):
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    (data_dir / 'morning_brief_config.json').write_text(json.dumps({
        'notification': {
            'enabled': True,
            'channel': 'feishu',
            'webhook': 'https://example.com/webhook/test'
        }
    }, ensure_ascii=False), encoding='utf-8')
    (data_dir / 'tasks_source.json').write_text(json.dumps([{
        'id': 'TEST-GATE-APPROVE-NOTIFY',
        'title': '审批结果通知测试',
        'state': 'PendingConfirm',
        'org': '尚书省',
        'now': '待确认',
        'pending_confirm': {
            'target_state': 'Done',
            'requested_by': 'shangshu',
            'requested_at': '2026-04-17T00:00:00Z',
            'confirm_by': 'menxia',
            'risk_key': 'Review->Done',
            'status': 'pending',
        },
        'gate_checks': [{
            'at': '2026-04-17T00:00:00Z',
            'gate': 'high_risk_transition',
            'from': 'Review',
            'to': 'Done',
            'confirm_by': 'menxia',
            'risk_key': 'Review->Done',
            'result': 'pending',
        }],
        'flow_log': [],
        'updatedAt': '2026-04-17T00:00:00Z',
    }], ensure_ascii=False), encoding='utf-8')

    import server as srv
    srv.DATA = data_dir
    srv._ACTIVE_TASK_DATA_DIR = None

    sent = []

    class DummyChannel:
        label = '测试渠道'

        @classmethod
        def validate_webhook(cls, webhook):
            return True

        @classmethod
        def send(cls, webhook, title, content, url=None):
            sent.append({'webhook': webhook, 'title': title, 'content': content, 'url': url})
            return True

    monkeypatch.setattr(srv, 'get_channel', lambda channel_type: DummyChannel)

    result = srv.handle_review_action('TEST-GATE-APPROVE-NOTIFY', 'approve', '准奏')
    assert result['ok'] is True
    assert len(sent) == 1
    assert '审批结果' in sent[0]['title']
    assert '已准奏' in sent[0]['content']
    assert 'TEST-GATE-APPROVE-NOTIFY' in sent[0]['content']


def test_get_approval_panel_returns_pending_and_full_history(tmp_path):
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    (data_dir / 'tasks_source.json').write_text(json.dumps([
        {
            'id': 'TEST-APPROVAL-PENDING',
            'title': '待批面板任务',
            'state': 'PendingConfirm',
            'org': '尚书省',
            'now': '待确认：Review→Done',
            'pending_confirm': {
                'target_state': 'Done',
                'requested_by': 'shangshu',
                'requested_at': '2026-04-18T02:00:00Z',
                'confirm_by': 'menxia',
                'risk_key': 'Review->Done',
                'status': 'pending',
            },
            'gate_checks': [
                {
                    'at': '2026-04-18T02:00:00Z',
                    'gate': 'high_risk_transition',
                    'from': 'Review',
                    'to': 'Done',
                    'confirm_by': 'menxia',
                    'risk_key': 'Review->Done',
                    'result': 'pending',
                }
            ],
        },
        {
            'id': 'TEST-APPROVAL-HISTORY',
            'title': '历史批示任务',
            'state': 'Done',
            'org': '尚书省',
            'now': '御批通过，任务完成',
            'gate_checks': [
                {
                    'at': '2026-04-17T03:00:00Z',
                    'gate': 'high_risk_transition',
                    'from': 'Review',
                    'to': 'Done',
                    'confirm_by': 'menxia',
                    'risk_key': 'Review->Done',
                    'result': 'pending',
                },
                {
                    'at': '2026-04-17T03:05:00Z',
                    'gate': 'high_risk_transition',
                    'from': 'Review',
                    'to': 'Done',
                    'confirm_by': 'menxia',
                    'risk_key': 'Review->Done',
                    'result': 'approved',
                },
            ],
        },
        {
            'id': 'TEST-APPROVAL-REJECTED',
            'title': '封驳历史任务',
            'state': 'Zhongshu',
            'org': '中书省',
            'now': '门下封驳，退回中书省第1轮修订',
            'gate_checks': [
                {
                    'at': '2026-04-16T01:00:00Z',
                    'gate': 'high_risk_transition',
                    'from': 'Doing',
                    'to': 'Cancelled',
                    'confirm_by': 'shangshu',
                    'risk_key': 'Doing->Cancelled',
                    'result': 'rejected',
                },
            ],
        }
    ], ensure_ascii=False), encoding='utf-8')

    import server as srv
    srv.DATA = data_dir
    srv._ACTIVE_TASK_DATA_DIR = None

    body = srv.get_approval_panel()
    assert body['ok'] is True
    assert body['stats']['pending'] == 1
    assert body['stats']['approved'] == 1
    assert body['stats']['rejected'] == 1
    assert body['stats']['pendingHistory'] == 2
    assert body['stats']['totalHistory'] == 4
    assert body['pending'][0]['taskId'] == 'TEST-APPROVAL-PENDING'
    assert body['pending'][0]['riskKey'] == 'Review->Done'
    assert body['pending'][0]['latestPendingCheck']['result'] == 'pending'
    assert [item['taskId'] for item in body['history'][:2]] == ['TEST-APPROVAL-PENDING', 'TEST-APPROVAL-HISTORY']
    assert body['history'][0]['result'] == 'pending'


def test_approval_panel_route_returns_panel_payload(tmp_path):
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    (data_dir / 'tasks_source.json').write_text(json.dumps([{
        'id': 'TEST-APPROVAL-ROUTE',
        'title': '待批路由测试',
        'state': 'PendingConfirm',
        'org': '尚书省',
        'now': '待确认',
        'pending_confirm': {
            'target_state': 'Done',
            'requested_by': 'shangshu',
            'requested_at': '2026-04-18T04:00:00Z',
            'confirm_by': 'menxia',
            'risk_key': 'Review->Done',
            'status': 'pending',
        },
        'gate_checks': [{
            'at': '2026-04-18T04:00:00Z',
            'gate': 'high_risk_transition',
            'from': 'Review',
            'to': 'Done',
            'confirm_by': 'menxia',
            'risk_key': 'Review->Done',
            'result': 'pending',
        }],
    }], ensure_ascii=False), encoding='utf-8')

    import server as srv
    srv.DATA = data_dir
    srv._ACTIVE_TASK_DATA_DIR = None

    from http.server import HTTPServer
    port = 18974
    httpd = HTTPServer(('127.0.0.1', port), srv.Handler)
    t = threading.Thread(target=httpd.handle_request, daemon=True)
    t.start()
    time.sleep(0.1)

    conn = HTTPConnection('127.0.0.1', port, timeout=5)
    conn.request('GET', '/api/approval-panel')
    resp = conn.getresponse()
    body = json.loads(resp.read())
    conn.close()

    assert resp.status == 200
    assert body['ok'] is True
    assert body['stats']['pending'] == 1
    assert body['pending'][0]['taskId'] == 'TEST-APPROVAL-ROUTE'

    httpd.server_close()


def test_task_command_panel_route_returns_scheduler_actions(tmp_path):
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    (data_dir / 'tasks_source.json').write_text(json.dumps([{
        'id': 'TEST-CMD-PANEL',
        'title': '命令面板测试',
        'state': 'Doing',
        'org': '尚书省',
        'updatedAt': '2026-04-17T00:00:00Z',
        '_scheduler': {
            'stallThresholdSec': 180,
            'retryCount': 2,
            'snapshot': {'state': 'Doing', 'updatedAt': '2026-04-17T00:00:00Z'}
        },
    }], ensure_ascii=False), encoding='utf-8')

    import server as srv
    srv.DATA = data_dir
    srv._ACTIVE_TASK_DATA_DIR = None

    from http.server import HTTPServer
    port = 18973
    httpd = HTTPServer(('127.0.0.1', port), srv.Handler)
    t = threading.Thread(target=httpd.handle_request, daemon=True)
    t.start()
    time.sleep(0.1)

    conn = HTTPConnection('127.0.0.1', port, timeout=5)
    conn.request('GET', '/api/task-command-panel/TEST-CMD-PANEL')
    resp = conn.getresponse()
    body = json.loads(resp.read())
    conn.close()

    assert resp.status == 200
    assert body['ok'] is True
    actions = {item['action']: item for item in body['commands']}
    assert actions['retry']['enabled'] is True
    assert actions['rollback']['enabled'] is True
    assert actions['autopsy']['api'] == '/api/task-autopsy'

    httpd.server_close()


def test_handle_scheduler_scan_retries_stalled_task_and_records_trigger(tmp_path):
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    (data_dir / 'tasks_source.json').write_text(json.dumps([{
        'id': 'TEST-SCHED-SCAN-RETRY',
        'title': '巡检重试样本',
        'state': 'Doing',
        'org': '工部',
        'updatedAt': '2026-04-17T00:00:00Z',
        '_scheduler': {
            'enabled': True,
            'stallThresholdSec': 180,
            'maxRetry': 1,
            'retryCount': 0,
            'escalationLevel': 0,
            'autoRollback': True,
            'lastProgressAt': '2026-04-17T00:00:00Z',
            'stallSince': None,
            'lastDispatchStatus': 'idle',
            'snapshot': {'state': 'Doing', 'org': '工部', 'now': '巡检重试样本', 'savedAt': '2026-04-17T00:00:00Z', 'note': 'init'}
        },
    }], ensure_ascii=False), encoding='utf-8')

    import server as srv
    srv.DATA = data_dir
    srv._ACTIVE_TASK_DATA_DIR = None

    called = []
    old_dispatch = srv.dispatch_for_state
    try:
        srv.dispatch_for_state = lambda task_id, task, state, trigger='state-transition': called.append({
            'task_id': task_id,
            'state': state,
            'trigger': trigger,
        })

        result = srv.handle_scheduler_scan(180)
        saved = json.loads((data_dir / 'tasks_source.json').read_text(encoding='utf-8'))[0]
    finally:
        srv.dispatch_for_state = old_dispatch

    assert result['ok'] is True
    assert result['count'] == 1
    assert result['actions'][0]['taskId'] == 'TEST-SCHED-SCAN-RETRY'
    assert result['actions'][0]['action'] == 'retry'
    assert called == [{
        'task_id': 'TEST-SCHED-SCAN-RETRY',
        'state': 'Doing',
        'trigger': 'taizi-scan-retry',
    }]
    assert saved['_scheduler']['retryCount'] == 1
    assert saved['_scheduler']['lastDispatchTrigger'] == 'taizi-scan-retry'
    assert saved['_scheduler']['stallSince'] is not None
    assert '停滞' in saved['flow_log'][-1]['remark']


def test_handle_scheduler_scan_suppresses_backend_export_empty_scheduler_retry(tmp_path):
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    (data_dir / 'tasks_source.json').write_text(json.dumps([{
        'id': 'TEST-SCHED-BACKEND-EXPORT-GUARD-1',
        'title': 'backend export 空调度保护',
        'state': 'Zhongshu',
        'org': '中书省',
        'sourceLayer': 'backend_export',
        'updatedAt': '2026-04-17T00:00:00Z',
        '_scheduler': {},
    }], ensure_ascii=False), encoding='utf-8')

    import server as srv
    srv.DATA = data_dir
    srv._ACTIVE_TASK_DATA_DIR = None

    called = []
    old_dispatch = srv.dispatch_for_state
    try:
        srv.dispatch_for_state = lambda task_id, task, state, trigger='state-transition': called.append({
            'task_id': task_id,
            'state': state,
            'trigger': trigger,
        })
        result = srv.handle_scheduler_scan(180)
        saved = json.loads((data_dir / 'tasks_source.json').read_text(encoding='utf-8'))[0]
    finally:
        srv.dispatch_for_state = old_dispatch

    assert result['ok'] is True
    assert result['count'] == 0
    assert result['actions'] == []
    assert called == []
    assert saved['_scheduler']['lastDispatchTrigger'] == 'taizi-scan-backend-export-guard'
    assert saved['_scheduler']['lastDispatchStatus'] == 'suppressed-backend-export-empty-scheduler'
    assert '旧态重复派发保护' in saved['_scheduler']['lastDispatchError']
    assert 'sourceLayer=backend_export' in saved['_scheduler']['lastDispatchError']
    assert any('跳过自动重试' in str(item.get('remark', '')) for item in saved.get('flow_log', []))


def test_dispatch_for_state_falls_back_to_target_dept_when_org_is_generic(tmp_path, monkeypatch):
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    (data_dir / 'tasks_source.json').write_text(json.dumps([{
        'id': 'TEST-DISPATCH-TARGETDEPT-1',
        'title': '按模板建议派工',
        'state': 'Doing',
        'org': '执行中',
        'targetDept': '工部',
        'updatedAt': '2026-04-17T00:00:00Z',
        '_scheduler': {
            'enabled': True,
            'stallThresholdSec': 180,
            'maxRetry': 1,
            'retryCount': 0,
            'escalationLevel': 0,
            'autoRollback': True,
            'lastProgressAt': '2026-04-17T00:00:00Z',
            'stallSince': None,
            'lastDispatchStatus': 'idle',
            'snapshot': {'state': 'Doing', 'org': '执行中', 'now': '待派发', 'savedAt': '2026-04-17T00:00:00Z', 'note': 'init'}
        },
    }], ensure_ascii=False), encoding='utf-8')

    import server as srv
    srv.DATA = data_dir
    srv._ACTIVE_TASK_DATA_DIR = None

    monkeypatch.setattr(srv, '_check_gateway_alive', lambda: False)

    class InlineThread:
        def __init__(self, target=None, daemon=None, args=(), kwargs=None):
            self.target = target
            self.args = args
            self.kwargs = kwargs or {}
        def start(self):
            if self.target:
                self.target(*self.args, **self.kwargs)

    monkeypatch.setattr(srv.threading, 'Thread', InlineThread)

    task = json.loads((data_dir / 'tasks_source.json').read_text(encoding='utf-8'))[0]
    srv.dispatch_for_state('TEST-DISPATCH-TARGETDEPT-1', task, 'Doing', trigger='unit-test')
    saved = json.loads((data_dir / 'tasks_source.json').read_text(encoding='utf-8'))[0]

    assert saved['_scheduler']['lastDispatchAgent'] == 'gongbu'
    assert saved['_scheduler']['lastDispatchTrigger'] == 'unit-test'
    assert saved['_scheduler']['lastDispatchStatus'] == 'gateway-offline'


def test_dispatch_for_state_queues_taizi_with_isolated_session_dispatch(tmp_path, monkeypatch):
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    (data_dir / 'tasks_source.json').write_text(json.dumps([{
        'id': 'TEST-TAIZI-AUTO-DISPATCH-1',
        'title': '太子隔离会话派发',
        'state': 'Taizi',
        'org': '太子',
        'updatedAt': '2026-04-17T00:00:00Z',
        '_scheduler': {
            'enabled': True,
            'stallThresholdSec': 180,
            'maxRetry': 1,
            'retryCount': 0,
            'escalationLevel': 0,
            'autoRollback': True,
            'lastProgressAt': '2026-04-17T00:00:00Z',
            'stallSince': None,
            'lastDispatchStatus': 'idle',
            'snapshot': {'state': 'Taizi', 'org': '太子', 'now': '待储君处理', 'savedAt': '2026-04-17T00:00:00Z', 'note': 'init'}
        },
    }], ensure_ascii=False), encoding='utf-8')

    import server as srv
    srv.DATA = data_dir
    srv._ACTIVE_TASK_DATA_DIR = None

    run_calls = []
    monkeypatch.setattr(srv.subprocess, 'run', lambda *args, **kwargs: run_calls.append((args, kwargs)))

    task = json.loads((data_dir / 'tasks_source.json').read_text(encoding='utf-8'))[0]
    srv.dispatch_for_state('TEST-TAIZI-AUTO-DISPATCH-1', task, 'Taizi', trigger='unit-test')
    saved = json.loads((data_dir / 'tasks_source.json').read_text(encoding='utf-8'))[0]

    assert not any(args and args[0] and args[0][0] == 'openclaw' for args, kwargs in run_calls)
    assert saved['_scheduler']['lastDispatchAgent'] == 'taizi'
    assert saved['_scheduler']['lastDispatchTrigger'] == 'unit-test'
    assert saved['_scheduler']['lastDispatchStatus'] == 'queued'


def test_wake_agent_uses_isolated_session_for_taizi(monkeypatch):
    import server as srv

    monkeypatch.setattr(srv, '_check_agent_workspace', lambda agent_id: True)
    monkeypatch.setattr(srv, '_check_gateway_alive', lambda: True)
    monkeypatch.setattr(srv, '_resolve_openclaw_bin', lambda: 'openclaw')

    class InlineThread:
        def __init__(self, target=None, daemon=None):
            self.target = target
            self.daemon = daemon
        def start(self):
            if self.target:
                self.target()

    class Completed:
        returncode = 0
        stdout = '{}'
        stderr = ''

    run_calls = []
    def fake_run(*args, **kwargs):
        run_calls.append((args, kwargs))
        return Completed()

    monkeypatch.setattr(srv.threading, 'Thread', InlineThread)
    monkeypatch.setattr(srv.subprocess, 'run', fake_run)

    result = srv.wake_agent('taizi', 'ping')

    assert result['ok'] is True
    assert '唤醒指令已发出' in result['message']
    assert run_calls
    cmd = run_calls[0][0][0]
    params = json.loads(cmd[cmd.index('--params') + 1])
    assert params['sessionKey'] == 'agent:taizi:edict-dispatch'
    assert params['agentId'] == 'taizi'


def test_dispatch_for_state_suppresses_menxia_repeat_review_dispatch(tmp_path, monkeypatch):
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    (data_dir / 'tasks_source.json').write_text(json.dumps([{
        'id': 'TEST-MENXIA-AUTO-DISPATCH-1',
        'title': '门下省重复送审保护',
        'state': 'Menxia',
        'org': '门下省',
        'now': '等待门下省审议',
        'block': '无',
        'updatedAt': '2026-04-17T00:00:00Z',
        'flow_log': [
            {'from': '中书省', 'to': '门下省', 'remark': '中书省方案提交门下省审议', 'at': '2026-04-17T00:00:00Z'},
            {'from': '门下省', 'to': '门下省', 'remark': '门下省已封驳：方案正文缺失，请补齐后再报', 'at': '2026-04-17T00:03:00Z'},
        ],
        'progress_log': [
            {'text': '结论：封驳；当前送审内容仍仅含任务ID与旨意，未附中书省方案正文'}
        ],
        '_scheduler': {
            'enabled': True,
            'stallThresholdSec': 180,
            'maxRetry': 1,
            'retryCount': 0,
            'escalationLevel': 0,
            'autoRollback': True,
            'lastProgressAt': '2026-04-17T00:03:00Z',
            'stallSince': None,
            'lastDispatchStatus': 'idle',
            'snapshot': {'state': 'Menxia', 'org': '门下省', 'now': '等待门下省审议', 'savedAt': '2026-04-17T00:00:00Z', 'note': 'init'}
        },
    }], ensure_ascii=False), encoding='utf-8')

    import server as srv
    srv.DATA = data_dir
    srv._ACTIVE_TASK_DATA_DIR = None

    run_calls = []
    monkeypatch.setattr(srv.subprocess, 'run', lambda *args, **kwargs: run_calls.append((args, kwargs)))

    task = json.loads((data_dir / 'tasks_source.json').read_text(encoding='utf-8'))[0]
    srv.dispatch_for_state('TEST-MENXIA-AUTO-DISPATCH-1', task, 'Menxia', trigger='unit-test')
    saved = json.loads((data_dir / 'tasks_source.json').read_text(encoding='utf-8'))[0]

    assert not any(args and args[0] and args[0][0] == 'openclaw' for args, kwargs in run_calls)
    assert saved['_scheduler']['lastDispatchAgent'] == 'menxia'
    assert saved['_scheduler']['lastDispatchTrigger'] == 'unit-test'
    assert saved['_scheduler']['lastDispatchStatus'] == 'suppressed-repeat-review-guard'
    assert '门下省重复送审保护' in saved['_scheduler']['lastDispatchError']


def test_scheduler_scan_skips_retry_for_menxia_task_with_existing_verdict(tmp_path, monkeypatch):
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    (data_dir / 'tasks_source.json').write_text(json.dumps([{
        'id': 'TEST-SCHED-MENXIA-RETRY-1',
        'title': '门下省已出结论不应重试',
        'state': 'Menxia',
        'org': '门下省',
        'now': '等待门下省审议',
        'updatedAt': '2026-04-17T00:00:00Z',
        'flow_log': [
            {'from': '中书省', 'to': '门下省', 'remark': '中书省方案提交门下省审议', 'at': '2026-04-17T00:00:00Z'},
            {'from': '门下省', 'to': '门下省', 'remark': '门下省已准奏：允许进入尚书省派发', 'at': '2026-04-17T00:04:00Z'},
        ],
        'progress_log': [
            {'text': '结论：准奏；允许转尚书省派发执行'}
        ],
        '_scheduler': {
            'enabled': True,
            'stallThresholdSec': 180,
            'maxRetry': 1,
            'retryCount': 0,
            'escalationLevel': 0,
            'autoRollback': True,
            'lastProgressAt': '2026-04-17T00:00:00Z',
            'stallSince': None,
            'lastDispatchStatus': 'idle',
            'snapshot': {'state': 'Menxia', 'org': '门下省', 'now': '等待门下省审议', 'savedAt': '2026-04-17T00:00:00Z', 'note': 'init'}
        },
    }], ensure_ascii=False), encoding='utf-8')
    (data_dir / 'tasks_governance_samples.json').write_text('[]', encoding='utf-8')

    import server as srv
    srv.DATA = data_dir
    srv._ACTIVE_TASK_DATA_DIR = None

    called = []
    old_dispatch = srv.dispatch_for_state
    try:
        srv.dispatch_for_state = lambda task_id, task, state, trigger='state-transition': called.append({
            'task_id': task_id,
            'state': state,
            'trigger': trigger,
        })
        result = srv.handle_scheduler_scan(180)
        saved = json.loads((data_dir / 'tasks_source.json').read_text(encoding='utf-8'))[0]
    finally:
        srv.dispatch_for_state = old_dispatch

    assert result['ok'] is True
    assert result['count'] == 0
    assert called == []
    assert saved['_scheduler']['retryCount'] == 0
    assert saved['_scheduler']['lastDispatchStatus'] == 'suppressed-repeat-review-guard'
    assert '门下省重复送审保护' in saved['_scheduler']['lastDispatchError']


def test_dispatch_for_state_suppresses_menxia_when_verdict_exists_only_in_governance_sample(tmp_path, monkeypatch):
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    (data_dir / 'tasks_source.json').write_text(json.dumps([{
        'id': 'TEST-MENXIA-SAMPLE-GUARD-1',
        'title': '样本层门下结论保护',
        'state': 'Menxia',
        'org': '门下省',
        'now': '等待门下省审议',
        'block': '无',
        'updatedAt': '2026-04-17T00:00:00Z',
        'flow_log': [
            {'from': '中书省', 'to': '门下省', 'remark': '中书省方案提交门下省审议', 'at': '2026-04-17T00:00:00Z'}
        ],
        'progress_log': [],
        '_scheduler': {
            'enabled': True,
            'stallThresholdSec': 180,
            'maxRetry': 1,
            'retryCount': 0,
            'escalationLevel': 0,
            'autoRollback': True,
            'lastProgressAt': '2026-04-17T00:03:00Z',
            'stallSince': None,
            'lastDispatchStatus': 'idle',
            'snapshot': {'state': 'Menxia', 'org': '门下省', 'now': '等待门下省审议', 'savedAt': '2026-04-17T00:00:00Z', 'note': 'init'}
        },
    }], ensure_ascii=False), encoding='utf-8')
    (data_dir / 'tasks_governance_samples.json').write_text(json.dumps([{
        'id': 'TEST-MENXIA-SAMPLE-GUARD-1',
        'task_id': 'TEST-MENXIA-SAMPLE-GUARD-1',
        'org': '门下省',
        'flow_log': [
            {'from': '门下省', 'to': '中书省', 'remark': '❌ 封驳：未附中书省方案正文，无法审议'}
        ],
        'progress_log': [
            {'text': '审议完成，封驳：要求补齐方案正文后再报'}
        ]
    }], ensure_ascii=False), encoding='utf-8')

    import server as srv
    srv.DATA = data_dir
    srv._ACTIVE_TASK_DATA_DIR = None

    run_calls = []
    monkeypatch.setattr(srv.subprocess, 'run', lambda *args, **kwargs: run_calls.append((args, kwargs)))

    task = json.loads((data_dir / 'tasks_source.json').read_text(encoding='utf-8'))[0]
    srv.dispatch_for_state('TEST-MENXIA-SAMPLE-GUARD-1', task, 'Menxia', trigger='unit-test')
    saved = json.loads((data_dir / 'tasks_source.json').read_text(encoding='utf-8'))[0]

    assert not any(args and args[0] and args[0][0] == 'openclaw' for args, kwargs in run_calls)
    assert saved['_scheduler']['lastDispatchStatus'] == 'suppressed-repeat-review-guard'
    assert '门下省重复送审保护' in saved['_scheduler']['lastDispatchError']
    assert saved['now'] == '门下省已封驳，等待中书省补正文后再报'
    assert '未附中书省方案正文' in saved['block']
    assert any('已跳过重复送审' in str(item.get('content', '')) for item in saved['progress_log'])


def test_handle_dispatch_task_explicitly_assigns_six_department_and_dispatches(tmp_path, monkeypatch):
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    (data_dir / 'tasks_source.json').write_text(json.dumps([{
        'id': 'TEST-MANUAL-DISPATCH-1',
        'title': '手动显式派部',
        'state': 'Assigned',
        'org': '尚书省',
        'now': '等待尚书省派发',
        'updatedAt': '2026-04-17T00:00:00Z',
        '_scheduler': {
            'enabled': True,
            'stallThresholdSec': 180,
            'maxRetry': 1,
            'retryCount': 0,
            'escalationLevel': 0,
            'autoRollback': True,
            'lastProgressAt': '2026-04-17T00:00:00Z',
            'stallSince': None,
            'lastDispatchStatus': 'idle',
            'snapshot': {'state': 'Assigned', 'org': '尚书省', 'now': '等待尚书省派发', 'savedAt': '2026-04-17T00:00:00Z', 'note': 'init'}
        },
    }], ensure_ascii=False), encoding='utf-8')

    import server as srv
    srv.DATA = data_dir
    srv._ACTIVE_TASK_DATA_DIR = None

    monkeypatch.setattr(srv, '_check_gateway_alive', lambda: False)

    class InlineThread:
        def __init__(self, target=None, daemon=None, args=(), kwargs=None):
            self.target = target
            self.args = args
            self.kwargs = kwargs or {}
        def start(self):
            if self.target:
                self.target(*self.args, **self.kwargs)

    monkeypatch.setattr(srv.threading, 'Thread', InlineThread)

    result = srv.handle_dispatch_task('TEST-MANUAL-DISPATCH-1', '工部', '改由工部执行')
    saved = json.loads((data_dir / 'tasks_source.json').read_text(encoding='utf-8'))[0]

    assert result['ok'] is True
    assert saved['state'] == 'Doing'
    assert saved['org'] == '工部'
    assert saved['targetDept'] == '工部'
    assert '改由工部执行' in saved['now']
    explicit_flow = next(item for item in saved['flow_log'] if item.get('from') == '尚书省' and item.get('to') == '工部' and '显式派发' in item.get('remark', ''))
    assert explicit_flow['from'] == '尚书省'
    assert explicit_flow['to'] == '工部'
    assert saved['_scheduler']['lastDispatchAgent'] == 'gongbu'
    assert saved['_scheduler']['lastDispatchTrigger'] == 'manual-dispatch'
    assert saved['_scheduler']['lastDispatchStatus'] == 'gateway-offline'


def test_handle_dispatch_task_rejects_non_dispatchable_state(tmp_path):
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    (data_dir / 'tasks_source.json').write_text(json.dumps([{
        'id': 'TEST-MANUAL-DISPATCH-REJECT',
        'title': '审查态不可派部',
        'state': 'Review',
        'org': '尚书省',
    }], ensure_ascii=False), encoding='utf-8')

    import server as srv
    srv.DATA = data_dir
    srv._ACTIVE_TASK_DATA_DIR = None

    result = srv.handle_dispatch_task('TEST-MANUAL-DISPATCH-REJECT', '工部', '')
    assert result['ok'] is False
    assert '不可显式派部' in result['error']


def test_handle_dispatch_task_dual_mode_uses_backend_without_local_json(monkeypatch):
    import server as srv

    monkeypatch.setattr(srv, 'TASK_WRITE_MODE', 'dual', raising=False)
    monkeypatch.setattr(
        srv,
        '_dispatch_task_via_backend',
        lambda task_id, target_dept, comment='': {
            'ok': True,
            'message': 'backend dispatch ok',
            'state': 'Doing',
            'org': '工部',
            'targetDept': '工部',
        },
        raising=False,
    )
    save_calls = []
    monkeypatch.setattr(srv, 'save_tasks', lambda tasks: save_calls.append(tasks))
    monkeypatch.setattr(srv, 'load_tasks', lambda: [{'id': 'TEST-MANUAL-DISPATCH-1', 'state': 'Assigned', 'org': '尚书省'}])

    result = srv.handle_dispatch_task('TEST-MANUAL-DISPATCH-1', '工部', '改由工部执行')

    assert result['ok'] is True
    assert result['message'] == 'backend dispatch ok'
    assert save_calls == []


def test_handle_dispatch_task_dual_mode_falls_back_to_legacy_when_backend_fails(tmp_path, monkeypatch):
    import server as srv

    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    (data_dir / 'tasks_source.json').write_text(json.dumps([{'id': 'TEST-MANUAL-DISPATCH-2', 'state': 'Assigned', 'org': '尚书省'}], ensure_ascii=False), encoding='utf-8')
    srv.DATA = data_dir
    srv._ACTIVE_TASK_DATA_DIR = None

    monkeypatch.setattr(srv, 'TASK_WRITE_MODE', 'dual', raising=False)
    monkeypatch.setattr(
        srv,
        '_dispatch_task_via_backend',
        lambda task_id, target_dept, comment='': {'ok': False, 'error': 'backend unavailable'},
        raising=False,
    )

    dispatched = []
    monkeypatch.setattr(
        srv,
        'dispatch_for_state',
        lambda task_id, task, state, trigger='state-transition': dispatched.append({
            'task_id': task_id,
            'state': state,
            'trigger': trigger,
            'task': task,
        }),
    )
    result = srv.handle_dispatch_task('TEST-MANUAL-DISPATCH-2', '工部', '改由工部执行')
    saved_tasks = json.loads((data_dir / 'tasks_source.json').read_text(encoding='utf-8'))

    assert result['ok'] is True
    assert saved_tasks[0]['state'] == 'Doing'
    assert saved_tasks[0]['targetDept'] == '工部'
    assert dispatched and dispatched[0]['task_id'] == 'TEST-MANUAL-DISPATCH-2'
    assert dispatched[0]['trigger'] == 'manual-dispatch'


def test_handle_review_action_dual_mode_uses_backend_without_local_json(monkeypatch):
    import server as srv

    monkeypatch.setattr(srv, 'TASK_WRITE_MODE', 'dual', raising=False)
    monkeypatch.setattr(
        srv,
        '_review_action_via_backend',
        lambda task_id, action, comment='': {
            'ok': True,
            'message': 'backend review ok',
            'state': 'Done',
            'review_round': 0,
        },
        raising=False,
    )
    save_calls = []
    monkeypatch.setattr(srv, 'save_tasks', lambda tasks: save_calls.append(tasks))
    monkeypatch.setattr(srv, 'load_tasks', lambda: [{'id': 'TEST-REVIEW-DUAL-1', 'state': 'PendingConfirm', 'org': '尚书省'}])

    result = srv.handle_review_action('TEST-REVIEW-DUAL-1', 'approve', '准奏')

    assert result['ok'] is True
    assert result['message'] == 'backend review ok'
    assert save_calls == []



def test_handle_review_action_dual_mode_falls_back_to_legacy_when_backend_fails(tmp_path, monkeypatch):
    import server as srv

    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    srv.DATA = data_dir
    srv._ACTIVE_TASK_DATA_DIR = None

    monkeypatch.setattr(srv, 'TASK_WRITE_MODE', 'dual', raising=False)
    monkeypatch.setattr(
        srv,
        '_review_action_via_backend',
        lambda task_id, action, comment='': {'ok': False, 'error': 'backend unavailable'},
        raising=False,
    )

    (data_dir / 'tasks_source.json').write_text(json.dumps([{
        'id': 'TEST-REVIEW-DUAL-2',
        'state': 'PendingConfirm',
        'title': '待回退审批',
        'org': '尚书省',
        'now': '待确认',
        'pending_confirm': {
            'target_state': 'Done',
            'requested_by': 'shangshu',
            'requested_at': '2026-04-17T00:00:00Z',
            'confirm_by': 'menxia',
            'risk_key': 'Review->Done',
            'status': 'pending',
        },
        'gate_checks': [{
            'at': '2026-04-17T00:00:00Z',
            'gate': 'high_risk_transition',
            'from': 'Review',
            'to': 'Done',
            'confirm_by': 'menxia',
            'risk_key': 'Review->Done',
            'result': 'pending',
        }],
        'flow_log': [],
        'updatedAt': '2026-04-17T00:00:00Z',
    }], ensure_ascii=False), encoding='utf-8')

    result = srv.handle_review_action('TEST-REVIEW-DUAL-2', 'approve', '准奏')
    saved_tasks = json.loads((data_dir / 'tasks_source.json').read_text(encoding='utf-8'))

    assert result['ok'] is True
    assert saved_tasks[0]['state'] == 'Done'
    assert saved_tasks[0]['gate_checks'][-1]['result'] == 'approved'


def test_timeout_summary_route_groups_stalled_tasks(tmp_path):
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    (data_dir / 'tasks_source.json').write_text(json.dumps([
        {
            'id': 'TEST-TIMEOUT-1',
            'title': '超时分类任务',
            'state': 'Doing',
            'org': '工部',
            'updatedAt': '2026-04-17T00:00:00Z',
            '_scheduler': {
                'stallThresholdSec': 180,
                'lastProgressAt': '2026-04-17T00:00:00Z',
                'retryCount': 1,
                'lastDispatchStatus': 'dispatch timeout'
            }
        },
        {
            'id': 'TEST-HEALTHY-1',
            'title': '正常任务',
            'state': 'Doing',
            'org': '礼部',
            'updatedAt': '2099-01-01T00:00:00Z',
            '_scheduler': {
                'stallThresholdSec': 999999,
                'lastProgressAt': '2099-01-01T00:00:00Z'
            }
        }
    ], ensure_ascii=False), encoding='utf-8')

    import server as srv
    srv.DATA = data_dir
    srv._ACTIVE_TASK_DATA_DIR = None

    from http.server import HTTPServer
    port = 18974
    httpd = HTTPServer(('127.0.0.1', port), srv.Handler)
    t = threading.Thread(target=httpd.handle_request, daemon=True)
    t.start()
    time.sleep(0.1)

    conn = HTTPConnection('127.0.0.1', port, timeout=5)
    conn.request('GET', '/api/timeout-summary?limit=2')
    resp = conn.getresponse()
    body = json.loads(resp.read())
    conn.close()

    assert resp.status == 200
    assert body['ok'] is True
    assert body['totals']['interestingTasks'] == 1
    assert body['categories'][0]['reason'] == 'dispatch_timeout'
    assert body['tasks'][0]['taskId'] == 'TEST-TIMEOUT-1'

    httpd.server_close()


def test_jidipu_panel_route_aggregates_dispatch_notification_and_approval(tmp_path):
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    (data_dir / 'tasks_source.json').write_text(json.dumps([{
        'id': 'TEST-JIDIPU-1',
        'title': '急递铺样本',
        'state': 'PendingConfirm',
        'org': '工部',
        'official': 'gongbu',
        'updatedAt': '2026-04-20T08:00:00Z',
        'flow_log': [
            {'at': '2026-04-20T07:00:00Z', 'from': '中书省', 'to': '门下省', 'remark': '派发审议'},
            {'at': '2026-04-20T07:30:00Z', 'from': '尚书省', 'to': '工部', 'remark': '停滞重试：重新派发'},
        ],
        'notifications': {
            'pending_confirm_sent_at': '2026-04-20T07:40:00Z',
            'pending_confirm_sent': True,
            'review_result_sent_at': '2026-04-20T07:50:00Z',
            'review_result_sent': 'approved',
        },
        'gate_checks': [{
            'requested_at': '2026-04-20T07:35:00Z',
            'result': 'approved',
            'risk_key': 'Review->Done',
            'from': 'Review',
            'to': 'Done',
        }],
        '_scheduler': {
            'lastDispatchAgent': 'gongbu',
        },
    }], ensure_ascii=False), encoding='utf-8')

    import server as srv
    srv.DATA = data_dir
    srv._ACTIVE_TASK_DATA_DIR = None

    from http.server import HTTPServer
    port = 18976
    httpd = HTTPServer(('127.0.0.1', port), srv.Handler)
    t = threading.Thread(target=httpd.handle_request, daemon=True)
    t.start()
    time.sleep(0.1)

    conn = HTTPConnection('127.0.0.1', port, timeout=5)
    conn.request('GET', '/api/jidipu-panel?limit=10')
    resp = conn.getresponse()
    body = json.loads(resp.read())
    conn.close()

    assert resp.status == 200
    assert body['ok'] is True
    assert body['stats']['notifications'] >= 2
    assert body['stats']['dispatches'] >= 1
    assert body['stats']['retries'] >= 1
    assert body['stats']['approvals'] >= 1
    assert body['items'][0]['taskId'] == 'TEST-JIDIPU-1'

    httpd.server_close()


def test_guoshiguan_panel_route_aggregates_task_memory_autopsy_and_rules(tmp_path):
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    task_memory_dir = data_dir / 'task_memory'
    task_memory_dir.mkdir()
    task_memory_dir.joinpath('TASK-GUOSHI-1.json').write_text(json.dumps({
        'title': '支付链路修复',
        'summary': '修复 provider timeout 并沉淀排查经验',
        'agent_id': 'gongbu',
        'tags': ['payment', 'provider_timeout'],
        'updated_at': '2026-04-19T03:00:00Z',
        'context_chain': [{
            'summary': '先排查 provider timeout，再补重试机制',
            'key_decisions': ['增加 provider timeout 重试', '补充监控'],
            'warnings': ['避免无上限重试'],
            'agent_id': 'gongbu',
            'at': '2026-04-19T03:00:00Z',
        }]
    }, ensure_ascii=False), encoding='utf-8')
    autopsy_dir = data_dir / 'autopsy'
    autopsy_dir.mkdir()
    report = autopsy_dir / 'TASK-GUOSHI-2.md'
    report.write_text('# autopsy\nprovider_timeout\n', encoding='utf-8')
    (data_dir / 'shared_memory.json').write_text(json.dumps({
        'rules': [{
            'content': '高风险状态切换必须显式确认后执行',
            'scope': 'global',
            'at': '2026-04-19T05:00:00Z',
            'added_by': 'court_discuss',
            'reason': '避免直接跳过审批门禁',
        }]
    }, ensure_ascii=False), encoding='utf-8')
    (data_dir / 'tasks_source.json').write_text(json.dumps([{
        'id': 'TASK-GUOSHI-2',
        'title': '超时验尸样本',
        'state': 'Blocked',
        'org': '兵部',
        'block': 'provider_timeout',
        'autopsy': {
            'path': str(report),
            'reason': 'provider_timeout',
            'label': '模型超时',
            'generatedAt': '2026-04-19T04:00:00Z',
        },
        'memory_extracted': {
            'autopsy': {'agent': 'bingbu'}
        },
        'updatedAt': '2026-04-19T04:00:00Z',
    }], ensure_ascii=False), encoding='utf-8')

    import server as srv
    srv.DATA = data_dir
    srv._ACTIVE_TASK_DATA_DIR = None

    from http.server import HTTPServer
    port = 18976
    httpd = HTTPServer(('127.0.0.1', port), srv.Handler)
    t = threading.Thread(target=httpd.handle_request, daemon=True)
    t.start()
    time.sleep(0.1)

    conn = HTTPConnection('127.0.0.1', port, timeout=5)
    conn.request('GET', '/api/guoshiguan-panel?limit=10&q=provider_timeout')
    resp = conn.getresponse()
    body = json.loads(resp.read())
    conn.close()

    assert resp.status == 200
    assert body['ok'] is True
    assert body['stats']['taskMemory'] == 1
    assert body['stats']['autopsy'] == 1
    assert body['stats']['sharedRules'] == 0
    assert {item['sourceType'] for item in body['items']} == {'task_memory', 'autopsy'}
    assert any('provider timeout' in item['excerpt'].lower() or 'provider_timeout' in item['excerpt'].lower() for item in body['items'])

    httpd.server_close()


def test_guoshiguan_panel_route_matches_shared_rules_and_unfiltered_totals(tmp_path):
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    task_memory_dir = data_dir / 'task_memory'
    task_memory_dir.mkdir()
    task_memory_dir.joinpath('TASK-GUOSHI-3.json').write_text(json.dumps({
        'title': '审批门禁补强',
        'summary': '给高风险状态迁移补人工确认',
        'agent_id': 'menxia',
        'updated_at': '2026-04-20T01:00:00Z',
        'context_chain': [{
            'summary': '审批门禁规则沉淀',
            'key_decisions': ['高风险流转必须人工确认'],
            'warnings': ['不要绕过 PendingConfirm'],
            'agent_id': 'menxia',
            'at': '2026-04-20T01:00:00Z',
        }]
    }, ensure_ascii=False), encoding='utf-8')
    autopsy_dir = data_dir / 'autopsy'
    autopsy_dir.mkdir()
    report = autopsy_dir / 'TASK-GUOSHI-4.md'
    report.write_text('# autopsy\nnetwork flap\n', encoding='utf-8')
    (data_dir / 'shared_memory.json').write_text(json.dumps({
        'rules': [{
            'content': '高风险状态切换必须显式确认后执行',
            'scope': 'global',
            'at': '2026-04-20T02:00:00Z',
            'added_by': 'court_discuss',
            'reason': '避免直接跳过审批门禁',
        }]
    }, ensure_ascii=False), encoding='utf-8')
    (data_dir / 'tasks_source.json').write_text(json.dumps([{
        'id': 'TASK-GUOSHI-4',
        'title': '网络抖动验尸',
        'state': 'Blocked',
        'org': '工部',
        'block': 'network flap',
        'autopsy': {
            'path': str(report),
            'reason': 'network_flap',
            'label': '网络抖动',
            'generatedAt': '2026-04-20T02:30:00Z',
        },
        'memory_extracted': {
            'autopsy': {'agent': 'gongbu'}
        },
        'updatedAt': '2026-04-20T02:30:00Z',
    }], ensure_ascii=False), encoding='utf-8')

    import server as srv
    srv.DATA = data_dir
    srv._ACTIVE_TASK_DATA_DIR = None

    from http.server import HTTPServer
    port = 18978
    httpd = HTTPServer(('127.0.0.1', port), srv.Handler)
    t1 = threading.Thread(target=httpd.handle_request, daemon=True)
    t1.start()
    time.sleep(0.1)

    conn = HTTPConnection('127.0.0.1', port, timeout=5)
    conn.request('GET', '/api/guoshiguan-panel?limit=10')
    resp = conn.getresponse()
    body = json.loads(resp.read())
    conn.close()

    assert resp.status == 200
    assert body['ok'] is True
    assert body['stats']['taskMemory'] == 1
    assert body['stats']['autopsy'] == 1
    assert body['stats']['sharedRules'] == 1
    assert body['stats']['total'] == 3
    assert {item['sourceType'] for item in body['items']} == {'task_memory', 'autopsy', 'shared_rule'}

    t2 = threading.Thread(target=httpd.handle_request, daemon=True)
    t2.start()
    time.sleep(0.1)

    conn = HTTPConnection('127.0.0.1', port, timeout=5)
    conn.request('GET', '/api/guoshiguan-panel?limit=10&q=%E5%AE%A1%E6%89%B9%E9%97%A8%E7%A6%81')
    resp = conn.getresponse()
    filtered = json.loads(resp.read())
    conn.close()

    assert resp.status == 200
    assert filtered['ok'] is True
    assert filtered['stats']['sharedRules'] == 1
    assert filtered['stats']['taskMemory'] == 1
    assert filtered['stats']['autopsy'] == 0
    assert {item['sourceType'] for item in filtered['items']} == {'task_memory', 'shared_rule'}

    httpd.server_close()


def test_court_conclude_returns_structured_fallback(monkeypatch):
    import court_discuss as cd
    monkeypatch.setattr(cd, '_llm_complete', lambda *args, **kwargs: None)
    created = cd.create_session('测试议政结论结构化', ['gongbu', 'xingbu'], 'TASK-COURT-1')
    sid = created['session_id']
    cd.advance_discussion(sid)
    result = cd.conclude_session(sid)
    assert result['ok'] is True
    assert result['conclusion']['actions']
    fetched = cd.get_session(sid)
    assert fetched['conclusion']['actions'][0]['type'] == 'todo'


def test_court_discussion_supports_all_11_officials():
    import court_discuss as cd

    official_ids = [
        'taizi', 'zhongshu', 'menxia', 'shangshu', 'libu', 'hubu',
        'bingbu', 'xingbu', 'gongbu', 'libu_hr', 'zaochao'
    ]

    created = cd.create_session('测试 11 位官员同时参朝', official_ids, 'TASK-COURT-ALL')

    assert created['ok'] is True
    assert len(created['officials']) == 11
    assert {o['id'] for o in created['officials']} == set(official_ids)


def test_handle_create_task_dual_mode_uses_backend_without_local_json(monkeypatch):
    import server as srv

    monkeypatch.setattr(srv, 'TASK_WRITE_MODE', 'dual', raising=False)
    monkeypatch.setattr(srv, 'load_tasks', lambda: [])

    backend_calls = []
    monkeypatch.setattr(
        srv,
        '_create_task_via_backend',
        lambda **kwargs: backend_calls.append(kwargs) or {
            'ok': True,
            'taskId': kwargs['legacy_id'],
            'backendTaskId': 'uuid-backend-1',
            'message': 'backend created',
        },
        raising=False,
    )

    save_calls = []
    dispatch_calls = []
    monkeypatch.setattr(srv, 'save_tasks', lambda tasks: save_calls.append(tasks))
    monkeypatch.setattr(srv, 'dispatch_for_state', lambda *args, **kwargs: dispatch_calls.append((args, kwargs)))

    result = srv.handle_create_task(
        '这是一个足够长的 backend 创建测试标题',
        priority='high',
        template_id='tpl-001',
        params={'city': '北京'},
        target_dept='工部',
    )

    assert result['ok'] is True
    assert result['taskId'].startswith('JJC-')
    assert result['backendTaskId'] == 'uuid-backend-1'
    assert backend_calls[0]['legacy_id'] == result['taskId']
    assert backend_calls[0]['template_id'] == 'tpl-001'
    assert backend_calls[0]['target_dept'] == '工部'
    assert save_calls == []
    assert dispatch_calls == []



def test_next_legacy_task_id_prefers_candidate_when_unused():
    import server as srv

    tasks = [
        {'id': 'JJC-20260430-001'},
        {'id': 'JJC-20260430-002'},
    ]

    assert srv._next_legacy_task_id(tasks, '20260430', preferred='JJC-20260430-003') == 'JJC-20260430-003'


def test_next_legacy_task_id_skips_used_preferred_and_advances():
    import server as srv

    tasks = [
        {'id': 'JJC-20260430-001'},
        {'id': 'JJC-20260430-002'},
        {'id': 'JJC-20260430-003'},
    ]

    assert srv._next_legacy_task_id(tasks, '20260430', preferred='JJC-20260430-003') == 'JJC-20260430-004'


def test_handle_create_task_dual_mode_uses_real_daily_legacy_id_instead_of_pending(monkeypatch):
    import server as srv

    monkeypatch.setattr(srv, 'TASK_WRITE_MODE', 'dual', raising=False)
    monkeypatch.setattr(srv, 'load_tasks', lambda: [{'id': 'JJC-20260430-001'}, {'id': 'JJC-20260430-002'}])

    real_datetime = srv.datetime.datetime

    class _FakeNow:
        @staticmethod
        def now():
            return real_datetime(2026, 4, 30, 9, 0, 0)

    monkeypatch.setattr(srv.datetime, 'datetime', _FakeNow, raising=False)

    backend_calls = []
    monkeypatch.setattr(
        srv,
        '_create_task_via_backend',
        lambda **kwargs: backend_calls.append(kwargs) or {
            'ok': True,
            'taskId': kwargs['legacy_id'],
            'legacyId': kwargs['legacy_id'],
            'backendTaskId': 'uuid-backend-2',
            'message': 'backend created',
        },
        raising=False,
    )
    monkeypatch.setattr(srv, 'dispatch_for_state', lambda *args, **kwargs: None)

    result = srv.handle_create_task('这是一个足够长的 backend 日流水测试标题')

    assert result['ok'] is True
    assert result['taskId'] == 'JJC-20260430-003'
    assert result['legacyId'] == 'JJC-20260430-003'
    assert backend_calls[0]['legacy_id'] == 'JJC-20260430-003'
    assert 'PENDING' not in backend_calls[0]['legacy_id']


def test_handle_create_task_dual_mode_falls_back_to_legacy_when_backend_fails(tmp_path, monkeypatch):
    import server as srv

    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    (data_dir / 'tasks_source.json').write_text('[]', encoding='utf-8')
    srv.DATA = data_dir
    srv._ACTIVE_TASK_DATA_DIR = None

    monkeypatch.setattr(srv, 'TASK_WRITE_MODE', 'dual', raising=False)
    monkeypatch.setattr(
        srv,
        '_create_task_via_backend',
        lambda **kwargs: {'ok': False, 'error': 'backend unavailable'},
        raising=False,
    )

    dispatched = []
    monkeypatch.setattr(
        srv,
        'dispatch_for_state',
        lambda task_id, task, state, trigger='imperial-edict': dispatched.append({
            'task_id': task_id,
            'state': state,
            'trigger': trigger,
            'task': task,
        }),
    )

    result = srv.handle_create_task('这是一个足够长的 fallback 测试标题', target_dept='工部')

    assert result['ok'] is True
    assert result['taskId'].startswith('JJC-')
    saved_tasks = json.loads((data_dir / 'tasks_source.json').read_text(encoding='utf-8'))
    assert saved_tasks[0]['id'] == result['taskId']
    assert saved_tasks[0]['targetDept'] == '工部'
    assert dispatched and dispatched[0]['task_id'] == result['taskId']
    assert dispatched[0]['state'] == 'Taizi'


def test_update_task_todos_dual_mode_uses_backend_without_local_json(monkeypatch):
    import server as srv

    monkeypatch.setattr(srv, 'TASK_WRITE_MODE', 'dual', raising=False)
    monkeypatch.setattr(srv, '_update_task_todos_via_backend', lambda task_id, todos: {'ok': True, 'message': 'backend todos ok'}, raising=False)

    save_calls = []
    monkeypatch.setattr(srv, 'save_tasks', lambda tasks: save_calls.append(tasks))
    monkeypatch.setattr(srv, 'load_tasks', lambda: [{'id': 'JJC-TODO-001', 'todos': []}])

    result = srv.update_task_todos('JJC-TODO-001', [{'id': '1', 'title': '补测试', 'status': 'completed'}])

    assert result['ok'] is True
    assert result['message'] == 'backend todos ok'
    assert save_calls == []


def test_update_task_todos_dual_mode_falls_back_to_legacy_when_backend_fails(tmp_path, monkeypatch):
    import server as srv

    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    (data_dir / 'tasks_source.json').write_text(json.dumps([{'id': 'JJC-TODO-001', 'todos': []}], ensure_ascii=False), encoding='utf-8')
    srv.DATA = data_dir
    srv._ACTIVE_TASK_DATA_DIR = None

    monkeypatch.setattr(srv, 'TASK_WRITE_MODE', 'dual', raising=False)
    monkeypatch.setattr(srv, '_update_task_todos_via_backend', lambda task_id, todos: {'ok': False, 'error': 'backend unavailable'}, raising=False)

    result = srv.update_task_todos('JJC-TODO-001', [{'id': '1', 'title': '补测试', 'status': 'completed'}])
    saved_tasks = json.loads((data_dir / 'tasks_source.json').read_text(encoding='utf-8'))

    assert result['ok'] is True
    assert saved_tasks[0]['todos'][0]['id'] == '1'
    assert saved_tasks[0]['todos'][0]['status'] == 'completed'


def test_adopt_court_conclusion_writes_todo_and_rule(tmp_path, monkeypatch):
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    (data_dir / 'tasks_source.json').write_text(json.dumps([{
        'id': 'TASK-COURT-ADOPT', 'title': '采纳议政结论测试', 'state': 'Doing', 'todos': []
    }], ensure_ascii=False), encoding='utf-8')

    import court_discuss as cd
    import server as srv
    srv.DATA = data_dir
    srv._ACTIVE_TASK_DATA_DIR = None
    monkeypatch.setattr(srv, 'save_tasks', lambda tasks: srv.atomic_json_write(data_dir / 'tasks_source.json', tasks))

    created = cd.create_session('议政采纳测试', ['gongbu', 'xingbu'], 'TASK-COURT-ADOPT')
    sid = created['session_id']
    raw = cd._sessions[sid]
    raw['phase'] = 'concluded'
    raw['summary'] = '形成一条 todo 和一条 rule'
    raw['conclusion'] = {
        'decision': '采纳', 'consensus': [], 'controversies': [], 'next_steps': [],
        'actions': [
            {'type': 'todo', 'title': '补齐采纳测试', 'content': '把结论转 todo', 'owner': 'gongbu'},
            {'type': 'rule', 'title': '议政结论须入账', 'content': '议政结论必须显式采纳后入台账', 'scope': 'global'},
        ]
    }

    result = srv.adopt_court_conclusion(sid)
    assert result['ok'] is True
    assert result['counts']['todos'] == 1
    assert result['counts']['rules'] == 1

    tasks = json.loads((data_dir / 'tasks_source.json').read_text(encoding='utf-8'))
    assert tasks[0]['todos'][0]['source'] == 'court_discuss'
    shared = json.loads((data_dir / 'shared_memory.json').read_text(encoding='utf-8'))
    assert shared['rules'][0]['content'] == '议政结论必须显式采纳后入台账'

    again = srv.adopt_court_conclusion(sid)
    assert again['counts']['todos'] == 0
    assert again['counts']['rules'] == 0
    assert again['counts']['skipped'] >= 2


def test_adopt_court_conclusion_creates_court_task_via_modify_tasks(tmp_path, monkeypatch):
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    (data_dir / 'tasks_source.json').write_text(json.dumps([], ensure_ascii=False), encoding='utf-8')

    import court_discuss as cd
    import server as srv
    srv.DATA = data_dir
    srv._ACTIVE_TASK_DATA_DIR = None

    called = {'count': 0}
    real_modify_tasks = srv.modify_tasks

    def wrapped(updater):
        called['count'] += 1
        return real_modify_tasks(updater)

    monkeypatch.setattr(srv, 'modify_tasks', wrapped)

    created = cd.create_session('议政采纳建任务', ['gongbu'], '')
    sid = created['session_id']
    raw = cd._sessions[sid]
    raw['phase'] = 'concluded'
    raw['summary'] = '形成一条 task'
    raw['conclusion'] = {
        'decision': '采纳', 'consensus': [], 'controversies': [], 'next_steps': [],
        'actions': [
            {'type': 'task', 'title': '生成 COURT 任务', 'content': '从议政结论创建任务', 'owner': '工部'},
        ]
    }

    result = srv.adopt_court_conclusion(sid)
    assert result['ok'] is True
    assert result['counts']['tasks'] == 1
    assert called['count'] == 1

    tasks = json.loads((data_dir / 'tasks_source.json').read_text(encoding='utf-8'))
    assert tasks[0]['id'].startswith(f'COURT-{sid}-0')
    assert tasks[0]['source'] == 'court_discuss'


def test_startup_recover_queued_dispatches_repairs_then_dispatches(tmp_path, monkeypatch):
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    task = {
        'id': 'JJC-RECOVER-001',
        'title': '启动恢复测试',
        'state': 'Doing',
        'org': '工部',
        '_scheduler': {
            'lastDispatchStatus': 'queued',
            'lastDispatchAgent': 'gongbu',
        }
    }
    (data_dir / 'tasks_source.json').write_text(json.dumps([task], ensure_ascii=False), encoding='utf-8')

    import server as srv
    srv.DATA = data_dir
    srv._ACTIVE_TASK_DATA_DIR = None

    dispatched = []
    monkeypatch.setattr(srv, 'dispatch_for_state', lambda task_id, task, state, trigger='state-transition': dispatched.append({
        'task_id': task_id,
        'state': state,
        'trigger': trigger,
        'snapshot_status': ((task.get('_scheduler') or {}).get('lastDispatchStatus')),
    }))

    srv._startup_recover_queued_dispatches()

    tasks = json.loads((data_dir / 'tasks_source.json').read_text(encoding='utf-8'))
    sched = tasks[0]['_scheduler']
    assert sched['lastDispatchStatus'] == 'queued'
    assert sched['lastDispatchTrigger'] == 'startup-recovery'
    assert len(dispatched) == 1
    assert dispatched[0]['task_id'] == 'JJC-RECOVER-001'
    assert dispatched[0]['trigger'] == 'startup-recovery'
    assert dispatched[0]['snapshot_status'] == 'queued'


def test_startup_recover_queued_dispatches_keeps_shangshu_queued_without_redispatch(tmp_path, monkeypatch):
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    task = {
        'id': 'JJC-RECOVER-002',
        'title': '启动恢复尚书队列保持测试',
        'state': 'Assigned',
        'org': '尚书省',
        '_scheduler': {
            'lastDispatchStatus': 'queued',
            'lastDispatchAgent': 'shangshu',
        }
    }


def test_get_observability_panel_summarizes_search_logs_cron_session_token(tmp_path, monkeypatch):
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    (data_dir / 'tasks_source.json').write_text(json.dumps([
        {
            'id': 'OBS-SEARCH-1',
            'title': '搜索和日志观测任务',
            'state': 'Doing',
            'org': '太子',
            'now': '正在排查 token 兼容路径',
            'updatedAt': '2026-05-11T02:00:00Z',
            'sourceMeta': {'sessionKey': 'agent:taizi:edict-dispatch'},
            '_scheduler': {
                'enabled': True,
                'retryCount': 2,
                'lastDispatchStatus': 'rate-limited',
                'lastDispatchError': '429 upstream key expired',
                'lastDispatchAt': '2026-05-11T02:01:00Z',
            },
            'progress_log': [
                {'at': '2026-05-11T02:02:00Z', 'tokens': 321, 'cost': 0.12, 'elapsed': 9, 'msg': 'token usage sample'},
            ],
            'flow_log': [
                {'at': '2026-05-11T02:03:00Z', 'from': '太子', 'to': '中书省', 'remark': '搜索日志定位 key 过期'},
            ],
            'activity': [
                {'at': '2026-05-11T02:04:00Z', 'kind': 'assistant', 'text': '兼容路径 /v1/chat/completions 失败'},
            ],
        },
        {
            'id': 'OBS-DONE-1',
            'title': '已完成样本',
            'state': 'Done',
            'org': '工部',
            'updatedAt': '2026-05-10T02:00:00Z',
            'progress_log': [{'tokens': 100, 'cost': 0.03}],
        },
    ], ensure_ascii=False), encoding='utf-8')
    (data_dir / 'model_change_log.json').write_text(json.dumps([
        {'at': '2026-05-11T02:05:00Z', 'agentId': 'taizi', 'model': 'gpt-5.4', 'result': 'ok'}
    ], ensure_ascii=False), encoding='utf-8')
    (data_dir / 'last_model_change_result.json').write_text(json.dumps({
        'ok': False,
        'error': 'compat route token expired',
        'checkedAt': '2026-05-11T02:06:00Z',
    }, ensure_ascii=False), encoding='utf-8')
    (data_dir / 'live_status.json').write_text(json.dumps({
        'activeTasks': {'OBS-SEARCH-1': {'state': 'Doing'}},
        'completedTasks': {'OBS-DONE-1': {'state': 'Done'}},
        'taskSource': 'backend_api_export',
        'taskSourceMeta': {'count': 2},
    }, ensure_ascii=False), encoding='utf-8')
    (data_dir / 'tasks_governance_samples.json').write_text(json.dumps([
        {
            'id': 'GOV-SAMPLE-1',
            'title': '治理样本 token 复盘',
            'state': 'Review',
            'org': '门下省',
            'updatedAt': '2026-05-11T02:09:00Z',
            'now': 'token governance sample',
            'autopsy': {'reason': 'token cost spike'},
        }
    ], ensure_ascii=False), encoding='utf-8')

    import server as srv
    srv.DATA = data_dir
    srv._ACTIVE_TASK_DATA_DIR = None

    def fake_backend_request(method, path, payload=None):
        assert method == 'GET'
        if path.startswith('/api/tasks?'):
            return {'tasks': [
                {'id': 'backend-1', 'state': 'Doing'},
                {'id': 'backend-2', 'state': 'Done'},
            ], 'count': 2}
        raise AssertionError(path)

    monkeypatch.setattr(srv, '_backend_json_request', fake_backend_request)

    oc_home = tmp_path / '.openclaw'
    agent_sessions = oc_home / 'agents' / 'taizi' / 'sessions'
    agent_sessions.mkdir(parents=True)
    session_file = agent_sessions / 'session-1.jsonl'
    session_file.write_text(
        json.dumps({'type': 'user', 'timestamp': '2026-05-11T02:07:00Z', 'text': '查最近 proxy log'}, ensure_ascii=False) + '\n' +
        json.dumps({'type': 'assistant', 'timestamp': '2026-05-11T02:08:00Z', 'text': '发现 token expired'}, ensure_ascii=False) + '\n',
        encoding='utf-8'
    )
    (agent_sessions / 'sessions.json').write_text(json.dumps({
        'items': [
            {
                'id': 'session-1',
                'sessionKey': 'agent:taizi:edict-dispatch',
                'updatedAt': 1778465280000,
                'title': 'edict dispatch',
                'file': str(session_file),
            }
        ]
    }, ensure_ascii=False), encoding='utf-8')
    (oc_home / 'openclaw.json').write_text(json.dumps({
        'gateway': {'auth': {'token': 'real-secret-token'}},
        'agents': {'taizi': {'model': 'gpt-5.4'}},
    }, ensure_ascii=False), encoding='utf-8')
    monkeypatch.setattr(srv, 'OCLAW_HOME', oc_home)

    body = srv.get_observability_panel(query='token', limit=5)

    assert body['ok'] is True
    assert body['query'] == 'token'
    assert body['stats']['matchingTasks'] == 1
    assert body['stats']['activeTasks'] == 1
    assert body['stats']['tokenEvents'] >= 2
    assert body['stats']['cronItems'] >= 1
    assert body['search']['items'][0]['taskId'] == 'OBS-SEARCH-1'
    assert 'token' in body['search']['items'][0]['matchedText'].lower()
    assert body['logs']['items']
    assert any('token' in item['summary'].lower() or 'key' in item['summary'].lower() for item in body['logs']['items'])
    assert body['cron']['items'][0]['taskId'] == 'OBS-SEARCH-1'
    assert body['sessions']['items'][0]['agentId'] == 'taizi'
    assert body['tokens']['summary']['totalTokens'] == 421
    assert body['tokens']['summary']['totalCostUsd'] == 0.15
    assert 'real-secret-token' not in json.dumps(body, ensure_ascii=False)
    assert body['tokens']['gatewayAuth']['configured'] is True
    assert body['tokens']['gatewayAuth']['redactedToken'].startswith('rea')
    assert body['sources']['tasksSource']['count'] == 2
    assert body['sources']['liveStatus']['count'] == 2
    assert body['sources']['backendDb']['count'] == 2
    assert body['sources']['consistent'] is True
    assert body['search']['groups']['tasks'] == 1
    assert body['search']['groups']['logs'] >= 1
    assert body['search']['groups']['sessions'] == 1
    assert body['search']['groups']['governanceSamples'] == 1
    assert body['logs']['streams']['edict'] >= 1
    assert body['logs']['streams']['scheduler'] >= 1
    assert body['logs']['streams']['dispatch'] >= 1
    assert body['cron']['summary']['total'] == 1
    assert body['cron']['summary']['failed'] == 1
    assert body['cron']['items'][0]['nextRunHint']
    assert body['sessions']['items'][0]['status'] == 'running'
    assert body['sessions']['items'][0]['messageCount'] == 2
    assert body['sessions']['items'][0]['markers']['heartbeat'] is False
    assert body['tokens']['summary']['byAgent']['taizi']['tokens'] == 321
    assert body['tokens']['summary']['byModel']['gpt-5.4']['tokens'] == 321
    assert body['tokens']['summary']['byTask']['OBS-SEARCH-1']['tokens'] == 321
    assert body['tokens']['summary']['alerts']


def test_observability_panel_route_returns_payload(tmp_path):
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    (data_dir / 'tasks_source.json').write_text(json.dumps([{
        'id': 'OBS-ROUTE-1',
        'title': 'route token smoke',
        'state': 'Doing',
        'org': '太子',
        'now': 'token path check',
        'updatedAt': '2026-05-11T02:00:00Z',
    }], ensure_ascii=False), encoding='utf-8')

    import server as srv
    srv.DATA = data_dir
    srv._ACTIVE_TASK_DATA_DIR = None

    from http.server import HTTPServer
    port = 18972
    httpd = HTTPServer(('127.0.0.1', port), srv.Handler)
    t = threading.Thread(target=httpd.handle_request, daemon=True)
    t.start()
    time.sleep(0.1)

    conn = HTTPConnection('127.0.0.1', port, timeout=5)
    conn.request('GET', '/api/observability-panel?q=token&limit=3')
    resp = conn.getresponse()
    body = json.loads(resp.read())
    conn.close()
    httpd.server_close()

    assert resp.status == 200
    assert body['ok'] is True
    assert body['query'] == 'token'
    assert body['stats']['matchingTasks'] == 1
