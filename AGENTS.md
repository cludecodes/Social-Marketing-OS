# AGENTS.md — guide for AI coding agents

## Stack

FastAPI + SQLAlchemy 2.0 + Pydantic v2 + APScheduler backend; vanilla HTML/CSS/JS SPA in
`frontend/` (no build step). SQLite via `DATABASE_URL` (default
`storage/data/shophippy.db`). Python 3.14 in the test env.

## Layout

- `backend/app/main.py` — app entry, router includes, static mount of `../frontend` at `/`.
- `backend/app/api/auth.py` — JWT login, `seed_admin`, public `public_router` (`/health`).
- `backend/app/api/routes.py` — ALL business endpoints. Router is declared with
  `dependencies=[Depends(get_current_user)]`; only `public_router` is unauthenticated.
- `backend/app/settings_store.py` — app settings persistence.
- `backend/app/ai/`, `agents/`, `automation/`, `media/`, `social/` — feature modules.
- `backend/tests/` — `conftest.py` (temp sqlite via env override before app import,
  `init_db`, `ensure_all_registered`, `seed_admin`, `client`, `auth_headers`),
  `test_api.py`, `test_scheduler.py`.

## Run / test

```powershell
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
python -m pytest tests -q
```

Admin creds default `admin` / `admin123` (config.py `ADMIN_USERNAME`/`ADMIN_PASSWORD`).

## Conventions & gotchas

- No code comments (project style).
- PowerShell 5.1: no `&&` (use `;` or separate calls); `Invoke-WebRequest` has no
  `-SkipHttpErrorCheck` — use try/catch or python for non-2xx checks.
- `db_session()` commits on context exit; never return ORM objects after session close —
  materialize dicts first (see `settings_store.get_settings` fix).
- Frontend `formVals()` reads `data-field` attributes, NOT element ids (schedule modal bug).
- `content_engine.daily_plan(count=...)` takes `max_posts`, not `count`.
- Timezone for schedules/settings is PKT (Asia/Karachi) by default.
- `AUTONOMOUS_PUBLISHING` defaults false; publisher only runs manually or when enabled.
- Add new business endpoints to the auth-protected `router`, never to `public_router`.
- Never commit secrets; `.env` is config-only (see `.env.example`).

## Scratch-file hygiene

Diag scripts (`diag_db.py`, `test_flow.py`, `test_publish.py`) are temporary; delete after
use. Keep `backend/tests/` as the only test home.
