import importlib.util
import os
import pathlib
import sys

ROOT = pathlib.Path('/root/.openclaw/workspace/edict')
SCRIPTS = ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

ROOT_SCRIPT = ROOT / 'scripts' / 'kanban_update.py'
LEGACY_SCRIPT = ROOT / 'scripts' / 'kanban_update_legacy.py'
WRAPPER_SCRIPT = ROOT / 'edict' / 'scripts' / 'kanban_update_edict.py'


def _load_module(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_legacy_main_dispatches_create(monkeypatch):
    legacy = _load_module('kanban_update_legacy_entry', LEGACY_SCRIPT)
    called = {}

    def fake_cmd_create(*args):
        called['args'] = args

    monkeypatch.setattr(legacy, 'cmd_create', fake_cmd_create)

    legacy.main(['create', 'JJC-T-001', '标题', 'Zhongshu', '中书省', '中书令'])

    assert called['args'] == ('JJC-T-001', '标题', 'Zhongshu', '中书省', '中书令', None)


def test_wrapper_main_dispatches_progress(monkeypatch):
    wrapper = _load_module('kanban_update_edict_entry', WRAPPER_SCRIPT)
    called = {}

    def fake_cmd_progress(*args, **kwargs):
        called['args'] = args
        called['kwargs'] = kwargs

    monkeypatch.setattr(wrapper, 'cmd_progress', fake_cmd_progress)

    wrapper.main(['progress', 'JJC-T-002', '推进中', '1.调研✅', '--tokens', '12', '--cost', '0.3', '--elapsed', '9'])

    assert called['args'] == ('JJC-T-002', '推进中', '1.调研✅')
    assert called['kwargs'] == {'tokens': '12', 'cost': '0.3', 'elapsed': '9'}


def test_root_script_is_direct_cli_module():
    root = _load_module('kanban_update_root_entry_default', ROOT_SCRIPT)

    assert hasattr(root, 'cmd_create')
    assert hasattr(root, 'cmd_progress')
    assert hasattr(root, '_check_permission')
    assert not hasattr(root, '_load_legacy_module')
    assert not hasattr(root, '_load_wrapper_module')


def test_wrapper_keeps_api_json_compat_layer_contract():
    wrapper = _load_module('kanban_update_root_entry_api', WRAPPER_SCRIPT)

    assert hasattr(wrapper, '_fallback_json')
    assert hasattr(wrapper, 'cmd_progress')
    assert getattr(wrapper, 'EDICT_MODE', None) in {'auto', 'api', 'json'}
