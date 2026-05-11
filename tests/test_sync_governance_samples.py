import datetime
import importlib.util
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def recent_iso(hours_ago=0):
    dt = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=hours_ago)
    return dt.replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def recent_epoch_ms(hours_ago=0):
    dt = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=hours_ago)
    return int(dt.timestamp() * 1000)
SCRIPTS = ROOT / 'scripts'
sys.path.insert(0, str(SCRIPTS))

spec = importlib.util.spec_from_file_location('sync_governance_samples', SCRIPTS / 'sync_governance_samples.py')
samples = importlib.util.module_from_spec(spec)
spec.loader.exec_module(samples)


def test_main_extracts_and_merges_governance_samples(tmp_path, monkeypatch):
    data = tmp_path / 'data'
    data.mkdir()
    (data / 'tasks_runtime_view.json').write_text(json.dumps([
        {
            'id': 'OC-runtime-1',
            'title': '待审批样本',
            'state': 'PendingConfirm',
            'pending_confirm': {'target_state': 'Done', 'requested_at': recent_iso(3)},
            'sourceMeta': {'sessionId': 'sess-1', 'updatedAt': recent_epoch_ms(3)},
        }
    ], ensure_ascii=False), encoding='utf-8')
    (data / 'tasks_source.json').write_text(json.dumps([
        {
            'id': 'JJC-1',
            'state': 'Blocked',
            'autopsy': {'reason': 'provider_timeout'},
            'updatedAt': recent_iso(2),
        }
    ], ensure_ascii=False), encoding='utf-8')
    (data / 'mission_control_tasks.json').write_text(json.dumps([
        {
            'id': 'MC-1',
            'state': 'Review',
            'templateId': 'tpl-001',
            'templateParams': {'topic': '治理'},
            'updatedAt': recent_iso(1),
        }
    ], ensure_ascii=False), encoding='utf-8')
    (data / 'manual_parallel_tasks.json').write_text(json.dumps([
        {
            'id': 'OC-runtime-1',
            'state': 'PendingConfirm',
            'gate_checks': [{'result': 'pending'}],
            'notifications': {'pending_confirm_sent': True},
            'updatedAt': recent_iso(),
        }
    ], ensure_ascii=False), encoding='utf-8')

    monkeypatch.setattr(samples, 'DATA', data)
    monkeypatch.setattr(samples, 'SAMPLES_FILE', data / 'tasks_governance_samples.json')
    monkeypatch.setattr(samples, 'RUNTIME_FILE', data / 'tasks_runtime_view.json')
    monkeypatch.setattr(samples, 'LEGACY_TASKS_FILE', data / 'tasks_source.json')
    monkeypatch.setattr(samples, 'MISSION_FILE', data / 'mission_control_tasks.json')
    monkeypatch.setattr(samples, 'MANUAL_FILE', data / 'manual_parallel_tasks.json')

    samples.main()

    payload = json.loads((data / 'tasks_governance_samples.json').read_text(encoding='utf-8'))
    assert len(payload) == 3
    runtime_item = next(item for item in payload if item['id'] == 'OC-runtime-1')
    assert runtime_item['sourceLayer'] == 'governance_sample'
    assert set(runtime_item['sampleSources']) == {'runtime_view', 'manual_parallel'}
    assert runtime_item['pending_confirm']['target_state'] == 'Done'
    assert runtime_item['gate_checks'][0]['result'] == 'pending'
    assert runtime_item['notifications']['pending_confirm_sent'] is True
    assert runtime_item['sampleCapturedAt']
    assert runtime_item['sampleLastSeenAt']

    jjc_item = next(item for item in payload if item['id'] == 'JJC-1')
    assert jjc_item['autopsy']['reason'] == 'provider_timeout'

    mission_item = next(item for item in payload if item['id'] == 'MC-1')
    assert mission_item['templateId'] == 'tpl-001'


def test_main_skips_temporary_probe_tasks(tmp_path, monkeypatch):
    data = tmp_path / 'data'
    data.mkdir()
    (data / 'tasks_runtime_view.json').write_text(json.dumps([
        {
            'id': 'probe-1',
            'title': '[probe] 回写链现网实跑验证 2026-05-02',
            'state': 'Zhongshu',
            'targetDept': '工部',
            'tags': ['PROBE-WRITEBACK-20260502'],
            'meta': {'legacy_id': 'PROBE-WRITEBACK-20260502', 'source': 'taizi.audit.probe'},
            'creator': 'taizi-audit',
        }
    ], ensure_ascii=False), encoding='utf-8')
    (data / 'tasks_source.json').write_text('[]', encoding='utf-8')
    (data / 'mission_control_tasks.json').write_text('[]', encoding='utf-8')
    (data / 'manual_parallel_tasks.json').write_text('[]', encoding='utf-8')
    (data / 'tasks_governance_samples.json').write_text(json.dumps([
        {
            'id': 'probe-1',
            'title': '[probe] 回写链现网实跑验证 2026-05-02',
            'state': 'Taizi',
            'targetDept': '工部',
            'tags': ['PROBE-WRITEBACK-20260502'],
            'meta': {'legacy_id': 'PROBE-WRITEBACK-20260502', 'source': 'taizi.audit.probe'},
            'creator': 'taizi-audit',
            'sampleLastSeenAt': '2026-05-02T12:00:00Z',
            'sourceLayer': 'governance_sample',
            'sampleSources': ['legacy_tasks_source'],
        }
    ], ensure_ascii=False), encoding='utf-8')

    monkeypatch.setattr(samples, 'DATA', data)
    monkeypatch.setattr(samples, 'SAMPLES_FILE', data / 'tasks_governance_samples.json')
    monkeypatch.setattr(samples, 'RUNTIME_FILE', data / 'tasks_runtime_view.json')
    monkeypatch.setattr(samples, 'LEGACY_TASKS_FILE', data / 'tasks_source.json')
    monkeypatch.setattr(samples, 'MISSION_FILE', data / 'mission_control_tasks.json')
    monkeypatch.setattr(samples, 'MANUAL_FILE', data / 'manual_parallel_tasks.json')

    samples.main()

    payload = json.loads((data / 'tasks_governance_samples.json').read_text(encoding='utf-8'))
    assert payload == []



def test_main_clears_stale_pending_confirm_when_source_resolved(tmp_path, monkeypatch):
    data = tmp_path / 'data'
    data.mkdir()
    (data / 'tasks_governance_samples.json').write_text(json.dumps([
        {
            'id': 'OC-resolved-1',
            'state': 'PendingConfirm',
            'pending_confirm': {'target_state': 'Done', 'requested_at': recent_iso(3)},
            'gate_checks': [{'result': 'pending'}],
            'sampleCapturedAt': recent_iso(3),
            'sampleLastSeenAt': recent_iso(3),
            'sampleSources': ['legacy_tasks_source'],
            'sourceLayer': 'governance_sample',
        }
    ], ensure_ascii=False), encoding='utf-8')
    (data / 'tasks_runtime_view.json').write_text('[]', encoding='utf-8')
    (data / 'tasks_source.json').write_text(json.dumps([
        {
            'id': 'OC-resolved-1',
            'state': 'Done',
            'gate_checks': [
                {'result': 'pending'},
                {'result': 'approved', 'to': 'Done'}
            ],
            'updatedAt': recent_iso(2),
        }
    ], ensure_ascii=False), encoding='utf-8')
    (data / 'mission_control_tasks.json').write_text('[]', encoding='utf-8')
    (data / 'manual_parallel_tasks.json').write_text('[]', encoding='utf-8')

    monkeypatch.setattr(samples, 'DATA', data)
    monkeypatch.setattr(samples, 'SAMPLES_FILE', data / 'tasks_governance_samples.json')
    monkeypatch.setattr(samples, 'RUNTIME_FILE', data / 'tasks_runtime_view.json')
    monkeypatch.setattr(samples, 'LEGACY_TASKS_FILE', data / 'tasks_source.json')
    monkeypatch.setattr(samples, 'MISSION_FILE', data / 'mission_control_tasks.json')
    monkeypatch.setattr(samples, 'MANUAL_FILE', data / 'manual_parallel_tasks.json')

    samples.main()

    payload = json.loads((data / 'tasks_governance_samples.json').read_text(encoding='utf-8'))
    item = next(entry for entry in payload if entry['id'] == 'OC-resolved-1')
    assert item['state'] == 'Done'
    assert 'pending_confirm' not in item
    assert item['gate_checks'][-1]['result'] == 'approved'


def test_main_sanitizes_probe_text_from_existing_sample_history(tmp_path, monkeypatch):
    data = tmp_path / 'data'
    data.mkdir()
    task_id = 'TASK-REAL-001'
    probe_id = '4455998e-77ae-446c-b786-f2c476ac94ff'
    (data / 'tasks_governance_samples.json').write_text(json.dumps([
        {
            'id': task_id,
            'title': '太子会话',
            'state': 'Review',
            'targetDept': '工部',
            'sampleCapturedAt': '2026-05-02T12:00:00Z',
            'sampleLastSeenAt': '2026-05-02T12:00:00Z',
            'sampleSources': ['legacy_tasks_source'],
            'sourceLayer': 'governance_sample',
            'activity': [
                {
                    'kind': 'user',
                    'text': f'User: 任务ID: {probe_id} 旨意: [probe] 回写链现网实跑验证',
                    'rawText': f'{probe_id} [probe]'
                },
                {
                    'kind': 'assistant',
                    'text': '正常保留的审议意见',
                    'rawText': '正常保留的审议意见'
                }
            ],
            'progress_log': [
                {
                    'kind': 'tool',
                    'text': 'Tool',
                    'rawText': '/data/_probe_backups/tasks_source.PROBE-SCHED-20260426031517.bak.json'
                },
                {
                    'kind': 'tool',
                    'text': 'Tool',
                    'rawText': '正常工具输出'
                }
            ],
            'output': '包含 PROBE- 与 [probe] 的旧输出',
        }
    ], ensure_ascii=False), encoding='utf-8')
    (data / 'tasks_runtime_view.json').write_text('[]', encoding='utf-8')
    (data / 'tasks_source.json').write_text(json.dumps([
        {
            'id': task_id,
            'title': '太子会话',
            'state': 'Review',
            'targetDept': '工部',
            'updatedAt': '2026-05-03T08:00:00Z',
            'gate_checks': [{'result': 'pending'}],
            'activity': [
                {'kind': 'assistant', 'text': '正常新 activity', 'rawText': '正常新 activity'}
            ],
            'progress_log': [
                {'kind': 'tool', 'text': 'Tool', 'rawText': '正常新 progress'}
            ],
            'output': '正常输出',
        }
    ], ensure_ascii=False), encoding='utf-8')
    (data / 'mission_control_tasks.json').write_text('[]', encoding='utf-8')
    (data / 'manual_parallel_tasks.json').write_text('[]', encoding='utf-8')

    monkeypatch.setattr(samples, 'DATA', data)
    monkeypatch.setattr(samples, 'SAMPLES_FILE', data / 'tasks_governance_samples.json')
    monkeypatch.setattr(samples, 'RUNTIME_FILE', data / 'tasks_runtime_view.json')
    monkeypatch.setattr(samples, 'LEGACY_TASKS_FILE', data / 'tasks_source.json')
    monkeypatch.setattr(samples, 'MISSION_FILE', data / 'mission_control_tasks.json')
    monkeypatch.setattr(samples, 'MANUAL_FILE', data / 'manual_parallel_tasks.json')

    samples.main()

    payload = json.loads((data / 'tasks_governance_samples.json').read_text(encoding='utf-8'))
    item = next(entry for entry in payload if entry['id'] == task_id)
    text = json.dumps(item, ensure_ascii=False)
    assert probe_id not in text
    assert '[probe]' not in text.lower()
    assert 'PROBE-' not in text
    assert '_probe_backups' not in text
    assert {'kind': 'assistant', 'text': '正常保留的审议意见', 'rawText': '正常保留的审议意见'} in item['activity']
    assert {'kind': 'assistant', 'text': '正常新 activity', 'rawText': '正常新 activity'} in item['activity']
    assert item['progress_log'] == [
        {'kind': 'tool', 'text': 'Tool', 'rawText': '正常新 progress'}
    ]
    assert item['output'] == '正常输出'
