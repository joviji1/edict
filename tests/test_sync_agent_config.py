import json
import importlib.util
import sys
from copy import deepcopy
from pathlib import Path


def _load_sync_agent_config():
    root = Path(__file__).resolve().parents[1]
    scripts_dir = root / "scripts"
    script_path = scripts_dir / "sync_agent_config.py"
    sys.path.insert(0, str(scripts_dir))
    spec = importlib.util.spec_from_file_location("sync_agent_config", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_sync_agent_config_accepts_allow_agents_key(tmp_path, monkeypatch):
    sync_agent_config = _load_sync_agent_config()

    cfg = {
        "agents": {
            "defaults": {"model": "openai/gpt-4o"},
            "list": [
                {
                    "id": "taizi",
                    "workspace": str(tmp_path / "ws-taizi"),
                    "allowAgents": ["zhongshu"]
                }
            ]
        }
    }

    cfg_path = tmp_path / "openclaw.json"
    cfg_path.write_text(json.dumps(cfg, ensure_ascii=False))

    monkeypatch.setattr(sync_agent_config, "OPENCLAW_CFG", cfg_path)
    monkeypatch.setattr(sync_agent_config, "DATA", tmp_path / "data")

    sync_agent_config.main()

    out = json.loads((tmp_path / "data" / "agent_config.json").read_text())
    taizi = next(agent for agent in out["agents"] if agent["id"] == "taizi")
    assert taizi["allowAgents"] == ["zhongshu"]


def test_sync_agent_config_includes_default_agents_and_discovers_skills(tmp_path, monkeypatch):
    sync_agent_config = _load_sync_agent_config()

    cfg = {
        "agents": {
            "defaults": {"model": "openai/gpt-4o"},
            "list": [
                {
                    "id": "taizi",
                    "workspace": str(tmp_path / ".openclaw" / "workspace-taizi"),
                    "allowAgents": ["zhongshu"]
                }
            ]
        }
    }

    home = tmp_path
    openclaw_root = home / ".openclaw"
    (openclaw_root / "workspace-zaochao" / "skills" / "weather").mkdir(parents=True)
    (openclaw_root / "workspace-zaochao" / "skills" / "weather" / "SKILL.md").write_text(
        "---\nname: weather\ndescription: 朝报天气\n---\n朝报天气技能\n",
        encoding="utf-8",
    )
    (openclaw_root / "workspace-libu_hr" / "skills" / "recruiting").mkdir(parents=True)
    (openclaw_root / "workspace-libu_hr" / "skills" / "recruiting" / "SKILL.md").write_text(
        "---\nname: recruiting\ndescription: 招贤纳士\n---\n礼部人事技能\n",
        encoding="utf-8",
    )

    cfg_path = tmp_path / "openclaw.json"
    cfg_path.write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")

    monkeypatch.setattr(sync_agent_config, "OPENCLAW_CFG", cfg_path)
    monkeypatch.setattr(sync_agent_config, "DATA", tmp_path / "data")
    monkeypatch.setattr(Path, "home", lambda: home)

    sync_agent_config.main()

    out = json.loads((tmp_path / "data" / "agent_config.json").read_text(encoding="utf-8"))
    agents = {agent["id"]: agent for agent in out["agents"]}

    assert "zaochao" in agents
    assert "libu_hr" in agents
    assert [s["name"] for s in agents["zaochao"]["skills"]] == ["weather"]
    assert [s["name"] for s in agents["libu_hr"]["skills"]] == ["recruiting"]


def _load_apply_model_changes():
    root = Path(__file__).resolve().parents[1]
    scripts_dir = root / "scripts"
    script_path = scripts_dir / "apply_model_changes.py"
    sys.path.insert(0, str(scripts_dir))
    spec = importlib.util.spec_from_file_location("apply_model_changes", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_apply_model_changes_persists_agent_model_and_records_result(tmp_path, monkeypatch):
    apply_model_changes = _load_apply_model_changes()

    cfg = {
        "agents": {
            "defaults": {"model": {"primary": "longcat/LongCat-Flash-Chat", "fallbacks": ["faker/gpt-5.4"]}},
            "list": [
                {"id": "taizi", "workspace": str(tmp_path / "ws-taizi")},
                {"id": "zhongshu", "workspace": str(tmp_path / "ws-zhongshu")},
            ],
        }
    }

    openclaw_cfg = tmp_path / "openclaw.json"
    original_cfg = deepcopy(cfg)
    openclaw_cfg.write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    pending_path = data_dir / "pending_model_changes.json"
    pending_path.write_text(json.dumps([
        {"agentId": "taizi", "model": "faker/gpt-5.4"}
    ], ensure_ascii=False), encoding="utf-8")

    monkeypatch.setattr(apply_model_changes, "OPENCLAW_CFG", openclaw_cfg)
    monkeypatch.setattr(apply_model_changes, "DATA", data_dir)
    monkeypatch.setattr(apply_model_changes, "PENDING", pending_path)
    monkeypatch.setattr(apply_model_changes, "CHANGE_LOG", data_dir / "model_change_log.json")

    class DummyResult:
        returncode = 0

    restart_calls = []

    def fake_run(cmd, capture_output=None, text=None, timeout=None):
        restart_calls.append({
            "cmd": cmd,
            "capture_output": capture_output,
            "text": text,
            "timeout": timeout,
        })
        return DummyResult()

    monkeypatch.setattr(apply_model_changes.subprocess, "run", fake_run)

    apply_model_changes.main()

    assert cfg == original_cfg

    last_result = json.loads((data_dir / "last_model_change_result.json").read_text(encoding="utf-8"))
    assert last_result["gatewayRestarted"] is True
    assert last_result["rolledBack"] is False
    assert last_result["applied"][0]["agentId"] == "taizi"
    assert last_result["applied"][0]["oldModel"] == "faker/gpt-5.4"
    assert last_result["applied"][0]["newModel"] == "faker/gpt-5.4"
    assert last_result["applied"][0].get("writeSkipped") is True

    updated_cfg = json.loads(openclaw_cfg.read_text(encoding="utf-8"))
    taizi = next(agent for agent in updated_cfg["agents"]["list"] if agent["id"] == "taizi")
    assert "model" not in taizi

    change_log = json.loads((data_dir / "model_change_log.json").read_text(encoding="utf-8"))
    assert change_log[-1]["agentId"] == "taizi"
    assert change_log[-1]["newModel"] == "faker/gpt-5.4"

    remaining_pending = json.loads(pending_path.read_text(encoding="utf-8"))
    assert remaining_pending == []
    assert restart_calls == [{
        "cmd": ["openclaw", "gateway", "restart"],
        "capture_output": True,
        "text": True,
        "timeout": 30,
    }]
