import pathlib
import unittest
import uuid
from unittest.mock import patch

from tests.backend_test_env import bootstrap_backend_test_env


class BackendReviewActionTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        env = bootstrap_backend_test_env('test-backend-review-action.db')
        self._tmpdir = env['tmpdir']
        self.data_dir = env['root'] / 'data'
        self.data_dir.mkdir(exist_ok=True)
        (self.data_dir / 'morning_brief_config.json').write_text(
            '{"notification": {"enabled": true, "channel": "webhook", "webhook": "https://example.com/webhook/test"}}',
            encoding='utf-8',
        )
        self.Base = env['Base']
        self.engine = env['engine']
        self.async_session = env['async_session']
        self.TaskState = env['TaskState']
        self.TaskService = env['TaskService']

        async with self.engine.begin() as conn:
            await conn.run_sync(self.Base.metadata.drop_all)
            await conn.run_sync(self.Base.metadata.create_all)

    async def asyncTearDown(self):
        await self.engine.dispose()
        self._tmpdir.cleanup()

    async def _create_task(self, *, state, assignee_org='工部'):
        async with self.async_session() as session:
            svc = self.TaskService(session)
            task = await svc.create_task(
                title='backend review action test',
                description='verify backend review action and notifications',
                assignee_org=assignee_org,
                initial_state=state,
                creator='tester',
                meta={'legacy_id': f'JJC-REVIEW-{uuid.uuid4().hex[:8]}'},
            )
            return task.task_id

    async def test_transition_to_pending_confirm_persists_marker(self):
        task_id = await self._create_task(state=self.TaskState.Review)

        with patch('edict.backend.app.services.task_service.send_pending_confirm_notification', lambda task, source_state='', target_state='': True):
            async with self.async_session() as session:
                svc = self.TaskService(session)
                await svc.transition_state(task_id, self.TaskState.Done, agent='shangshu', reason='申请完结')

            async with self.async_session() as session:
                svc = self.TaskService(session)
                data = (await svc.get_task(task_id)).to_dict()

        self.assertEqual(data['state'], 'PendingConfirm')
        self.assertTrue(data['notifications']['pending_confirm_sent'])
        self.assertIn('gate_checks', data)
        self.assertEqual(data['gate_checks'][-1]['result'], 'pending')

    async def test_review_action_approve_pending_confirm_persists_result_marker(self):
        task_id = await self._create_task(state=self.TaskState.Review)

        with patch('edict.backend.app.services.task_service.send_pending_confirm_notification', lambda task, source_state='', target_state='': True), patch('edict.backend.app.services.task_service.send_review_result_notification', lambda task, action='', comment='': True):
            async with self.async_session() as session:
                svc = self.TaskService(session)
                await svc.transition_state(task_id, self.TaskState.Done, agent='shangshu', reason='申请完结')

            async with self.async_session() as session:
                svc = self.TaskService(session)
                await svc.review_action(task_id, action='approve', comment='准奏', agent='menxia')

            async with self.async_session() as session:
                svc = self.TaskService(session)
                data = (await svc.get_task(task_id)).to_dict()

        self.assertEqual(data['state'], 'Done')
        self.assertEqual(data['notifications']['review_result_sent'], 'approve')
        self.assertIn('准奏', data['output'])
        self.assertTrue(any('review:approve' in item.get('content', '') for item in data['progress_log']))

    async def test_review_action_reject_from_review_returns_to_zhongshu_and_tracks_round(self):
        task_id = await self._create_task(state=self.TaskState.Review)

        with patch('edict.backend.app.services.task_service.send_review_result_notification', lambda task, action='', comment='': True):
            async with self.async_session() as session:
                svc = self.TaskService(session)
                await svc.review_action(task_id, action='reject', comment='需要修改', agent='menxia')

            async with self.async_session() as session:
                svc = self.TaskService(session)
                data = (await svc.get_task(task_id)).to_dict()

        self.assertEqual(data['state'], 'Zhongshu')
        self.assertEqual(data['review_round'], 1)
        self.assertIn('第1轮', data['now'])
        self.assertEqual(data['notifications']['review_result_sent'], 'reject')
        self.assertTrue(any('review:reject' in item.get('content', '') for item in data['progress_log']))


if __name__ == '__main__':
    unittest.main()
