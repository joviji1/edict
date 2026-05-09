import pathlib
import unittest
import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient

from tests.backend_test_env import bootstrap_backend_test_env


class ReviewActionRoutesTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        env = bootstrap_backend_test_env('test-review-action-routes.db')
        self._tmpdir = env['tmpdir']
        self.data_dir = env['root'] / 'data'
        self.data_dir.mkdir(exist_ok=True)
        (self.data_dir / 'morning_brief_config.json').write_text(
            '{"notification": {"enabled": false, "channel": "feishu", "webhook": "https://example.com/webhook/test"}}',
            encoding='utf-8',
        )
        self.Base = env['Base']
        self.engine = env['engine']
        self.async_session = env['async_session']
        self.TaskState = env['TaskState']
        self.TaskService = env['TaskService']
        self.legacy_api = env['legacy_api']
        self.tasks_api = env['tasks_api']

        async with self.engine.begin() as conn:
            await conn.run_sync(self.Base.metadata.drop_all)
            await conn.run_sync(self.Base.metadata.create_all)

    async def asyncTearDown(self):
        await self.engine.dispose()
        self._tmpdir.cleanup()

    async def _create_task(self, *, state):
        legacy_id = f'JJC-ROUTE-REVIEW-{uuid.uuid4().hex[:8]}'
        async with self.async_session() as session:
            svc = self.TaskService(session)
            task = await svc.create_task(
                title='review action route test',
                description='verify review-action routes',
                assignee_org='工部',
                initial_state=state,
                creator='tester',
                meta={'legacy_id': legacy_id},
                tags=[legacy_id],
            )
            return legacy_id, task.task_id

    def _make_client(self):
        app = FastAPI()
        app.include_router(self.tasks_api.router, prefix='/api/tasks')
        app.include_router(self.legacy_api.router, prefix='/api/tasks')
        return TestClient(app)

    async def test_task_review_action_route_approves_pending_confirm(self):
        _legacy_id, task_id = await self._create_task(state=self.TaskState.Review)

        async with self.async_session() as session:
            svc = self.TaskService(session)
            await svc.transition_state(task_id, self.TaskState.Done, agent='shangshu', reason='申请完结')

        with self._make_client() as client:
            resp = client.post(
                f'/api/tasks/{task_id}/review-action',
                json={'action': 'approve', 'comment': '准奏', 'agent': 'menxia'},
            )

        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body['ok'])
        self.assertEqual(body['state'], 'Done')
        self.assertIn('已准奏', body['message'])

    async def test_legacy_review_action_route_rejects_review_and_returns_round(self):
        legacy_id, _task_id = await self._create_task(state=self.TaskState.Review)

        with self._make_client() as client:
            resp = client.post(
                f'/api/tasks/by-legacy/{legacy_id}/review-action',
                json={'action': 'reject', 'comment': '退回修订', 'agent': 'menxia'},
            )

        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body['ok'])
        self.assertEqual(body['state'], 'Zhongshu')
        self.assertEqual(body['review_round'], 1)


if __name__ == '__main__':
    unittest.main()
