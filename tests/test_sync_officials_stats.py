import importlib.util
import json
import pathlib
import sys

ROOT = pathlib.Path('/root/.openclaw/workspace/edict')
SCRIPTS = ROOT / 'scripts'
sys.path.insert(0, str(SCRIPTS))

spec = importlib.util.spec_from_file_location('sync_officials_stats', SCRIPTS / 'sync_officials_stats.py')
stats = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stats)


def test_task_stats_include_sla_success_timeout_and_resource_cost():
    tasks = [
        {
            'id': 'T-DONE-1', 'org': '兵部', 'state': 'Done',
            'progress_log': [
                {'tokens': 1000, 'cost': 0.02, 'elapsed': 8},
                {'tokens': 500, 'cost': 0.01, 'elapsed': 12},
            ],
            '_scheduler': {'retryCount': 1, 'stallReason': 'no_heartbeat'},
        },
        {
            'id': 'T-BLOCK-1', 'org': '兵部', 'state': 'Blocked',
            'block': '模型接口超时',
            'autopsy': {'reason': 'provider_timeout'},
            'progress_log': [{'tokens': 300, 'cost': 0.03, 'elapsed': 20}],
            '_scheduler': {'retryCount': 3, 'stallReason': 'provider_timeout'},
        },
        {
            'id': 'T-ACTIVE-1', 'org': '兵部', 'state': 'Doing',
            '_scheduler': {'retryCount': 2, 'stallReason': 'no_heartbeat'},
            'progress_log': [{'tokens': 200, 'cost': 0.04, 'elapsed': 5}],
        },
        {'id': 'T-OTHER', 'org': '工部', 'state': 'Done'},
    ]

    body = stats.get_task_stats('兵部', tasks)

    assert body['tasks_done'] == 1
    assert body['tasks_blocked'] == 1
    assert body['tasks_total'] == 3
    assert body['success_rate'] == 0.5
    assert body['timeout_count'] == 1
    assert body['timeout_rate'] == round(1 / 3, 4)
    assert body['scheduler_retries'] == 6
    assert body['task_tokens'] == 2000
    assert body['task_cost_usd'] == 0.1
    assert body['task_elapsed_sec'] == 45
    assert body['sla_score'] == 10
    assert body['productivity_score'] == 56.0
    assert body['stability_score'] == 40.0
    assert body['efficiency_score'] == 93.5
    assert body['composite_score'] == 60.2
    assert body['merit_history'] == [
        {'task_id': 'T-DONE-1', 'score': 9, 'state': 'Done'},
        {'task_id': 'T-BLOCK-1', 'score': -9, 'state': 'Blocked'},
        {'task_id': 'T-ACTIVE-1', 'score': 0, 'state': 'Doing'},
    ]


def test_main_writes_extended_official_stats(tmp_path, monkeypatch):
    data = tmp_path / 'data'
    data.mkdir()
    (data / 'tasks_source.json').write_text(json.dumps([
        {'id': 'T1', 'org': '兵部', 'state': 'Done', 'progress_log': [{'tokens': 100, 'cost': 0.01, 'elapsed': 3}]},
        {'id': 'T2', 'org': '兵部', 'state': 'Blocked', 'autopsy': {'reason': 'provider_timeout'}, '_scheduler': {'retryCount': 1}},
        {'id': 'T3', 'org': '工部', 'state': 'Done', 'progress_log': [{'tokens': 20, 'cost': 0.005, 'elapsed': 2}]},
    ], ensure_ascii=False), encoding='utf-8')
    (data / 'live_status.json').write_text(json.dumps({'tasks': []}), encoding='utf-8')

    monkeypatch.setattr(stats, 'DATA', data)
    monkeypatch.setattr(stats, 'AGENTS_ROOT', tmp_path / 'agents')
    monkeypatch.setattr(stats, 'OPENCLAW_CFG', tmp_path / 'missing.json')
    monkeypatch.setattr(stats, '_OPENCLAW_CACHE', None)

    stats.main()

    payload = json.loads((data / 'officials_stats.json').read_text(encoding='utf-8'))
    bingbu = next(o for o in payload['officials'] if o['id'] == 'bingbu')
    gongbu = next(o for o in payload['officials'] if o['id'] == 'gongbu')
    assert payload['top']['id'] == payload['officials'][0]['id']
    assert bingbu['success_rate'] == 0.5
    assert bingbu['timeout_rate'] == 0.5
    assert bingbu['task_cost_usd'] == 0.01
    assert bingbu['productivity_score'] == 55.0
    assert bingbu['stability_score'] == 65.0
    assert bingbu['efficiency_score'] == 99.4
    assert bingbu['composite_score'] == 68.63
    assert bingbu['tags'] == ['需训练']
    assert gongbu['tags'] == ['能臣']
    assert bingbu['merit_history'] == [
        {'task_id': 'T1', 'score': 10, 'state': 'Done'},
        {'task_id': 'T2', 'score': -7, 'state': 'Blocked'},
    ]
    assert 'sla_score' in bingbu
    assert payload['totals']['tasks_blocked'] == 1
    assert payload['totals']['timeout_count'] == 1
    assert payload['totals']['task_cost_usd'] == 0.015
