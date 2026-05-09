import unittest
from unittest.mock import AsyncMock, patch

from tests.backend_test_env import bootstrap_backend_test_env


class OrchestratorStalledRecoveryTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        env = bootstrap_backend_test_env('test-orchestrator-stalled.db')
        self._tmpdir = env['tmpdir']
        self.Base = env['Base']
        self.engine = env['engine']
        self.async_session = env['async_session']
        self.TaskState = env['TaskState']
        self.TaskService = env['TaskService']
        self.orchestrator_worker_module = env['orchestrator_worker_module']
        self.MAX_ESCALATION_LEVEL = env['orchestrator_worker_module'].MAX_ESCALATION_LEVEL
        self.MAX_STALL_RETRIES = env['orchestrator_worker_module'].MAX_STALL_RETRIES
        self.OrchestratorWorker = env['orchestrator_worker_module'].OrchestratorWorker

        async with self.engine.begin() as conn:
            await conn.run_sync(self.Base.metadata.drop_all)
            await conn.run_sync(self.Base.metadata.create_all)

    async def asyncTearDown(self):
        await self.engine.dispose()
        self._tmpdir.cleanup()

    async def _create_task(self, state=None, assignee_org='兵部'):
        state = state or self.TaskState.Doing
        async with self.async_session() as session:
            svc = self.TaskService(session)
            task = await svc.create_task(
                title='stalled recovery test',
                description='simulate stalled task',
                assignee_org=assignee_org,
                initial_state=state,
                creator='tester',
            )
            return str(task.task_id), task.trace_id

    async def _load_task(self, task_id):
        async with self.async_session() as session:
            svc = self.TaskService(session)
            task = await svc.get_task(task_id)
            return task.to_dict()

    async def test_retry_updates_scheduler_and_requeues_dispatch(self):
        task_id, trace_id = await self._create_task(state=self.TaskState.Doing, assignee_org='兵部')
        worker = self.OrchestratorWorker()
        worker.bus = AsyncMock()

        payload = {
            'task_id': task_id,
            'state': 'Doing',
            'assignee_org': '兵部',
            'stall_count': 0,
            'escalation_level': 0,
            'last_updated': '2026-04-17T00:00:00+00:00',
        }
        await worker._on_task_stalled(payload, trace_id)

        task = await self._load_task(task_id)
        sched = task['scheduler']
        self.assertEqual(sched.get('retryCount'), 1)
        self.assertEqual(sched.get('escalationLevel'), 0)
        self.assertEqual(sched.get('stallReason'), 'no_heartbeat')
        self.assertEqual(sched.get('lastStalledState'), 'Doing')
        self.assertEqual(sched.get('lastDispatchAgent'), 'bingbu')
        self.assertIn('停滞重试', task['flow_log'][-1]['reason'])

        worker.bus.publish.assert_awaited_once()
        kwargs = worker.bus.publish.await_args.kwargs
        self.assertEqual(kwargs['event_type'], 'task.dispatch.retry')
        self.assertEqual(kwargs['payload']['agent'], 'bingbu')
        self.assertEqual(kwargs['payload']['stall_count'], 1)

    async def test_escalation_persists_state_and_dispatches_supervisor(self):
        task_id, trace_id = await self._create_task(state=self.TaskState.Doing, assignee_org='兵部')
        worker = self.OrchestratorWorker()
        worker.bus = AsyncMock()

        payload = {
            'task_id': task_id,
            'state': 'Doing',
            'assignee_org': '兵部',
            'stall_count': self.MAX_STALL_RETRIES,
            'escalation_level': 0,
            'last_updated': '2026-04-17T00:00:00+00:00',
        }
        await worker._on_task_stalled(payload, trace_id)

        task = await self._load_task(task_id)
        sched = task['scheduler']
        self.assertEqual(task['state'], 'Assigned')
        self.assertEqual(task['org'], '尚书省')
        self.assertEqual(sched.get('retryCount'), self.MAX_STALL_RETRIES)
        self.assertEqual(sched.get('escalationLevel'), 1)
        self.assertEqual(sched.get('stallReason'), 'no_heartbeat')
        self.assertEqual(sched.get('lastEscalatedFrom'), 'Doing')
        self.assertEqual(sched.get('lastEscalatedTo'), 'Assigned')
        self.assertIn('停滞升级', task['flow_log'][-1]['reason'])

        self.assertEqual(worker.bus.publish.await_count, 2)
        first = worker.bus.publish.await_args_list[0].kwargs
        second = worker.bus.publish.await_args_list[1].kwargs
        self.assertEqual(first['topic'], 'task.escalated')
        self.assertEqual(second['event_type'], 'task.dispatch.escalation')
        self.assertEqual(second['payload']['agent'], 'shangshu')

    async def test_blocked_generates_autopsy_and_marks_task_blocked(self):
        task_id, trace_id = await self._create_task(state=self.TaskState.Taizi, assignee_org='兵部')
        worker = self.OrchestratorWorker()
        worker.bus = AsyncMock()

        with patch('edict.backend.app.workers.orchestrator_worker.subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = '{"mode":"bypass-draft","mutated_task_source":false}'
            mock_run.return_value.stderr = ''

            payload = {
                'task_id': task_id,
                'state': 'Taizi',
                'assignee_org': '兵部',
                'stall_count': self.MAX_STALL_RETRIES,
                'escalation_level': self.MAX_ESCALATION_LEVEL,
                'last_updated': '2026-04-17T00:00:00+00:00',
                'stall_reason': 'provider_timeout',
            }
            await worker._on_task_stalled(payload, trace_id)

        task = await self._load_task(task_id)
        sched = task['scheduler']
        self.assertEqual(task['state'], 'Blocked')
        self.assertEqual(sched.get('retryCount'), self.MAX_STALL_RETRIES)
        self.assertEqual(sched.get('escalationLevel'), self.MAX_ESCALATION_LEVEL)
        self.assertEqual(sched.get('stallReason'), 'provider_timeout')
        self.assertIn('人工介入', task['block'])
        self.assertIn('停滞阻塞', task['flow_log'][-1]['reason'])
        self.assertEqual(worker.bus.publish.await_count, 0)
        mock_run.assert_called_once()
        cmd = mock_run.call_args.args[0]
        self.assertTrue(any(part.endswith('autopsy_draft.py') for part in cmd))
        self.assertFalse(any(part.endswith('kanban_update.py') for part in cmd))
        self.assertNotIn('autopsy', cmd)
        self.assertIn(task_id, cmd)
        self.assertIn('--reason', cmd)
        self.assertIn('provider_timeout', cmd)


if __name__ == '__main__':
    unittest.main()
