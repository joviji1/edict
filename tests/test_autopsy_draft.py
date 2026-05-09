import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'autopsy_draft.py'


class AutopsyDraftCLITest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.base = Path(self.tmpdir.name)
        (self.base / 'data').mkdir(parents=True, exist_ok=True)
        (self.base / 'scripts').mkdir(parents=True, exist_ok=True)
        (self.base / 'edict' / 'backend' / 'app' / 'models').mkdir(parents=True, exist_ok=True)
        source_task_py = ROOT / 'edict' / 'backend' / 'app' / 'models' / 'task.py'
        (self.base / 'edict' / 'backend' / 'app' / 'models' / 'task.py').write_text(source_task_py.read_text(), encoding='utf-8')
        tasks = [
            {
                'id': 'TEST-DRAFT-001',
                'title': '测试旁路验尸草稿',
                'org': '兵部',
                'state': 'Blocked',
                'now': '任务多次停滞，等待人工判断',
                'block': '模型接口连续超时',
                'updatedAt': '2026-04-17T00:00:00Z',
                '_scheduler': {
                    'retryCount': 3,
                    'escalationLevel': 2,
                    'lastProgressAt': '2026-04-17T00:00:00Z',
                },
                'flow_log': [
                    {'at': '2026-04-17T00:00:00Z', 'from': '尚书省', 'to': '兵部', 'remark': '派发执行'},
                    {'at': '2026-04-17T00:10:00Z', 'from': '兵部', 'to': '尚书省', 'remark': 'provider timeout，第一次催办'},
                ],
                'progress_log': [
                    {'at': '2026-04-17T00:05:00Z', 'agent': 'bingbu', 'text': '调用 provider 时报 timeout', 'todos': []}
                ],
                'todos': []
            }
        ]
        self.tasks_file = self.base / 'data' / 'tasks_source.json'
        self.tasks_file.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding='utf-8')
        self.original_tasks_text = self.tasks_file.read_text(encoding='utf-8')

    def tearDown(self):
        self.tmpdir.cleanup()

    def _run(self, *args):
        env = os.environ.copy()
        env['EDICT_HOME'] = str(self.base)
        return subprocess.run(
            ['python3', str(SCRIPT), *args],
            cwd=str(ROOT / 'scripts'),
            env=env,
            capture_output=True,
            text=True,
        )

    def test_generates_markdown_draft_without_mutating_tasks_source(self):
        out_dir = self.base / 'isolation' / 'danghuangshang' / 'autopsy-drafts'
        result = self._run('TEST-DRAFT-001', '--output-dir', str(out_dir))
        self.assertEqual(result.returncode, 0, msg=result.stderr + result.stdout)

        report_path = out_dir / 'TEST-DRAFT-001.md'
        self.assertTrue(report_path.exists())
        report = report_path.read_text(encoding='utf-8')
        self.assertIn('provider_timeout', report)
        self.assertIn('置信度', report)
        self.assertIn('证据来源', report)
        self.assertIn('不自动写回任务', report)

        payload = json.loads(result.stdout)
        self.assertEqual(payload['task_id'], 'TEST-DRAFT-001')
        self.assertEqual(payload['reason'], 'provider_timeout')
        self.assertEqual(payload['mutated_task_source'], False)
        self.assertEqual(payload['report_path'], str(report_path))

        self.assertEqual(self.tasks_file.read_text(encoding='utf-8'), self.original_tasks_text)
    def test_accepts_explicit_reason_without_mutating_tasks_source(self):
        out_dir = self.base / 'isolation' / 'danghuangshang' / 'autopsy-drafts'
        result = self._run('TEST-DRAFT-001', '--reason', 'waiting_human', '--output-dir', str(out_dir), '--format', 'json')
        self.assertEqual(result.returncode, 0, msg=result.stderr + result.stdout)

        payload = json.loads(result.stdout)
        self.assertEqual(payload['reason'], 'waiting_human')
        self.assertEqual(payload['evidence_sources'], ['cli.--reason'])
        self.assertEqual(payload['mutated_task_source'], False)
        self.assertEqual(self.tasks_file.read_text(encoding='utf-8'), self.original_tasks_text)


if __name__ == '__main__':
    unittest.main()
