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


def test_build_task_infers_zhongshu_state_from_kanban_transition(tmp_path):
    now_ms = int(time.time() * 1000)
    transcript = tmp_path / 'dispatch-state.jsonl'
    transcript.write_text(
        '\n'.join([
            '{"timestamp":"2026-05-02T09:10:33Z","message":{"role":"user","content":[{"type":"text","text":"📜 皇上旨意需要你处理\\n任务ID: 4455998e-77ae-446c-b786-f2c476ac94ff\\n旨意: probe"}]}}',
            '{"timestamp":"2026-05-02T09:14:53Z","message":{"role":"toolResult","toolName":"kanban","content":[{"type":"text","text":"17:14:53 [kanban] ✅ 4455998e-77ae-446c-b786-f2c476ac94ff 状态更新: Taizi → Zhongshu"}]}}',
            '{"timestamp":"2026-05-02T09:34:53Z","message":{"role":"assistant","content":[{"type":"text","text":"[[reply_to_current]] 已在中书省，无需重复流转。"}]}}'
        ]),
        encoding='utf-8',
    )
    row = {
        'sessionId': '353b313b-bb1b-443f-9034-a8e44a804f02',
        'updatedAt': now_ms - 30_000,
        'origin': {'label': 'agent:taizi:edict-dispatch'},
        'sessionFile': str(transcript),
    }

    task = runtime.build_task('taizi', 'agent:taizi:edict-dispatch', row, now_ms)
    assert task['state'] == 'Zhongshu'
    assert task['org'] == '中书省'
