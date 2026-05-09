import unittest
import uuid

from tests.backend_test_env import bootstrap_backend_test_env


class TaskServiceGovernanceAdoptionTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        env = bootstrap_backend_test_env('test-adoption.db')
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
                title='governance adoption test',
                description='verify legacy governance side effects',
                assignee_org=assignee_org,
                initial_state=state,
                creator='tester',
                meta={'legacy_id': f'JJC-TEST-{uuid.uuid4().hex[:8]}'},
            )
            return task.task_id

    async def _load_task_dict(self, task_id):
        async with self.async_session() as session:
            svc = self.TaskService(session)
            task = await svc.get_task(task_id)
            return task.to_dict()

    async def test_review_done_becomes_pending_confirm_and_exports_gate_fields(self):
        task_id = await self._create_task(state=self.TaskState.Review)

        async with self.async_session() as session:
            svc = self.TaskService(session)
            task = await svc.transition_state(task_id, self.TaskState.Done, agent='shangshu', reason='申请完结')
            data = task.to_dict()

        self.assertEqual(data['state'], 'PendingConfirm')
        self.assertEqual(data['pending_confirm']['target_state'], 'Done')
        self.assertEqual(data['pendingConfirm']['confirm_by'], 'menxia')
        self.assertEqual(data['gate_checks'][0]['result'], 'pending')
        self.assertEqual(data['gateChecks'][0]['from'], 'Review')
        self.assertEqual(data['meta']['pending_confirm']['risk_key'], 'Review->Done')
        self.assertEqual(data['meta']['gate_checks'][0]['to'], 'Done')

    async def test_pending_confirm_approval_clears_pending_and_appends_gate_resolution(self):
        task_id = await self._create_task(state=self.TaskState.Review)

        async with self.async_session() as session:
            svc = self.TaskService(session)
            await svc.transition_state(task_id, self.TaskState.Done, agent='shangshu', reason='申请完结')

        async with self.async_session() as session:
            svc = self.TaskService(session)
            task = await svc.transition_state(task_id, self.TaskState.Done, agent='menxia', reason='准奏')
            data = task.to_dict()

        self.assertEqual(data['state'], 'Done')
        self.assertIsNone(data['pending_confirm'])
        self.assertIsNone(data['pendingConfirm'])
        self.assertEqual(len(data['gate_checks']), 2)
        self.assertEqual(data['gate_checks'][-1]['result'], 'approved')
        self.assertEqual(data['memory_extracted']['done']['agent'], 'menxia')
        self.assertEqual(data['memoryExtracted']['done']['source'], 'api-transition')
        self.assertNotIn('pending_confirm', data['meta'])

    async def test_pending_confirm_reject_returns_to_zhongshu_and_appends_gate_resolution(self):
        task_id = await self._create_task(state=self.TaskState.Review)

        async with self.async_session() as session:
            svc = self.TaskService(session)
            await svc.transition_state(task_id, self.TaskState.Done, agent='shangshu', reason='申请完结')

        async with self.async_session() as session:
            svc = self.TaskService(session)
            task = await svc.transition_state(task_id, self.TaskState.Zhongshu, agent='menxia', reason='封驳退回修订')
            data = task.to_dict()

        self.assertEqual(data['state'], 'Zhongshu')
        self.assertIsNone(data['pending_confirm'])
        self.assertEqual(data['gate_checks'][-1]['result'], 'rejected')
        self.assertEqual(data['gateChecks'][-1]['to'], 'Done')
        self.assertNotIn('pending_confirm', data['meta'])

    async def test_terminal_transition_sets_memory_extracted_and_compat_fields(self):
        task_id = await self._create_task(state=self.TaskState.Doing)

        async with self.async_session() as session:
            svc = self.TaskService(session)
            task = await svc.transition_state(task_id, self.TaskState.Cancelled, agent='gongbu', reason='执行中撤销')
            data = task.to_dict()

        self.assertEqual(data['state'], 'PendingConfirm')
        self.assertEqual(data['pendingConfirm']['risk_key'], 'Doing->Cancelled')

        async with self.async_session() as session:
            svc = self.TaskService(session)
            task = await svc.transition_state(task_id, self.TaskState.Cancelled, agent='shangshu', reason='确认撤销')
            data = task.to_dict()

        self.assertEqual(data['state'], 'Cancelled')
        self.assertEqual(data['memory_extracted']['blocked']['agent'], 'shangshu')
        self.assertEqual(data['memoryExtracted']['blocked']['source'], 'api-transition')
        self.assertEqual(data['gateChecks'][-1]['result'], 'approved')


if __name__ == '__main__':
    unittest.main()
