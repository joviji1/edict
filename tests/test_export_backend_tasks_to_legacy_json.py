import importlib.util
import json
import pathlib
import sys

ROOT = pathlib.Path('/root/.openclaw/workspace/edict')
SCRIPTS = ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

SCRIPT = SCRIPTS / 'export_backend_tasks_to_legacy_json.py'


def _load_module():
    spec = importlib.util.spec_from_file_location('export_backend_tasks_to_legacy_json', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sample_task():
    return {
        'task_id': 'task-1',
        'id': 'task-1',
        'trace_id': 'trace-1',
        'title': '后端导出样本',
        'description': '从 backend 导到旧看板',
        'priority': '高',
        'state': 'PendingConfirm',
        'assignee_org': '工部',
        'creator': 'taizi',
        'tags': ['governance'],
        'meta': {'foo': 'bar'},
        'org': '尚书省',
        'official': '工部尚书',
        'now': '等待用户确认',
        'eta': '2026-04-27T00:00:00+00:00',
        'block': '无',
        'output': '/tmp/report.md',
        'archived': False,
        'flow_log': [{'from': '门下省', 'to': '尚书省', 'remark': '待批'}],
        'progress_log': [{'agent': 'shangshu', 'text': '已提交待批'}],
        'todos': [{'id': '1', 'title': '确认', 'status': 'pending'}],
        'templateId': 'tpl-1',
        'templateParams': {'city': '北京'},
        'ac': '用户确认即可',
        'targetDept': '工部',
        '_scheduler': {'stallReason': 'waiting_dependency', 'retryCount': 2},
        'pending_confirm': {'requested_at': '2026-04-26T22:00:00+00:00', 'question': '买吗？'},
        'gate_checks': [{'gate': 'menxia_review', 'result': 'approved'}],
        'memory_extracted': {'done': {'agent': 'gongbu'}},
        'createdAt': '2026-04-26T21:00:00+00:00',
        'updatedAt': '2026-04-26T22:00:00+00:00',
    }


def test_transform_task_preserves_governance_fields():
    mod = _load_module()

    row = mod.transform_task(_sample_task())

    assert row['id'] == 'task-1'
    assert row['title'] == '后端导出样本'
    assert row['state'] == 'PendingConfirm'
    assert row['org'] == '尚书省'
    assert row['official'] == '工部尚书'
    assert row['pending_confirm']['question'] == '买吗？'
    assert row['gate_checks'][0]['gate'] == 'menxia_review'
    assert row['memory_extracted']['done']['agent'] == 'gongbu'
    assert row['templateId'] == 'tpl-1'
    assert row['templateParams']['city'] == '北京'
    assert row['targetDept'] == '工部'
    assert row['_scheduler']['retryCount'] == 2
    assert row['sourceLayer'] == 'backend_export'


def test_is_temporary_probe_task_detects_probe_markers():
    mod = _load_module()

    assert mod.is_temporary_probe_task({
        'title': '[probe] 回写链现网实跑验证 2026-05-02',
        'tags': ['PROBE-WRITEBACK-20260502'],
        'meta': {'legacy_id': 'PROBE-WRITEBACK-20260502', 'source': 'taizi.audit.probe'},
        'creator': 'taizi-audit',
    }) is True

    assert mod.is_temporary_probe_task(_sample_task()) is False


def test_main_writes_tasks_source_and_export_meta(tmp_path, monkeypatch):
    mod = _load_module()
    tasks_file = tmp_path / 'tasks_source.json'
    meta_file = tmp_path / 'tasks_backend_export_meta.json'

    monkeypatch.setattr(mod, 'TASKS_FILE', tasks_file)
    monkeypatch.setattr(mod, 'EXPORT_META_FILE', meta_file)
    monkeypatch.setattr(mod, 'fetch_backend_tasks', lambda: [_sample_task()])

    rc = mod.main()

    assert rc == 0
    tasks = json.loads(tasks_file.read_text(encoding='utf-8'))
    meta = json.loads(meta_file.read_text(encoding='utf-8'))
    assert tasks[0]['id'] == 'task-1'
    assert tasks[0]['sourceLayer'] == 'backend_export'
    assert meta['taskSource'] == 'backend_api_export'
    assert meta['count'] == 1
    assert meta['tasksFile'] == str(tasks_file)


def test_main_filters_temporary_probe_tasks_from_export(tmp_path, monkeypatch):
    mod = _load_module()
    tasks_file = tmp_path / 'tasks_source.json'
    meta_file = tmp_path / 'tasks_backend_export_meta.json'
    probe_task = {
        'task_id': 'probe-1',
        'id': 'probe-1',
        'title': '[probe] 回写链现网实跑验证 2026-05-02',
        'state': 'Taizi',
        'assignee_org': '工部',
        'creator': 'taizi-audit',
        'tags': ['PROBE-WRITEBACK-20260502'],
        'meta': {'legacy_id': 'PROBE-WRITEBACK-20260502', 'source': 'taizi.audit.probe'},
        'updatedAt': '2026-05-02T12:00:00Z',
    }

    monkeypatch.setattr(mod, 'TASKS_FILE', tasks_file)
    monkeypatch.setattr(mod, 'EXPORT_META_FILE', meta_file)
    monkeypatch.setattr(mod, 'fetch_backend_tasks', lambda: [_sample_task(), probe_task])

    rc = mod.main()

    assert rc == 0
    tasks = json.loads(tasks_file.read_text(encoding='utf-8'))
    assert [item['id'] for item in tasks] == ['task-1']
    meta = json.loads(meta_file.read_text(encoding='utf-8'))
    assert meta['count'] == 1


def test_main_does_not_overwrite_existing_tasks_when_fetch_fails(tmp_path, monkeypatch):
    mod = _load_module()
    tasks_file = tmp_path / 'tasks_source.json'
    tasks_file.write_text(json.dumps([{'id': 'keep-me'}], ensure_ascii=False), encoding='utf-8')
    meta_file = tmp_path / 'tasks_backend_export_meta.json'

    def boom():
        raise RuntimeError('backend unavailable')

    monkeypatch.setattr(mod, 'TASKS_FILE', tasks_file)
    monkeypatch.setattr(mod, 'EXPORT_META_FILE', meta_file)
    monkeypatch.setattr(mod, 'fetch_backend_tasks', boom)

    rc = mod.main()

    assert rc == 1
    assert json.loads(tasks_file.read_text(encoding='utf-8')) == [{'id': 'keep-me'}]
    assert meta_file.exists() is False


def test_main_skips_empty_overwrite_unless_explicitly_allowed(tmp_path, monkeypatch):
    mod = _load_module()
    tasks_file = tmp_path / 'tasks_source.json'
    tasks_file.write_text(json.dumps([{'id': 'keep-me'}], ensure_ascii=False), encoding='utf-8')
    meta_file = tmp_path / 'tasks_backend_export_meta.json'

    monkeypatch.setattr(mod, 'TASKS_FILE', tasks_file)
    monkeypatch.setattr(mod, 'EXPORT_META_FILE', meta_file)
    monkeypatch.setattr(mod, 'ALLOW_EMPTY', False)
    monkeypatch.setattr(mod, 'fetch_backend_tasks', lambda: [])

    rc = mod.main()

    assert rc == 2
    assert json.loads(tasks_file.read_text(encoding='utf-8')) == [{'id': 'keep-me'}]
    assert meta_file.exists() is False


def test_main_can_explicitly_export_empty_result(tmp_path, monkeypatch):
    mod = _load_module()
    tasks_file = tmp_path / 'tasks_source.json'
    tasks_file.write_text(json.dumps([{'id': 'keep-me'}], ensure_ascii=False), encoding='utf-8')
    meta_file = tmp_path / 'tasks_backend_export_meta.json'

    monkeypatch.setattr(mod, 'TASKS_FILE', tasks_file)
    monkeypatch.setattr(mod, 'EXPORT_META_FILE', meta_file)
    monkeypatch.setattr(mod, 'ALLOW_EMPTY', True)
    monkeypatch.setattr(mod, 'fetch_backend_tasks', lambda: [])

    rc = mod.main()

    assert rc == 0
    assert json.loads(tasks_file.read_text(encoding='utf-8')) == []
    meta = json.loads(meta_file.read_text(encoding='utf-8'))
    assert meta['count'] == 0
