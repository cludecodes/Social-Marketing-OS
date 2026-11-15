# Shophippy Social Media Marketing OS

**Repo:** https://github.com/cludecodes/Social-Marketing-OS
**Live (frontend SPA):** https://social-marketing-os.vercel.app

> The Vercel deployment hosts the static SPA in `frontend/`. The FastAPI backend runs
> locally (`python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`) or on any
> Python host; point `CORS_ORIGINS` and the SPA's API base at it when deploying both.

An all-in-one social media marketing operating system: AI content engine, multi-agent
automation, scheduling, media generation, multi-platform publishing, analytics, community
management, and lead capture — served by a single FastAPI backend with a built-in vanilla
JavaScript single-page frontend (no build step).

## Features

- **Auth**: JWT login; admin user seeded on first boot (`admin` / `admin123` by default).
- **AI content engine**: idea generation, scoring, daily plans, drafts, approval workflow.
- **Agents**: copywriter, designer, researcher, strategist, QA, publisher, CMO, analytics,
  audience, community, trends, video — toggleable and runnable from the dashboard.
- **Automation scheduler**: APScheduler pipeline (research -> strategy -> create -> QA ->
  publish -> analytics -> optimize) on a configurable PKT schedule.
- **Publishing**: multi-platform social accounts (Facebook, Instagram, LinkedIn, Pinterest,
  Threads, TikTok, X, YouTube) with OAuth connect; autonomous publishing is OFF by default
  (kill switch in Settings).
- **Media**: AI image generation, video generation, PDF lead-magnet guides.
- **Analytics & community**: published post metrics, comment inbox with reply/escalate.
- **Landing page & leads**: built-in landing page payload plus lead capture API.
- **Settings**: brand, timezone, QA score threshold, automation toggles.

## Project layout

```
backend/app/          FastAPI application
  main.py             app entry, static frontend mount, router includes
  config.py           env-driven settings
  db.py               engine + db_session + init_db
  models.py           SQLAlchemy models
  api/auth.py         JWT auth, /health
  api/routes.py       all business endpoints (auth required)
  ai/                 content engine + provider abstraction
  agents/             agent implementations
  automation/         scheduler + job queue
  media/              image/video/PDF generators
  social/             platform clients + factory
  orchestrator.py     queue processing
  settings_store.py   app settings persistence
frontend/             index.html, styles.css, app.js (SPA)
backend/tests/        pytest suite (conftest.py, test_api.py, test_scheduler.py)
storage/              data (SQLite), media, logs (created at runtime)
```

## Quick start

```powershell
# Windows PowerShell
copy .env.example backend\.env
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Or use the wrapper scripts at the repo root: `.\run.ps1` (Windows) or `bash run.sh` (Unix).

Open http://127.0.0.1:8000 and log in with `admin` / `admin123`.

## Tests

```powershell
cd backend
python -m pytest tests -q
```

## Configuration

See `.env.example`. Before production set `SECRET_KEY`, `OPENAI_API_KEY`, and
`ADMIN_PASSWORD`; never commit real credentials. `AUTONOMOUS_PUBLISHING` defaults to
`false` — enable it only when unattended publishing is intended.

## Security notes

- All `/api/v1` endpoints require a valid JWT except `GET /api/v1/health`.
- Default admin password must be changed in production.
