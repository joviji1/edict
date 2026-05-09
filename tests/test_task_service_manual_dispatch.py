import unittest
import uuid

from tests.backend_test_env import bootstrap_backend_test_env


class TaskServiceManualDispatchTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        env = bootstrap_backend_test_env('test-manual-dispatch.db')
        self._tmpdir = env['tmpdir']
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
                title='manual dispatch test',
                description='verify explicit assignee override',
                assignee_org=assignee_org,
                initial_state=state,
                creator='tester',
                meta={'legacy_id': f'JJC-DISPATCH-{uuid.uuid4().hex[:8]}'},
            )
            return task.task_id

    async def test_update_assignee_org_persists_target_dept_for_manual_dispatch(self):
        task_id = await self._create_task(state=self.TaskState.Assigned, assignee_org='工部')

        async with self.async_session() as session:
            svc = self.TaskService(session)
            task = await svc.update_assignee_org(task_id, '兵部', agent='shangshu', reason='显式改派到兵部')
            data = task.to_dict()

        self.assertEqual(data['state'], 'Assigned')
        self.assertEqual(data['org'], '尚书省')
        self.assertEqual(data['assignee_org'], '兵部')
        self.assertEqual(data['targetDept'], '兵部')
        self.assertEqual(data['meta']['targetDept'], '兵部')
        self.assertEqual(data['flow_log'][-1]['reason'], '显式改派到兵部')
        self.assertEqual(data['flow_log'][-1]['to'], '兵部')


if __name__ == '__main__':
    unittest.main()
