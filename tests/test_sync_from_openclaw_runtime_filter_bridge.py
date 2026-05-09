import importlib.util
import pathlib
import sys
import time

ROOT = pathlib.Path('/root/.openclaw/workspace/edict')
SCRIPTS = ROOT / 'scripts'
sys.path.insert(0, str(SCRIPTS))

spec = importlib.util.spec_from_file_location('sync_from_openclaw_runtime', SCRIPTS / 'sync_from_openclaw_runtime.py')
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)


def test_should_keep_runtime_task_for_recent_edict_dispatch_governance_state():
    now_ms = int(time.time() * 1000)
    task = {
        'id': '4455998e-77ae-446c-b786-f2c476ac94ff',
        'title': 'agent:taizi:edict-dispatch',
        'state': 'Zhongshu',
        'org': '中书省',
        'activity': [{'kind': 'assistant', 'text': '已在中书省，无需重复流转。'}],
        'output': '/root/.openclaw/agents/taizi/sessions/353b313b-bb1b-443f-9034-a8e44a804f02.jsonl',
        'sourceMeta': {
            'sessionKey': 'agent:taizi:edict-dispatch',
            'sessionId': '353b313b-bb1b-443f-9034-a8e44a804f02',
            'updatedAt': now_ms - 90_000,
            'taskId': '4455998e-77ae-446c-b786-f2c476ac94ff',
        },
    }
    assert runtime.should_keep_runtime_task(task, now_ms) is True
