import importlib.util
import json
from pathlib import Path

ROOT = Path('/root/.openclaw/workspace/edict')
SCRIPT = ROOT / 'scripts' / 'smoke_observability_auth.py'


def _load_script():
    spec = importlib.util.spec_from_file_location('smoke_observability_auth', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class StubResponse:
    def __init__(self, status, payload):
        self.status = status
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self._payload).encode('utf-8')


def test_smoke_observability_auth_uses_bearer_and_redacts_gateway_token(monkeypatch):
    mod = _load_script()
    calls = []

    def fake_urlopen(req, timeout=0):
        calls.append({
            'url': req.full_url,
            'method': req.get_method(),
            'headers': dict(req.header_items()),
            'data': req.data,
            'timeout': timeout,
        })
        if req.full_url.endswith('/api/auth/login'):
            assert b'secret-password' in req.data
            return StubResponse(200, {'ok': True, 'token': 'live-token-secret'})
        if '/api/observability-panel?' in req.full_url:
            assert dict(req.header_items()).get('Authorization') == 'Bearer live-token-secret'
            return StubResponse(200, {
                'ok': True,
                'stats': {'tasks': 2},
                'sources': {'consistent': True, 'backendDb': {'count': 2}},
                'tokens': {'gatewayAuth': {'configured': True, 'redactedToken': '645…331'}},
            })
        raise AssertionError(req.full_url)

    monkeypatch.setattr(mod.urllib.request, 'urlopen', fake_urlopen)

    result = mod.run_smoke('secret-password', base_url='http://127.0.0.1:7892', query='token', limit=3)

    assert result['ok'] is True
    assert result['httpStatus'] == 200
    assert result['stats']['tasks'] == 2
    assert result['sources']['consistent'] is True
    assert result['gatewayAuth']['redactedToken'] == '645…331'
    assert 'live-token-secret' not in json.dumps(result, ensure_ascii=False)
    assert calls[0]['method'] == 'POST'
    assert calls[1]['method'] == 'GET'


def test_smoke_observability_auth_requires_password():
    mod = _load_script()
    assert mod.main(['--base-url', 'http://127.0.0.1:7892']) == 2
