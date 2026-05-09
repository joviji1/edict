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


def make_task(*, task_id='OC-test', title='中书省会话', state='Review', session_key='agent:zhongshu:main', age_sec=60):
    now_ms = int(time.time() * 1000)
    return {
        'id': task_id,
        'title': title,
        'state': state,
        'sourceMeta': {
            'sessionKey': session_key,
            'updatedAt': now_ms - age_sec * 1000,
        },
    }, now_ms


def test_should_drop_main_session_when_transcript_missing(tmp_path):
    missing = tmp_path / 'missing.jsonl'
    task, now_ms = make_task(session_key='agent:shangshu:main', title='尚书省会话', state='Doing', age_sec=30)
    task['output'] = str(missing)
    task['activity'] = []
    assert runtime.should_keep_runtime_task(task, now_ms) is False



def test_should_drop_trivial_bootstrap_main_session(tmp_path):
    transcript = tmp_path / 'main.jsonl'
    transcript.write_text('{}\n', encoding='utf-8')
    task, now_ms = make_task(session_key='agent:taizi:main', title='太子会话', state='Review', age_sec=30)
    task['output'] = str(transcript)
    task['activity'] = [
        {'kind': 'assistant', 'text': 'HEARTBEAT_OK'},
        {'kind': 'tool', 'text': "Tool 'read' returned: "},
        {'kind': 'user', 'text': 'User: bootstrap...'},
    ]
    assert runtime.should_keep_runtime_task(task, now_ms) is False



def test_should_drop_empty_main_session_even_if_transcript_exists(tmp_path):
    transcript = tmp_path / 'empty.jsonl'
    transcript.write_text('', encoding='utf-8')
    task, now_ms = make_task(session_key='agent:menxia:main', title='门下省会话', state='Doing', age_sec=30)
    task['output'] = str(transcript)
    task['activity'] = []
    assert runtime.should_keep_runtime_task(task, now_ms) is False

def test_should_keep_real_main_session_review_task(tmp_path):
    transcript = tmp_path / 'real-review.jsonl'
    transcript.write_text('{}\n', encoding='utf-8')
    task, now_ms = make_task(session_key='agent:zhongshu:main', title='中书省会话', state='Review', age_sec=120)
    task['output'] = str(transcript)
    task['activity'] = [{'kind': 'assistant', 'text': '正在处理正式任务'}]
    assert runtime.should_keep_runtime_task(task, now_ms) is True



def test_should_keep_real_main_session_next_task_within_24h(tmp_path):
    transcript = tmp_path / 'real-next.jsonl'
    transcript.write_text('{}\n', encoding='utf-8')
    task, now_ms = make_task(session_key='agent:zhongshu:main', title='中书省会话', state='Next', age_sec=3900)
    task['output'] = str(transcript)
    task['activity'] = [{'kind': 'assistant', 'text': '等待后续推进'}]
    assert runtime.should_keep_runtime_task(task, now_ms) is True



def test_should_keep_heartbeat_labeled_main_session_with_real_activity(tmp_path):
    transcript = tmp_path / 'heartbeat-main.jsonl'
    transcript.write_text('{}\n', encoding='utf-8')
    task, now_ms = make_task(title='heartbeat', session_key='agent:taizi:main', state='Review', age_sec=30)
    task['output'] = str(transcript)
    task['activity'] = [{'kind': 'assistant', 'text': '继续处理正式任务'}]
    assert runtime.should_keep_runtime_task(task, now_ms) is True



def test_build_task_masks_heartbeat_label_for_main_session(tmp_path):
    now_ms = int(time.time() * 1000)
    transcript = tmp_path / 'sid-1.jsonl'
    transcript.write_text(
        '{"timestamp":"2026-04-26T10:00:00Z","message":{"role":"assistant","content":[{"type":"text","text":"继续处理正式任务"}]}}\n',
        encoding='utf-8',
    )
    row = {
        'sessionId': 'sid-1',
        'updatedAt': now_ms - 30_000,
        'origin': {'label': 'heartbeat'},
        'sessionFile': str(transcript),
    }
    task = runtime.build_task('taizi', 'agent:taizi:main', row, now_ms)
    assert task['title'] == '太子会话'
    assert runtime.should_keep_runtime_task(task, now_ms) is True


def test_should_drop_non_blocked_feishu_context_session():
    task, now_ms = make_task(title='user:ou_xxx', session_key='agent:taizi:feishu:direct:ou_xxx', state='Review', age_sec=90)
    assert runtime.should_keep_runtime_task(task, now_ms) is False


def test_should_keep_blocked_background_and_feishu_sessions():
    cron_task, now_ms = make_task(title='太子定时任务', session_key='agent:taizi:cron:job-1', state='Blocked', age_sec=120)
    feishu_task, _ = make_task(task_id='OC-feishu', title='oc_demo', session_key='agent:taizi:feishu:group:oc_demo', state='Blocked', age_sec=120)
    assert runtime.should_keep_runtime_task(cron_task, now_ms) is True
    assert runtime.should_keep_runtime_task(feishu_task, now_ms) is True


def test_should_drop_empty_edict_dispatch_session_after_reset():
    task, now_ms = make_task(task_id='OC-taizi-reset', title='太子会话', session_key='agent:taizi:edict-dispatch', state='Doing', age_sec=30)
    task['activity'] = []
    task['sourceMeta']['taskId'] = ''
    assert runtime.should_keep_runtime_task(task, now_ms) is False


def test_should_keep_edict_dispatch_session_with_real_task_signal():
    task, now_ms = make_task(task_id='27efcbbe-631f-40b1-89e0-6dc9ac7a14c7', title='中书省会话', session_key='agent:taizi:edict-dispatch', state='Zhongshu', age_sec=60)
    task['activity'] = [{'kind': 'assistant', 'text': '已在中书省，无需重复流转。'}]
    task['sourceMeta']['taskId'] = '27efcbbe-631f-40b1-89e0-6dc9ac7a14c7'
    assert runtime.should_keep_runtime_task(task, now_ms) is True
