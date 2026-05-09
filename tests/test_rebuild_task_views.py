import importlib.util
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path('/root/.openclaw/workspace/edict')
SCRIPTS = ROOT / 'scripts'
sys.path.insert(0, str(SCRIPTS))

spec = importlib.util.spec_from_file_location('rebuild_task_views', SCRIPTS / 'rebuild_task_views.py')
rebuild = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rebuild)


def test_main_rebuilds_aggregate_from_three_layers(tmp_path, monkeypatch):
    data = tmp_path / 'data'
    data.mkdir()
    (data / 'tasks_runtime_view.json').write_text(json.dumps([
        {'id': 'OC-1', 'title': 'runtime', 'state': 'Doing', 'sourceMeta': {'updatedAt': 1714080000000}}
    ], ensure_ascii=False), encoding='utf-8')
    (data / 'tasks_governance_samples.json').write_text(json.dumps([
        {'id': 'OC-1', 'title': 'runtime sample', 'state': 'PendingConfirm', 'pending_confirm': {'target_state': 'Done'}, 'sampleLastSeenAt': '2026-04-26T03:00:00Z'},
        {'id': 'GS-1', 'title': 'governance sample', 'state': 'Blocked', 'autopsy': {'reason': 'timeout'}, 'sampleLastSeenAt': '2026-04-26T02:00:00Z'}
    ], ensure_ascii=False), encoding='utf-8')
    (data / 'tasks_jjc_archive.json').write_text(json.dumps([
        {'id': 'JJC-OLD', 'title': 'old archive', 'state': 'Done', 'updatedAt': '2026-04-20T02:00:00Z'}
    ], ensure_ascii=False), encoding='utf-8')
    (data / 'tasks_source.json').write_text(json.dumps([
        {'id': 'JJC-NEW', 'title': 'new archive', 'state': 'Done', 'updatedAt': '2026-04-26T01:00:00Z'}
    ], ensure_ascii=False), encoding='utf-8')

    monkeypatch.setattr(rebuild, 'DATA', data)
    monkeypatch.setattr(rebuild, 'RUNTIME_FILE', data / 'tasks_runtime_view.json')
    monkeypatch.setattr(rebuild, 'SAMPLES_FILE', data / 'tasks_governance_samples.json')
    monkeypatch.setattr(rebuild, 'ARCHIVE_FILE', data / 'tasks_jjc_archive.json')
    monkeypatch.setattr(rebuild, 'TASKS_FILE', data / 'tasks_source.json')

    rebuild.main()

    archive = json.loads((data / 'tasks_jjc_archive.json').read_text(encoding='utf-8'))
    assert {item['id'] for item in archive} == {'JJC-OLD', 'JJC-NEW'}
    assert all(item['sourceLayer'] == 'jjc_archive' for item in archive)

    aggregate = json.loads((data / 'tasks_source.json').read_text(encoding='utf-8'))
    ids = [item['id'] for item in aggregate]
    assert ids == ['OC-1', 'GS-1', 'JJC-NEW', 'JJC-OLD']

    oc1 = next(item for item in aggregate if item['id'] == 'OC-1')
    assert oc1['sourceLayer'] == 'runtime'
    assert oc1['pending_confirm']['target_state'] == 'Done'

    gs1 = next(item for item in aggregate if item['id'] == 'GS-1')
    assert gs1['sourceLayer'] == 'governance_sample'



def test_rebuild_task_views_respects_edict_data_dir_env(tmp_path):
    data = tmp_path / 'data'
    data.mkdir()
    (data / 'tasks_runtime_view.json').write_text(json.dumps([
        {'id': 'ENV-RT-1', 'title': 'runtime env', 'state': 'Doing', 'sourceMeta': {'updatedAt': 1714080000000}}
    ], ensure_ascii=False), encoding='utf-8')
    (data / 'tasks_governance_samples.json').write_text(json.dumps([
        {'id': 'ENV-GS-1', 'title': 'sample env', 'state': 'Blocked', 'autopsy': {'reason': 'timeout'}, 'sampleLastSeenAt': '2026-04-26T02:00:00Z'}
    ], ensure_ascii=False), encoding='utf-8')
    (data / 'tasks_jjc_archive.json').write_text('[]', encoding='utf-8')
    (data / 'tasks_source.json').write_text('[]', encoding='utf-8')

    env = dict(__import__('os').environ)
    env['EDICT_DATA_DIR'] = str(data)
    result = subprocess.run(['python3', str(SCRIPTS / 'rebuild_task_views.py')], cwd=str(ROOT), capture_output=True, text=True, env=env)
    assert result.returncode == 0, result.stderr

    aggregate = json.loads((data / 'tasks_source.json').read_text(encoding='utf-8'))
    ids = [item['id'] for item in aggregate]
    assert ids == ['ENV-GS-1', 'ENV-RT-1']
