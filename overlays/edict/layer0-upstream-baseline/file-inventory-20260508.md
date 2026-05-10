# cft0808/edict upstream inventory — 2026-05-08

- upstream path: `/root/.openclaw/workspace/_third_party/cft0808-edict-upstream`
- upstream HEAD: `14a2075`
- total files: 221

## Module counts

| module | files | notes |
|---|---:|---|
| `edict/backend` | 35 | FastAPI backend, task service, outbox, Redis workers, channel adapters |
| `edict/frontend` | 31 | React/Vite dashboard client |
| `scripts` | 15 | runtime sync, model apply, kanban, live refresh, screenshots |
| `tests` | 12 | upstream baseline tests, much thinner than local |
| `docs` | 48 | docs + screenshots/assets |
| `dashboard` | 7 | stdlib dashboard server and built frontend |
| `agents` | 15 | 三省六部 SOUL/GLOBAL/group prompts |

## Key upstream contracts read so far

- Backend `TaskService`: CRUD/state transition/outbox in one transaction, row lock on transition, Redis event bus handoff.
- Backend `dispatch_worker`: consumes `task.dispatch`, builds agent context, calls OpenClaw CLI, records outputs.
- Backend `orchestrator_worker`: consumes task lifecycle events, auto dispatches next agent, handles stalled tasks with retry/escalation/block.
- Frontend `store.ts`: 10-tab baseline with edicts/court/monitor/officials/models/skills/sessions/memorials/templates/morning.
- `scripts/run_loop.sh`: 15s sync loop + 120s scheduler scan + single-instance pid guard.
- `docs/task-dispatch-architecture.md`: official architecture still describes 10 panels and institutional flow; local docs/UI have drifted to richer production surface.
