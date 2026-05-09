import importlib.util
import json
import pathlib
from types import SimpleNamespace

ROOT = pathlib.Path('/root/.openclaw/workspace/edict')
SCRIPT = ROOT / 'edict' / 'scripts' / 'kanban_update_edict.py'

spec = importlib.util.spec_from_file_location('kanban_update_edict', SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class _StubResponse:
    def __init__(self, status=200, body='{}'):
        self.status = status
        self._body = body.encode('utf-8')

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _LegacyStub:
    def __init__(self):
        self.progress_calls = []
        self.todo_calls = []

    def cmd_progress(self, *args):
        self.progress_calls.append(args)

    def cmd_todo(self, *args):
        self.todo_calls.append(args)



def test_api_available_rejects_generic_status_ok_health(monkeypatch):
    def fake_urlopen(req, timeout=2):
        return _StubResponse(200, json.dumps({'status': 'ok'}))

    monkeypatch.setattr('urllib.request.urlopen', fake_urlopen)
    monkeypatch.setattr(mod, 'EDICT_MODE', 'auto')
    assert mod._api_available() is False



def test_cmd_progress_falls_back_when_api_post_fails(monkeypatch):
    legacy = _LegacyStub()
    monkeypatch.setattr(mod, '_check_api', lambda: True)
    monkeypatch.setattr(mod, '_api_post', lambda path, data: None)
    monkeypatch.setattr(mod, '_api_put', lambda path, data: None)
    monkeypatch.setattr(mod, '_fallback_json', lambda: legacy)

    mod.cmd_progress('JJC-TEST-001', '正在推进', '1.调研✅|2.编码🔄')

    assert len(legacy.progress_calls) == 1
    args = legacy.progress_calls[0]
    assert args[0] == 'JJC-TEST-001'
    assert args[1] == '正在推进'



def test_cmd_todo_falls_back_when_api_post_fails(monkeypatch):
    legacy = _LegacyStub()
    monkeypatch.setattr(mod, '_check_api', lambda: True)
    monkeypatch.setattr(mod, '_api_post', lambda path, data: None)
    monkeypatch.setattr(mod, '_fallback_json', lambda: legacy)

    mod.cmd_todo('JJC-TEST-002', '1', '实现接口', 'in-progress', '先写接口')

    assert len(legacy.todo_calls) == 1
    args = legacy.todo_calls[0]
    assert args[:4] == ('JJC-TEST-002', '1', '实现接口', 'in-progress')



def test_fallback_json_loads_root_scripts_kanban_update(monkeypatch):
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

    expected = ROOT / 'scripts' / 'kanban_update.py'
    monkeypatch.setattr(pathlib.Path, 'exists', lambda self: self == expected)
    monkeypatch.setattr('importlib.util.spec_from_file_location', fake_spec_from_file_location)
    monkeypatch.setattr('importlib.util.module_from_spec', fake_module_from_spec)

    loaded = mod._fallback_json()

    assert calls[0] == expected
    assert getattr(loaded, 'loaded', False) is True



def test_fallback_json_imports_real_legacy_module_with_local_deps():
    loaded = mod._fallback_json()

    assert loaded is not None
    assert pathlib.Path(loaded.__file__) == ROOT / 'scripts' / 'kanban_update_legacy.py'
    assert hasattr(loaded, 'cmd_progress')
    assert hasattr(loaded, 'cmd_todo')
