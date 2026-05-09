import importlib.util
import json
import pathlib
import sys

ROOT = pathlib.Path('/root/.openclaw/workspace/edict')
SCRIPTS = ROOT / 'scripts'
sys.path.insert(0, str(SCRIPTS))

spec = importlib.util.spec_from_file_location('rebuild_task_views', SCRIPTS / 'rebuild_task_views.py')
rebuild = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rebuild)


def test_rebuild_prefers_newer_governance_state_over_stale_runtime(tmp_path, monkeypatch):
    data = tmp_path / 'data'
    data.mkdir()

    runtime_task = {
        'id': 'task-1',
        'state': 'Taizi',
        'org': '太子',
        'updatedAt': '2026-05-02T09:00:06Z',
        'now': '等待太子接旨分拣',
        '_scheduler': {},
        'progress_log': [],
        'flow_log': [{'reason': '任务创建'}],
        'sourceMeta': {'updatedAt': '2026-05-02T09:00:06Z'},
    }
    governance_task = {
        'id': 'task-1',
        'state': 'Zhongshu',
        'org': '中书省',
        'updatedAt': '2026-05-02T11:14:00Z',
        'now': '中书省起草中',
        '_scheduler': {'lastDispatchTrigger': 'taizi-scan-retry'},
        'progress_log': [{'content': '已在中书省，无需重复流转。'}],
        'flow_log': [{'reason': 'Taizi -> Zhongshu'}],
        'sampleLastSeenAt': '2026-05-02T11:14:00Z',
    }

    (data / 'tasks_runtime_view.json').write_text(json.dumps([runtime_task], ensure_ascii=False), encoding='utf-8')
    (data / 'tasks_governance_samples.json').write_text(json.dumps([governance_task], ensure_ascii=False), encoding='utf-8')
    (data / 'tasks_jjc_archive.json').write_text('[]', encoding='utf-8')
    (data / 'tasks_source.json').write_text('[]', encoding='utf-8')

    monkeypatch.setattr(rebuild, 'DATA', data)
    monkeypatch.setattr(rebuild, 'RUNTIME_FILE', data / 'tasks_runtime_view.json')
    monkeypatch.setattr(rebuild, 'SAMPLES_FILE', data / 'tasks_governance_samples.json')
    monkeypatch.setattr(rebuild, 'ARCHIVE_FILE', data / 'tasks_jjc_archive.json')
    monkeypatch.setattr(rebuild, 'TASKS_FILE', data / 'tasks_source.json')

    rebuild.main()

    payload = json.loads((data / 'tasks_source.json').read_text(encoding='utf-8'))
    task = payload[0]
    assert task['state'] == 'Zhongshu'
    assert task['org'] == '中书省'
    assert task['updatedAt'] == '2026-05-02T11:14:00Z'
    assert task['now'] == '中书省起草中'
    assert task['_scheduler']['lastDispatchTrigger'] == 'taizi-scan-retry'
    assert task['progress_log'][0]['content'] == '已在中书省，无需重复流转。'
