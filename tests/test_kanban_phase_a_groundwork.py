import importlib.util
import pathlib
import sys
from types import SimpleNamespace

ROOT = pathlib.Path('/root/.openclaw/workspace/edict')
SCRIPTS = ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

LEGACY_SCRIPT = ROOT / 'scripts' / 'kanban_update_legacy.py'
WRAPPER_SCRIPT = ROOT / 'edict' / 'scripts' / 'kanban_update_edict.py'


def _load_module(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_legacy_kanban_module_exists_and_exports_core_commands():
    assert LEGACY_SCRIPT.exists(), 'Phase A groundwork requires scripts/kanban_update_legacy.py'

    mod = _load_module('kanban_update_legacy', LEGACY_SCRIPT)

    for cmd in ('cmd_create', 'cmd_state', 'cmd_flow', 'cmd_done', 'cmd_progress', 'cmd_todo', 'cmd_autopsy', 'cmd_confirm'):
        assert hasattr(mod, cmd), f'missing legacy command: {cmd}'


def test_wrapper_fallback_prefers_legacy_module_when_present(monkeypatch):
    wrapper = _load_module('kanban_update_edict_phase_a', WRAPPER_SCRIPT)
    calls = []

    class _Loader:
        def exec_module(self, module):
            calls.append('exec')
            module.loaded = True

    class _Spec:
        loader = _Loader()

    def fake_spec_from_file_location(name, path):
        calls.append(pathlib.Path(path))
        return _Spec()

    def fake_module_from_spec(spec):
        return SimpleNamespace()

    expected = ROOT / 'scripts' / 'kanban_update_legacy.py'
    monkeypatch.setattr(pathlib.Path, 'exists', lambda self: self == expected)
    monkeypatch.setattr('importlib.util.spec_from_file_location', fake_spec_from_file_location)
    monkeypatch.setattr('importlib.util.module_from_spec', fake_module_from_spec)

    loaded = wrapper._fallback_json()

    assert calls[0] == expected
    assert getattr(loaded, 'loaded', False) is True
