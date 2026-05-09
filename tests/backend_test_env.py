from __future__ import annotations

import importlib
import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path('/root/.openclaw/workspace/edict')
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def bootstrap_backend_test_env(db_filename: str) -> dict:
    tmpdir = tempfile.TemporaryDirectory()
    db_path = pathlib.Path(tmpdir.name) / db_filename

    os.environ['DATABASE_URL'] = f'sqlite+aiosqlite:///{db_path}'
    os.environ['EDICT_HOME'] = tmpdir.name
    os.environ['OPENCLAW_PROJECT_DIR'] = tmpdir.name

    for name in [name for name in list(sys.modules) if name.startswith('edict.backend.app')]:
        sys.modules.pop(name, None)

    db_module = importlib.import_module('edict.backend.app.db')
    models_module = importlib.import_module('edict.backend.app.models.task')
    service_module = importlib.import_module('edict.backend.app.services.task_service')
    worker_module = importlib.import_module('edict.backend.app.workers.dispatch_worker')
    legacy_api = importlib.import_module('edict.backend.app.api.legacy')
    tasks_api = importlib.import_module('edict.backend.app.api.tasks')
    orchestrator_worker_module = importlib.import_module('edict.backend.app.workers.orchestrator_worker')

    return {
        'tmpdir': tmpdir,
        'root': pathlib.Path(tmpdir.name),
        'db_module': db_module,
        'models_module': models_module,
        'service_module': service_module,
        'worker_module': worker_module,
        'legacy_api': legacy_api,
        'tasks_api': tasks_api,
        'orchestrator_worker_module': orchestrator_worker_module,
        'Base': db_module.Base,
        'engine': db_module.engine,
        'async_session': db_module.async_session,
        'TaskState': models_module.TaskState,
        'TaskService': service_module.TaskService,
        'DispatchWorker': worker_module.DispatchWorker,
    }
