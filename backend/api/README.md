# Griffin Backend API (FastAPI)

A Python FastAPI service that mirrors the Bun `ml-service` websocket contract
(see `backend/ml-service/index.ts`) and adds database persistence for projects,
offices, and messages. It is additive: the existing Bun service keeps working,
and this service can run alongside it.

## What it does

- Exposes a `/ws` websocket that accepts `{"type": "prompt", "data": "..."}`,
  spawns `python -m ML.main <prompt>` from the repository root, parses its
  stdout, and forwards the exact same message types the Bun service emits:
  `progress`, `terminal`, `office_status`, `token_usage`, `cost_update`, `file`,
  and a final `complete` (with `projectName` and, when online, `githubUrl`), or
  `error` on failure.
- Persists a `project` row when a run starts, inserts `message` rows for
  `progress`, `office_status`, and `complete` events, and upserts `office` rows
  as office status events arrive. Token and secret values are masked before they
  are written.
- Serves a small REST surface for reading the persisted data.

## Database

The schema follows `REQUIREMENTS.md` section 7 (`projects`, `offices`,
`messages`). The default database is a local SQLite file, so the service runs
offline with no extra infrastructure:

    DATABASE_URL=sqlite:///griffin.db   # default

To use PostgreSQL, point `DATABASE_URL` at a `postgresql+psycopg://` URL (the
optional `psycopg[binary]` driver from `requirements.txt` handles it):

    DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/griffin

Tables are created automatically on startup.

## Run

From this directory (`backend/api`):

    pip install -r requirements.txt
    uvicorn app.main:app --reload --port 8000

The websocket is then available at `ws://localhost:8000/ws`.

### REST endpoints

- `GET /` health check, returns `{"status": "ok"}`.
- `GET /projects` list all projects, newest first.
- `GET /projects/{id}` a single project with its offices.
- `GET /projects/{id}/messages` the messages for a project, oldest first.

## Offline pipeline

Everything runs offline with the mock LLM provider. Set `LLM_PROVIDER=mock` in
the environment and the spawned pipeline makes no network calls and needs no API
keys. This is how the tests and CI run.

## Tests

From this directory:

    LLM_PROVIDER=mock python -m pytest

The suite covers persistence plus REST reads, and a websocket run that connects
to `/ws`, sends a prompt with the mock provider, collects the streamed messages,
and asserts it receives `office_status`, `token_usage`, and a final `complete`,
and that a project row was persisted.

## Environment variables

| Variable                  | Default               | Purpose                                   |
| ------------------------- | --------------------- | ----------------------------------------- |
| `DATABASE_URL`            | `sqlite:///griffin.db`| Database connection string.               |
| `LLM_PROVIDER`            | (from ML config)      | Set to `mock` for offline runs.           |
| `GRIFFIN_REPO_ROOT`       | auto detected         | Repository root used to spawn the ML CLI. |
| `GRIFFIN_PIPELINE_TIMEOUT`| `300`                 | Seconds before a stuck run is terminated. |
