import json
import importlib.util
import sys
from pathlib import Path


ROOT = Path('/root/.openclaw/workspace/edict')
SCRIPTS_DIR = ROOT / 'scripts'
SCRIPT_PATH = SCRIPTS_DIR / 'apply_model_changes.py'


def _load_apply_model_changes():
    sys.path.insert(0, str(SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location('apply_model_changes', SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_apply_model_changes_persists_explicit_fallback_override(tmp_path, monkeypatch):
    apply_model_changes = _load_apply_model_changes()

    cfg = {
        'agents': {
            'defaults': {'model': {'primary': 'faker/gpt-5.4', 'fallbacks': ['longcat/LongCat-Flash-Chat']}},
            'list': [
                {'id': 'taizi', 'workspace': str(tmp_path / 'ws-taizi')},
            ],
        }
    }

    openclaw_cfg = tmp_path / 'openclaw.json'
    openclaw_cfg.write_text(json.dumps(cfg, ensure_ascii=False), encoding='utf-8')
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    pending_path = data_dir / 'pending_model_changes.json'
    pending_path.write_text(json.dumps([
        {'agentId': 'taizi', 'model': 'longcat/LongCat-Flash-Chat'}
    ], ensure_ascii=False), encoding='utf-8')

    monkeypatch.setattr(apply_model_changes, 'OPENCLAW_CFG', openclaw_cfg)
    monkeypatch.setattr(apply_model_changes, 'DATA', data_dir)
    monkeypatch.setattr(apply_model_changes, 'PENDING', pending_path)
    monkeypatch.setattr(apply_model_changes, 'CHANGE_LOG', data_dir / 'model_change_log.json')

    class DummyResult:
        returncode = 0

    def fake_run(cmd, capture_output=None, text=None, timeout=None):
        return DummyResult()

    monkeypatch.setattr(apply_model_changes.subprocess, 'run', fake_run)

    apply_model_changes.main()

    updated_cfg = json.loads(openclaw_cfg.read_text(encoding='utf-8'))
    taizi = next(agent for agent in updated_cfg['agents']['list'] if agent['id'] == 'taizi')
    assert taizi['model'] == 'longcat/LongCat-Flash-Chat'

    last_result = json.loads((data_dir / 'last_model_change_result.json').read_text(encoding='utf-8'))
    assert last_result['applied'][0]['oldModel'] == 'faker/gpt-5.4'
    assert last_result['applied'][0]['newModel'] == 'longcat/LongCat-Flash-Chat'
    assert last_result['applied'][0].get('writeSkipped') is not True
