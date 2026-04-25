import os
import pathlib
import sys
import tempfile
import unittest
import uuid

ROOT = pathlib.Path('/root/.openclaw/workspace/edict')
sys.path.insert(0, str(ROOT))

_TMPDIR = tempfile.TemporaryDirectory()
os.environ['DATABASE_URL'] = f"sqlite+aiosqlite:///{pathlib.Path(_TMPDIR.name) / 'test-adoption.db'}"
os.environ['EDICT_HOME'] = _TMPDIR.name

from edict.backend.app.db import Base, async_session, engine  # noqa: E402
from edict.backend.app.models.task import TaskState  # noqa: E402
from edict.backend.app.services.task_service import TaskService  # noqa: E402


class TaskServiceGovernanceAdoptionTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    async def _create_task(self, *, state: TaskState, assignee_org='工部'):
        async with async_session() as session:
            svc = TaskService(session)
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
        async with async_session() as session:
            svc = TaskService(session)
            task = await svc.get_task(task_id)
            return task.to_dict()

    async def test_review_done_becomes_pending_confirm_and_exports_gate_fields(self):
        task_id = await self._create_task(state=TaskState.Review)

        async with async_session() as session:
            svc = TaskService(session)
            task = await svc.transition_state(task_id, TaskState.Done, agent='shangshu', reason='申请完结')
            data = task.to_dict()

        self.assertEqual(data['state'], 'PendingConfirm')
        self.assertEqual(data['pending_confirm']['target_state'], 'Done')
        self.assertEqual(data['pendingConfirm']['confirm_by'], 'menxia')
        self.assertEqual(data['gate_checks'][0]['result'], 'pending')
        self.assertEqual(data['gateChecks'][0]['from'], 'Review')
        self.assertEqual(data['meta']['pending_confirm']['risk_key'], 'Review->Done')
        self.assertEqual(data['meta']['gate_checks'][0]['to'], 'Done')

    async def test_pending_confirm_approval_clears_pending_and_appends_gate_resolution(self):
        task_id = await self._create_task(state=TaskState.Review)

        async with async_session() as session:
            svc = TaskService(session)
            await svc.transition_state(task_id, TaskState.Done, agent='shangshu', reason='申请完结')

        async with async_session() as session:
            svc = TaskService(session)
            task = await svc.transition_state(task_id, TaskState.Done, agent='menxia', reason='准奏')
            data = task.to_dict()

        self.assertEqual(data['state'], 'Done')
        self.assertIsNone(data['pending_confirm'])
        self.assertIsNone(data['pendingConfirm'])
        self.assertEqual(len(data['gate_checks']), 2)
        self.assertEqual(data['gate_checks'][-1]['result'], 'approved')
        self.assertEqual(data['memory_extracted']['done']['agent'], 'menxia')
        self.assertEqual(data['memoryExtracted']['done']['source'], 'api-transition')
        self.assertNotIn('pending_confirm', data['meta'])

    async def test_terminal_transition_sets_memory_extracted_and_compat_fields(self):
        task_id = await self._create_task(state=TaskState.Doing)

        async with async_session() as session:
            svc = TaskService(session)
            task = await svc.transition_state(task_id, TaskState.Cancelled, agent='gongbu', reason='执行中撤销')
            data = task.to_dict()

        self.assertEqual(data['state'], 'PendingConfirm')
        self.assertEqual(data['pendingConfirm']['risk_key'], 'Doing->Cancelled')

        async with async_session() as session:
            svc = TaskService(session)
            task = await svc.transition_state(task_id, TaskState.Cancelled, agent='shangshu', reason='确认撤销')
            data = task.to_dict()

        self.assertEqual(data['state'], 'Cancelled')
        self.assertEqual(data['memory_extracted']['blocked']['agent'], 'shangshu')
        self.assertEqual(data['memoryExtracted']['blocked']['source'], 'api-transition')
        self.assertEqual(data['gateChecks'][-1]['result'], 'approved')


if __name__ == '__main__':
    unittest.main()
