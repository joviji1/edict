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


def test_should_keep_real_main_session_review_task():
    task, now_ms = make_task(session_key='agent:zhongshu:main', title='中书省会话', state='Review', age_sec=120)
    assert runtime.should_keep_runtime_task(task, now_ms) is True


def test_should_drop_heartbeat_main_session():
    task, now_ms = make_task(title='heartbeat', session_key='agent:taizi:main', state='Review', age_sec=30)
    assert runtime.should_keep_runtime_task(task, now_ms) is False


def test_should_drop_non_blocked_feishu_context_session():
    task, now_ms = make_task(title='user:ou_xxx', session_key='agent:taizi:feishu:direct:ou_xxx', state='Review', age_sec=90)
    assert runtime.should_keep_runtime_task(task, now_ms) is False


def test_should_keep_blocked_background_and_feishu_sessions():
    cron_task, now_ms = make_task(title='太子定时任务', session_key='agent:taizi:cron:job-1', state='Blocked', age_sec=120)
    feishu_task, _ = make_task(task_id='OC-feishu', title='oc_demo', session_key='agent:taizi:feishu:group:oc_demo', state='Blocked', age_sec=120)
    assert runtime.should_keep_runtime_task(cron_task, now_ms) is True
    assert runtime.should_keep_runtime_task(feishu_task, now_ms) is True
