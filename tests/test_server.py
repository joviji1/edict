"""tests for dashboard/server.py route handling"""
import json, pathlib, sys, threading, time
from http.client import HTTPConnection

# Add project paths
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'dashboard'))
sys.path.insert(0, str(ROOT / 'scripts'))


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

    assert sync_calls[-1] == {'cmd': ['python3', str(srv.SCRIPTS / 'sync_agent_config.py')], 'timeout': 10, 'kwargs': {}}


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
    assert sync_calls == [{'cmd': ['python3', str(srv.SCRIPTS / 'sync_agent_config.py')], 'timeout': 10}]


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
