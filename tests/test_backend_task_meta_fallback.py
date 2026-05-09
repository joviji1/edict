from __future__ import annotations

import asyncio

from tests.backend_test_env import bootstrap_backend_test_env


def _build_task_row(**kwargs):
    env = bootstrap_backend_test_env('test-backend-task-meta-fallback.db')
    try:
        Task = env['models_module'].Task
        task = Task(**kwargs)
        return task.to_dict(), env
    except Exception:
        asyncio.run(env['engine'].dispose())
        env['tmpdir'].cleanup()
        raise


def _cleanup_env(env: dict):
    asyncio.run(env['engine'].dispose())
    env['tmpdir'].cleanup()


def test_task_to_dict_falls_back_to_meta_legacy_fields():
    env = bootstrap_backend_test_env('test-backend-task-meta-fallback.db')
    try:
        Task = env['models_module'].Task
        TaskState = env['TaskState']
        task = Task(
            title='backend meta fallback',
            description='等待太子接旨分拣',
            priority='high',
            state=TaskState.Taizi,
            creator='工部尚书',
            meta={
                'legacy_id': 'JJC-TEST-001',
                'templateId': 'tpl-legacy',
                'templateParams': {'city': '北京'},
                'ac': '验收说明',
                'targetDept': '工部',
            },
        )

        row = task.to_dict()

        assert row['templateId'] == 'tpl-legacy'
        assert row['templateParams']['city'] == '北京'
        assert row['ac'] == '验收说明'
        assert row['targetDept'] == '工部'
    finally:
        asyncio.run(env['engine'].dispose())
        env['tmpdir'].cleanup()


def test_task_to_dict_exposes_meta_notifications_compatibly():
    env = bootstrap_backend_test_env('test-backend-task-meta-fallback.db')
    try:
        Task = env['models_module'].Task
        TaskState = env['TaskState']
        task = Task(
            title='backend notification fallback',
            description='等待门禁审批',
            priority='high',
            state=TaskState.PendingConfirm,
            creator='尚书令',
            meta={
                'legacy_id': 'JJC-TEST-002',
                'notifications': {
                    'pending_confirm_sent': True,
                    'pending_confirm_sent_at': '2026-04-26T22:00:00Z',
                    'review_result_sent': 'approved',
                },
            },
        )

        row = task.to_dict()

        assert row['notifications']['pending_confirm_sent'] is True
        assert row['notifications']['review_result_sent'] == 'approved'
    finally:
        asyncio.run(env['engine'].dispose())
        env['tmpdir'].cleanup()
