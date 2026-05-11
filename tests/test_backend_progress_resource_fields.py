import unittest
import uuid

from tests.backend_test_env import bootstrap_backend_test_env


class BackendProgressResourceFieldsTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        env = bootstrap_backend_test_env('test-backend-progress-resource-fields.db')
        self._tmpdir = env['tmpdir']
        self.Base = env['Base']
        self.engine = env['engine']
        self.async_session = env['async_session']
        self.TaskState = env['TaskState']
        self.TaskService = env['TaskService']
        self.TaskProgress = env['tasks_api'].TaskProgress

        async with self.engine.begin() as conn:
            await conn.run_sync(self.Base.metadata.drop_all)
            await conn.run_sync(self.Base.metadata.create_all)

    async def asyncTearDown(self):
        await self.engine.dispose()
        self._tmpdir.cleanup()

    async def _create_task(self):
        async with self.async_session() as session:
            svc = self.TaskService(session)
            task = await svc.create_task(
                title='progress resource fields test',
                description='verify progress_log keeps resource metrics',
                initial_state=self.TaskState.Doing,
                creator='tester',
                meta={'legacy_id': f'JJC-PROGRESS-{uuid.uuid4().hex[:8]}'},
            )
            return task.task_id

    async def test_task_progress_schema_accepts_resource_fields(self):
        body = self.TaskProgress.model_validate({
            'agent': 'gongbu',
            'content': '实现完成，准备验证',
            'tokens': 1536,
            'cost': 0.0312,
            'model': 'gpt-5.5',
            'elapsed': 12.7,
            'usage': {'prompt_tokens': 900, 'completion_tokens': 636},
        })

        self.assertEqual(body.tokens, 1536)
        self.assertEqual(body.cost, 0.0312)
        self.assertEqual(body.model, 'gpt-5.5')
        self.assertEqual(body.elapsed, 12.7)
        self.assertEqual(body.usage['completion_tokens'], 636)

    async def test_add_progress_persists_resource_fields_in_progress_log(self):
        task_id = await self._create_task()

        async with self.async_session() as session:
            svc = self.TaskService(session)
            await svc.add_progress(
                task_id,
                'gongbu',
                '实现完成，准备验证',
                resource={
                    'tokens': 1536,
                    'cost': 0.0312,
                    'model': 'gpt-5.5',
                    'elapsed': 12.7,
                    'usage': {'prompt_tokens': 900, 'completion_tokens': 636},
                },
            )

        async with self.async_session() as session:
            svc = self.TaskService(session)
            data = (await svc.get_task(task_id)).to_dict()

        last = data['progress_log'][-1]
        self.assertEqual(last['agent'], 'gongbu')
        self.assertEqual(last['content'], '实现完成，准备验证')
        self.assertEqual(last['tokens'], 1536)
        self.assertEqual(last['cost'], 0.0312)
        self.assertEqual(last['model'], 'gpt-5.5')
        self.assertEqual(last['elapsed'], 12.7)
        self.assertEqual(last['usage']['prompt_tokens'], 900)


if __name__ == '__main__':
    unittest.main()
