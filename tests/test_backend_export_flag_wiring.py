from pathlib import Path

ROOT = Path('/root/.openclaw/workspace/edict')


def test_run_loop_gates_backend_export_behind_feature_flag():
    content = (ROOT / 'scripts' / 'run_loop.sh').read_text(encoding='utf-8')

    assert 'EDICT_ENABLE_BACKEND_EXPORT' in content
    assert 'export_backend_tasks_to_legacy_json.py' in content
    assert '默认关闭' in content or 'default off' in content or 'feature flag' in content


def test_run_loop_invokes_openclaw_session_guard_before_runtime_sync():
    content = (ROOT / 'scripts' / 'run_loop.sh').read_text(encoding='utf-8')

    assert 'guard_openclaw_sessions.py' in content
    assert content.index('guard_openclaw_sessions.py') < content.index('sync_from_openclaw_runtime.py')


def test_install_first_sync_gates_backend_export_behind_feature_flag():
    content = (ROOT / 'install.sh').read_text(encoding='utf-8')

    assert 'EDICT_ENABLE_BACKEND_EXPORT' in content
    assert 'export_backend_tasks_to_legacy_json.py' in content


def test_install_first_sync_invokes_openclaw_session_guard_before_runtime_sync():
    content = (ROOT / 'install.sh').read_text(encoding='utf-8')

    assert 'guard_openclaw_sessions.py' in content
    assert content.index('guard_openclaw_sessions.py') < content.index('sync_from_openclaw_runtime.py')
