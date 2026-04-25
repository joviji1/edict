import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path('/root/.openclaw/workspace/edict')
SCRIPT = ROOT / 'scripts' / 'kanban_update.py'


class KanbanAutopsyCLITest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.base = Path(self.tmpdir.name)
        (self.base / 'data').mkdir(parents=True, exist_ok=True)
        (self.base / 'scripts').mkdir(parents=True, exist_ok=True)
        (self.base / 'edict' / 'backend' / 'app' / 'models').mkdir(parents=True, exist_ok=True)
        # 让脚本的动态状态机解析有输入
        source_task_py = ROOT / 'edict' / 'backend' / 'app' / 'models' / 'task.py'
        (self.base / 'edict' / 'backend' / 'app' / 'models' / 'task.py').write_text(source_task_py.read_text())
        refresh = self.base / 'scripts' / 'refresh_live_data.py'
        refresh.write_text('print("refresh skipped")\n')
        tasks = [
            {
                'id': 'TEST-AUTOPSY-001',
                'title': '测试 autopsy 生成',
                'official': '工部尚书',
                'org': '兵部',
                'state': 'Blocked',
                'now': '任务多次停滞，等待验尸',
                'eta': '-',
                'block': '模型接口连续超时',
                'output': '',
                'ac': '',
                'updatedAt': '2026-04-17T00:00:00Z',
                '_scheduler': {
                    'stallReason': 'provider_timeout',
                    'retryCount': 3,
                    'escalationLevel': 2,
                    'lastProgressAt': '2026-04-17T00:00:00Z'
                },
                'flow_log': [
                    {'at': '2026-04-17T00:00:00Z', 'from': '尚书省', 'to': '兵部', 'remark': '派发执行'},
                    {'at': '2026-04-17T00:10:00Z', 'from': '兵部', 'to': '尚书省', 'remark': '停滞，第一次催办'},
                ],
                'progress_log': [
                    {'at': '2026-04-17T00:05:00Z', 'agent': 'bingbu', 'text': '调用 provider 时报超时', 'todos': []}
                ],
                'todos': []
            }
        ]
        (self.base / 'data' / 'tasks_source.json').write_text(json.dumps(tasks, ensure_ascii=False))

    def tearDown(self):
        self.tmpdir.cleanup()

    def _run(self, *args):
        env = os.environ.copy()
        env['EDICT_HOME'] = str(self.base)
        env['OPENCLAW_AGENT_ID'] = 'shangshu'
        return subprocess.run(
            ['python3', str(SCRIPT), *args],
            cwd=str(ROOT / 'scripts'),
            env=env,
            capture_output=True,
            text=True,
        )

    def test_autopsy_command_creates_report_and_updates_task(self):
        result = self._run('autopsy', 'TEST-AUTOPSY-001')
        self.assertEqual(result.returncode, 0, msg=result.stderr + result.stdout)

        report_path = self.base / 'data' / 'autopsy' / 'TEST-AUTOPSY-001.md'
        self.assertTrue(report_path.exists())
        report = report_path.read_text()
        self.assertIn('provider_timeout', report)
        self.assertIn('retryCount: 3', report)
        self.assertIn('escalationLevel: 2', report)

        tasks = json.loads((self.base / 'data' / 'tasks_source.json').read_text())
        task = tasks[0]
        self.assertIn('autopsy', task)
        self.assertEqual(task['autopsy']['path'], str(report_path))
        self.assertEqual(task['autopsy']['reason'], 'provider_timeout')


if __name__ == '__main__':
    unittest.main()
