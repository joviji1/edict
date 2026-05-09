# edict reality sync — 2026-05-08

## Runtime evidence

- dashboard health: `GET 127.0.0.1:7892/healthz` -> ok
- backend health: `GET 127.0.0.1:18000/health` -> `status=ok, version=2.0.0, engine=edict`
- backend deep health: `postgres=true, redis=true`
- systemd: `edict-dashboard.service=active`, `edict-loop.service=active`
- dashboard env: `EDICT_TASK_WRITE_MODE=dual`
- loop env: `EDICT_ENABLE_BACKEND_EXPORT=false`

## Data surfaces

- backend tasks: 18 (`Done=3, Cancelled=14, Zhongshu=1`)
- `data/tasks_source.json`: 16 (`Review=1, Menxia=1, Zhongshu=1, Done=12, Assigned=1`)
- `data/live_status.json`: `taskSource=tasks_source.json`, `taskSourceMeta={}`, layers=`runtime=1/governanceSample=5/jjcArchive=35`

Conclusion: current data surfaces are not three-surface consistent. The current truth is “production fork running, export chain disabled, local JSON view active”.

## Verification results

- Python compile: passed for selected dashboard/scripts/backend files.
- Frontend build: `npm run build` passed; built `dashboard/dist/assets/index-DTF-vrkR.js` and `index-CmV35B_1.css`.
- Targeted pytest set: 63 passed, 11 failed.

### Test failure clusters

1. `tests/test_server.py` still expects `python3` literal, but production code uses resolved interpreter path from Hermes venv/system Python.
2. PendingConfirm notification marker expectation drift: send happens, but `notifications.pending_confirm_sent` not written in this path.
3. taizi/shangshu main-session guard expectations drift: tests expect suppression, current behavior queues/wakes and logs subprocess failure in monkeypatched path.
4. dual-mode backend failure fallback expectations drift: dispatch/review/todos/create fallback behavior no longer matches tests.
5. `_FakeNow` monkeypatch incompatibility in create-task daily legacy id test.

These are real gaps. Do not report the targeted test suite as passing until fixed or deliberately rebaselined.
