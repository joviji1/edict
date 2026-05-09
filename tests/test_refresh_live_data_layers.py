import importlib.util
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path('/root/.openclaw/workspace/edict')
SCRIPTS = ROOT / 'scripts'
sys.path.insert(0, str(SCRIPTS))

spec = importlib.util.spec_from_file_location('refresh_live_data', SCRIPTS / 'refresh_live_data.py')
refresh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(refresh)


def test_main_exposes_task_layer_counts(tmp_path, monkeypatch):
    data = tmp_path / 'data'
    data.mkdir()
    (data / 'officials_stats.json').write_text(json.dumps({'officials': [{'label': '中书省'}]}, ensure_ascii=False), encoding='utf-8')
    (data / 'tasks_source.json').write_text(json.dumps([
        {'id': 'OC-1', 'official': '中书省', 'org': '中书省', 'state': 'Doing', 'sourceLayer': 'runtime', 'sourceMeta': {'updatedAt': 1714080000000}},
        {'id': 'GS-1', 'official': '中书省', 'org': '中书省', 'state': 'Blocked', 'sourceLayer': 'governance_sample'},
        {'id': 'JJC-1', 'official': '中书省', 'org': '中书省', 'state': 'Done', 'sourceLayer': 'jjc_archive'}
    ], ensure_ascii=False), encoding='utf-8')
    (data / 'tasks_runtime_view.json').write_text(json.dumps([{'id': 'OC-1'}], ensure_ascii=False), encoding='utf-8')
    (data / 'tasks_governance_samples.json').write_text(json.dumps([{'id': 'GS-1'}, {'id': 'GS-2'}], ensure_ascii=False), encoding='utf-8')
    (data / 'tasks_jjc_archive.json').write_text(json.dumps([{'id': 'JJC-1'}, {'id': 'JJC-2'}, {'id': 'JJC-3'}], ensure_ascii=False), encoding='utf-8')
    (data / 'sync_status.json').write_text(json.dumps({'ok': True, 'durationMs': 12}, ensure_ascii=False), encoding='utf-8')

    monkeypatch.setattr(refresh, 'DATA', data)
    monkeypatch.setattr(refresh, 'RUNTIME_FILE', data / 'tasks_runtime_view.json')
    monkeypatch.setattr(refresh, 'SAMPLES_FILE', data / 'tasks_governance_samples.json')
    monkeypatch.setattr(refresh, 'ARCHIVE_FILE', data / 'tasks_jjc_archive.json')

    refresh.main()

    payload = json.loads((data / 'live_status.json').read_text(encoding='utf-8'))
    assert payload['taskLayers'] == {
        'runtimeCount': 1,
        'governanceSampleCount': 2,
        'jjcArchiveCount': 3,
    }
    assert payload['health']['syncOk'] is True
    assert payload['metrics']['blocked'] == 1



def test_main_exposes_backend_export_task_source_meta(tmp_path, monkeypatch):
    data = tmp_path / 'data'
    data.mkdir()
    (data / 'officials_stats.json').write_text(json.dumps({'officials': [{'label': '工部'}]}, ensure_ascii=False), encoding='utf-8')
    (data / 'tasks_source.json').write_text(json.dumps([
        {'id': 'task-1', 'official': '工部尚书', 'org': '工部', 'state': 'PendingConfirm', 'sourceLayer': 'backend_export'}
    ], ensure_ascii=False), encoding='utf-8')
    (data / 'tasks_runtime_view.json').write_text('[]', encoding='utf-8')
    (data / 'tasks_governance_samples.json').write_text('[]', encoding='utf-8')
    (data / 'tasks_jjc_archive.json').write_text('[]', encoding='utf-8')
    (data / 'sync_status.json').write_text(json.dumps({'ok': True, 'durationMs': 3}, ensure_ascii=False), encoding='utf-8')
    (data / 'tasks_backend_export_meta.json').write_text(json.dumps({
        'taskSource': 'backend_api_export',
        'backendUrl': 'http://127.0.0.1:18000',
        'count': 1,
    }, ensure_ascii=False), encoding='utf-8')

    monkeypatch.setattr(refresh, 'DATA', data)
    monkeypatch.setattr(refresh, 'RUNTIME_FILE', data / 'tasks_runtime_view.json')
    monkeypatch.setattr(refresh, 'SAMPLES_FILE', data / 'tasks_governance_samples.json')
    monkeypatch.setattr(refresh, 'ARCHIVE_FILE', data / 'tasks_jjc_archive.json')

    refresh.main()

    payload = json.loads((data / 'live_status.json').read_text(encoding='utf-8'))
    assert payload['taskSource'] == 'backend_api_export'
    assert payload['taskSourceMeta']['backendUrl'] == 'http://127.0.0.1:18000'
    assert payload['taskSourceMeta']['count'] == 1


def test_main_ignores_stale_backend_export_meta_when_tasks_are_not_backend_export(tmp_path, monkeypatch):
    data = tmp_path / 'data'
    data.mkdir()
    (data / 'officials_stats.json').write_text(json.dumps({'officials': [{'label': '中书省'}]}, ensure_ascii=False), encoding='utf-8')
    (data / 'tasks_source.json').write_text(json.dumps([
        {'id': 'task-1', 'official': '中书省', 'org': '中书省', 'state': 'Doing', 'sourceLayer': 'runtime'}
    ], ensure_ascii=False), encoding='utf-8')
    (data / 'tasks_runtime_view.json').write_text(json.dumps([{'id': 'task-1'}], ensure_ascii=False), encoding='utf-8')
    (data / 'tasks_governance_samples.json').write_text('[]', encoding='utf-8')
    (data / 'tasks_jjc_archive.json').write_text('[]', encoding='utf-8')
    (data / 'sync_status.json').write_text(json.dumps({'ok': True, 'durationMs': 3}, ensure_ascii=False), encoding='utf-8')
    (data / 'tasks_backend_export_meta.json').write_text(json.dumps({
        'taskSource': 'backend_api_export',
        'backendUrl': 'http://127.0.0.1:18000',
        'count': 99,
    }, ensure_ascii=False), encoding='utf-8')

    monkeypatch.setattr(refresh, 'DATA', data)
    monkeypatch.setattr(refresh, 'RUNTIME_FILE', data / 'tasks_runtime_view.json')
    monkeypatch.setattr(refresh, 'SAMPLES_FILE', data / 'tasks_governance_samples.json')
    monkeypatch.setattr(refresh, 'ARCHIVE_FILE', data / 'tasks_jjc_archive.json')

    refresh.main()

    payload = json.loads((data / 'live_status.json').read_text(encoding='utf-8'))
    assert payload['taskSource'] == 'tasks_source.json'
    assert payload['taskSourceMeta'] == {}


def test_refresh_live_data_respects_edict_data_dir_env(tmp_path):
    data = tmp_path / 'data'
    data.mkdir()
    (data / 'officials_stats.json').write_text(json.dumps({'officials': [{'label': '中书省'}]}, ensure_ascii=False), encoding='utf-8')
    (data / 'tasks_source.json').write_text(json.dumps([
        {'id': 'ENV-1', 'official': '中书省', 'org': '中书省', 'state': 'Blocked', 'sourceLayer': 'governance_sample'}
    ], ensure_ascii=False), encoding='utf-8')
    (data / 'tasks_runtime_view.json').write_text('[]', encoding='utf-8')
    (data / 'tasks_governance_samples.json').write_text(json.dumps([{'id': 'ENV-1'}], ensure_ascii=False), encoding='utf-8')
    (data / 'tasks_jjc_archive.json').write_text('[]', encoding='utf-8')
    (data / 'sync_status.json').write_text(json.dumps({'ok': True, 'durationMs': 1}, ensure_ascii=False), encoding='utf-8')

    env = dict(__import__('os').environ)
    env['EDICT_DATA_DIR'] = str(data)
    result = subprocess.run(['python3', str(SCRIPTS / 'refresh_live_data.py')], cwd=str(ROOT), capture_output=True, text=True, env=env)
    assert result.returncode == 0, result.stderr

    payload = json.loads((data / 'live_status.json').read_text(encoding='utf-8'))
    assert payload['taskLayers']['governanceSampleCount'] == 1
    assert payload['tasks'][0]['id'] == 'ENV-1'
