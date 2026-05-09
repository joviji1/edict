import importlib.util
import json
import pathlib
import sys

ROOT = pathlib.Path('/root/.openclaw/workspace/edict')
SCRIPTS = ROOT / 'scripts'
sys.path.insert(0, str(SCRIPTS))

spec = importlib.util.spec_from_file_location('sync_governance_samples', SCRIPTS / 'sync_governance_samples.py')
sync_samples = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync_samples)


def test_sync_governance_samples_keeps_newer_runtime_state_over_stale_legacy(tmp_path, monkeypatch):
    data = tmp_path / 'data'
    data.mkdir()

    runtime_task = {
        'id': 'task-1',
        'state': 'Zhongshu',
        'org': '中书省',
        'updatedAt': '2026-05-02T11:14:00Z',
        'pending_confirm': {'requested_at': '2026-05-02T11:14:00Z'},
        '_scheduler': {'lastDispatchTrigger': 'taizi-scan-retry'},
    }
    legacy_task = {
        'id': 'task-1',
        'state': 'Taizi',
        'org': '太子',
        'updatedAt': '2026-05-02T09:00:06Z',
        'pending_confirm': {'requested_at': '2026-05-02T09:00:06Z'},
        '_scheduler': {},
    }

    (data / 'tasks_runtime_view.json').write_text(json.dumps([runtime_task], ensure_ascii=False), encoding='utf-8')
    (data / 'tasks_source.json').write_text(json.dumps([legacy_task], ensure_ascii=False), encoding='utf-8')
    (data / 'tasks_governance_samples.json').write_text('[]', encoding='utf-8')
    (data / 'mission_control_tasks.json').write_text('[]', encoding='utf-8')
    (data / 'manual_parallel_tasks.json').write_text('[]', encoding='utf-8')

    monkeypatch.setattr(sync_samples, 'DATA', data)
    monkeypatch.setattr(sync_samples, 'RUNTIME_FILE', data / 'tasks_runtime_view.json')
    monkeypatch.setattr(sync_samples, 'LEGACY_TASKS_FILE', data / 'tasks_source.json')
    monkeypatch.setattr(sync_samples, 'SAMPLES_FILE', data / 'tasks_governance_samples.json')
    monkeypatch.setattr(sync_samples, 'MISSION_FILE', data / 'mission_control_tasks.json')
    monkeypatch.setattr(sync_samples, 'MANUAL_FILE', data / 'manual_parallel_tasks.json')

    sync_samples.main()

    payload = json.loads((data / 'tasks_governance_samples.json').read_text(encoding='utf-8'))
    task = payload[0]
    assert task['state'] == 'Zhongshu'
    assert task['org'] == '中书省'
    assert task['updatedAt'] == '2026-05-02T11:14:00Z'
    assert task['_scheduler']['lastDispatchTrigger'] == 'taizi-scan-retry'
