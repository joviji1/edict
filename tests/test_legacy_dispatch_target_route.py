import unittest
import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient

from tests.backend_test_env import bootstrap_backend_test_env


class LegacyDispatchTargetRouteTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        env = bootstrap_backend_test_env('test-legacy-dispatch-route.db')
        self._tmpdir = env['tmpdir']
        self.Base = env['Base']
        self.engine = env['engine']
        self.async_session = env['async_session']
        self.TaskState = env['TaskState']
        self.TaskService = env['TaskService']
        self.legacy_api = env['legacy_api']

        async with self.engine.begin() as conn:
            await conn.run_sync(self.Base.metadata.drop_all)
            await conn.run_sync(self.Base.metadata.create_all)

    async def asyncTearDown(self):
        await self.engine.dispose()
        self._tmpdir.cleanup()

    async def _create_task(self, *, legacy_id: str, state, assignee_org='工部'):
        async with self.async_session() as session:
            svc = self.TaskService(session)
            task = await svc.create_task(
                title='legacy dispatch route test',
                description='verify legacy dispatch-target route',
                assignee_org=assignee_org,
                initial_state=state,
                creator='tester',
                meta={'legacy_id': legacy_id},
                tags=[legacy_id],
            )
            return task.task_id

    def _make_client(self):
        app = FastAPI()
        app.include_router(self.legacy_api.router, prefix='/api/tasks')
        return TestClient(app)

    async def test_dispatch_target_route_updates_assignee_for_legacy_id(self):
        legacy_id = f'JJC-ROUTE-{uuid.uuid4().hex[:8]}'
        await self._create_task(legacy_id=legacy_id, state=self.TaskState.Assigned, assignee_org='工部')

        with self._make_client() as client:
            resp = client.post(
                f'/api/tasks/by-legacy/{legacy_id}/dispatch-target',
                json={'target_dept': '兵部', 'agent': 'shangshu', 'reason': '显式改派到兵部'},
            )

        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body['assignee_org'], '兵部')
        self.assertEqual(body['targetDept'], '兵部')
        self.assertEqual(body['state'], 'Assigned')


if __name__ == '__main__':
    unittest.main()
