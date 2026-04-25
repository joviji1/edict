"""tests for scripts/kanban_update.py"""
import json, pathlib, sys

# Ensure scripts/ is importable
SCRIPTS = pathlib.Path(__file__).resolve().parent.parent / 'scripts'
sys.path.insert(0, str(SCRIPTS))

import kanban_update as kb


def test_create_and_get(tmp_path):
    """kanban create + get round-trip."""
    tasks_file = tmp_path / 'tasks_source.json'
    tasks_file.write_text('[]')

    # Patch TASKS_FILE
    original = kb.TASKS_FILE
    kb.TASKS_FILE = tasks_file
    try:
        kb.cmd_create('TEST-001', '测试任务创建和查询功能验证', 'Inbox', '工部', '工部尚书')
        tasks = json.loads(tasks_file.read_text())
        assert any(t.get('id') == 'TEST-001' for t in tasks)
        t = next(t for t in tasks if t['id'] == 'TEST-001')
        assert t['title'] == '测试任务创建和查询功能验证'
        assert t['state'] == 'Inbox'
        assert t['org'] == '工部'
    finally:
        kb.TASKS_FILE = original


def test_move_state(tmp_path):
    """kanban move changes task state."""
    tasks_file = tmp_path / 'tasks_source.json'
    tasks_file.write_text(json.dumps([
        {'id': 'T-1', 'title': 'test', 'state': 'Inbox'}
    ]))

    original = kb.TASKS_FILE
    kb.TASKS_FILE = tasks_file
    try:
        kb.cmd_state('T-1', 'Doing')
        tasks = json.loads(tasks_file.read_text())
        assert tasks[0]['state'] == 'Doing'
    finally:
        kb.TASKS_FILE = original


def test_block_and_unblock(tmp_path):
    """kanban block/unblock round-trip."""
    tasks_file = tmp_path / 'tasks_source.json'
    tasks_file.write_text(json.dumps([
        {'id': 'T-2', 'title': 'blocker test', 'state': 'Doing'}
    ]))

    original = kb.TASKS_FILE
    kb.TASKS_FILE = tasks_file
    try:
        kb.cmd_block('T-2', '等待依赖')
        tasks = json.loads(tasks_file.read_text())
        assert tasks[0]['state'] == 'Blocked'
        assert tasks[0]['block'] == '等待依赖'
    finally:
        kb.TASKS_FILE = original


def test_flow_log(tmp_path):
    """cmd_flow appends a flow_log entry."""
    tasks_file = tmp_path / 'tasks_source.json'
    tasks_file.write_text(json.dumps([
        {'id': 'T-3', 'title': 'flow test', 'state': 'Zhongshu', 'flow_log': []}
    ]))

    original = kb.TASKS_FILE
    kb.TASKS_FILE = tasks_file
    try:
        kb.cmd_flow('T-3', '中书省', '门下省', '规划方案提交审核')
        tasks = json.loads(tasks_file.read_text())
        t = tasks[0]
        assert len(t['flow_log']) == 1
        assert t['flow_log'][0]['from'] == '中书省'
        assert t['flow_log'][0]['to'] == '门下省'
    finally:
        kb.TASKS_FILE = original


def test_done(tmp_path):
    """cmd_done marks task as Done with output and flow_log entry."""
    tasks_file = tmp_path / 'tasks_source.json'
    tasks_file.write_text(json.dumps([
        {'id': 'T-4', 'title': 'done test', 'state': 'Doing', 'org': '兵部', 'flow_log': []}
    ]))

    original = kb.TASKS_FILE
    kb.TASKS_FILE = tasks_file
    try:
        kb.cmd_done('T-4', '/tmp/output.md', '功能已全部实现')
        tasks = json.loads(tasks_file.read_text())
        t = tasks[0]
        assert t['state'] == 'Done'
        assert t['output'] == '/tmp/output.md'
        assert t['now'] == '功能已全部实现'
        assert any('✅ 完成' in e.get('remark', '') for e in t['flow_log'])
    finally:
        kb.TASKS_FILE = original


def test_progress(tmp_path):
    """cmd_progress updates now text and appends to progress_log."""
    tasks_file = tmp_path / 'tasks_source.json'
    tasks_file.write_text(json.dumps([
        {'id': 'T-5', 'title': 'progress test', 'state': 'Doing', 'org': '工部'}
    ]))

    original = kb.TASKS_FILE
    kb.TASKS_FILE = tasks_file
    try:
        kb.cmd_progress('T-5', '正在实现核心模块', '已完成需求分析✅|正在写代码🔄|待测试')
        tasks = json.loads(tasks_file.read_text())
        t = tasks[0]
        assert t['now'] == '正在实现核心模块'
        assert len(t.get('progress_log', [])) == 1
        todos = t.get('todos', [])
        assert len(todos) == 3
        statuses = {td['title']: td['status'] for td in todos}
        assert statuses['已完成需求分析'] == 'completed'
        assert statuses['正在写代码'] == 'in-progress'
        assert statuses['待测试'] == 'not-started'
    finally:
        kb.TASKS_FILE = original


def test_todo(tmp_path):
    """cmd_todo adds and updates sub-tasks."""
    tasks_file = tmp_path / 'tasks_source.json'
    tasks_file.write_text(json.dumps([
        {'id': 'T-6', 'title': 'todo test', 'state': 'Doing'}
    ]))

    original = kb.TASKS_FILE
    kb.TASKS_FILE = tasks_file
    try:
        kb.cmd_todo('T-6', '1', '实现登录接口', 'in-progress')
        kb.cmd_todo('T-6', '2', '编写测试', 'not-started')
        kb.cmd_todo('T-6', '1', '', 'completed')  # 更新第1条为完成
        tasks = json.loads(tasks_file.read_text())
        t = tasks[0]
        todos = {td['id']: td for td in t.get('todos', [])}
        assert todos['1']['status'] == 'completed'
        assert todos['2']['status'] == 'not-started'
    finally:
        kb.TASKS_FILE = original


def _patch_kb_paths(tmp_path):
    """Point kanban_update data paths at a temp sandbox."""
    original = {
        'TASKS_FILE': kb.TASKS_FILE,
        'MEMORY_DIR': kb.MEMORY_DIR,
        'TASK_MEMORY_DIR': kb.TASK_MEMORY_DIR,
        'SHARED_MEMORY_FILE': kb.SHARED_MEMORY_FILE,
        'AUTOPSY_DIR': kb.AUTOPSY_DIR,
    }
    kb.TASKS_FILE = tmp_path / 'tasks_source.json'
    kb.MEMORY_DIR = tmp_path / 'agent_memory'
    kb.TASK_MEMORY_DIR = tmp_path / 'task_memory'
    kb.SHARED_MEMORY_FILE = tmp_path / 'shared_memory.json'
    kb.AUTOPSY_DIR = tmp_path / 'autopsy'
    return original


def _restore_kb_paths(original):
    for key, value in original.items():
        setattr(kb, key, value)


def test_done_auto_extracts_memory(tmp_path, monkeypatch):
    """cmd_done should automatically distill terminal experience into memory stores."""
    monkeypatch.setenv('OPENCLAW_AGENT_ID', 'gongbu')
    original = _patch_kb_paths(tmp_path)
    kb.TASKS_FILE.write_text(json.dumps([
        {
            'id': 'T-MEM-DONE', 'title': '自动记忆完成任务测试', 'state': 'Doing',
            'org': '工部', 'flow_log': [],
            'progress_log': [{'agent': 'gongbu', 'text': '完成核心实现和回归验证'}],
            'todos': [{'id': '1', 'title': '补自动记忆测试', 'status': 'completed'}],
        }
    ]), encoding='utf-8')
    try:
        kb.cmd_done('T-MEM-DONE', '/tmp/output.md', '功能已全部实现并通过验证')
        tasks = json.loads(kb.TASKS_FILE.read_text(encoding='utf-8'))
        task = tasks[0]
        assert task['memory_extracted']['done']['agent'] == 'gongbu'

        agent_mem = json.loads((kb.MEMORY_DIR / 'gongbu.json').read_text(encoding='utf-8'))
        assert agent_mem['memories'][0]['source_task'] == 'T-MEM-DONE'
        assert '功能已全部实现' in agent_mem['memories'][0]['content']

        task_mem = json.loads((kb.TASK_MEMORY_DIR / 'T-MEM-DONE.json').read_text(encoding='utf-8'))
        decisions = task_mem['context_chain'][0]['key_decisions']
        assert any('验收结论' in d for d in decisions)
    finally:
        _restore_kb_paths(original)


def test_block_auto_extracts_memory_once(tmp_path, monkeypatch):
    """cmd_block should write recovery warning once and be idempotent."""
    monkeypatch.setenv('OPENCLAW_AGENT_ID', 'xingbu')
    original = _patch_kb_paths(tmp_path)
    kb.TASKS_FILE.write_text(json.dumps([
        {'id': 'T-MEM-BLOCK', 'title': '自动记忆阻塞任务测试', 'state': 'Doing', 'org': '刑部'}
    ]), encoding='utf-8')
    try:
        kb.cmd_block('T-MEM-BLOCK', '等待外部 API 权限')
        kb.cmd_block('T-MEM-BLOCK', '等待外部 API 权限')
        task_mem = json.loads((kb.TASK_MEMORY_DIR / 'T-MEM-BLOCK.json').read_text(encoding='utf-8'))
        assert len(task_mem['context_chain']) == 1
        assert '等待外部 API 权限' in ','.join(task_mem['context_chain'][0]['warnings'])
    finally:
        _restore_kb_paths(original)


def test_autopsy_auto_extracts_failure_memory(tmp_path, monkeypatch):
    """cmd_autopsy should feed structured failure reason back into memory."""
    monkeypatch.setenv('OPENCLAW_AGENT_ID', 'xingbu')
    original = _patch_kb_paths(tmp_path)
    kb.TASKS_FILE.write_text(json.dumps([
        {
            'id': 'T-MEM-AUTOPSY', 'title': '自动记忆验尸任务测试', 'state': 'Blocked',
            'org': '刑部', 'block': 'provider timeout',
            '_scheduler': {'stallReason': 'provider_timeout'},
            'progress_log': [{'agent': 'xingbu', 'text': '模型调用超时'}],
        }
    ]), encoding='utf-8')
    try:
        kb.cmd_autopsy('T-MEM-AUTOPSY')
        tasks = json.loads(kb.TASKS_FILE.read_text(encoding='utf-8'))
        assert tasks[0]['memory_extracted']['autopsy']['agent'] == 'xingbu'
        task_mem = json.loads((kb.TASK_MEMORY_DIR / 'T-MEM-AUTOPSY.json').read_text(encoding='utf-8'))
        assert any('provider_timeout' in d for d in task_mem['context_chain'][0]['key_decisions'])
    finally:
        _restore_kb_paths(original)


def test_progress_log_capped(tmp_path):
    """progress_log should not exceed MAX_PROGRESS_LOG entries."""
    tasks_file = tmp_path / 'tasks_source.json'
    tasks_file.write_text(json.dumps([
        {'id': 'T-7', 'title': '日志上限测试', 'state': 'Doing', 'org': '礼部'}
    ]))

    original = kb.TASKS_FILE
    kb.TASKS_FILE = tasks_file
    try:
        for i in range(kb.MAX_PROGRESS_LOG + 5):
            kb.cmd_progress('T-7', f'第{i}次进展汇报内容，描述当前执行情况')
        tasks = json.loads(tasks_file.read_text())
        t = tasks[0]
        assert len(t.get('progress_log', [])) == kb.MAX_PROGRESS_LOG
    finally:
        kb.TASKS_FILE = original
