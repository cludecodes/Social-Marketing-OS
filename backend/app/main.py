"""FastAPI application entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import auth, routes
from .automation.scheduler import start_scheduler, stop_scheduler
from .config import settings
from .db import init_db
from .agents.base import ensure_all_registered
from .api.auth import seed_admin
from .orchestrator import process_queue


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    from .db import db_session
    with db_session() as db:
        ensure_all_registered(db)
        seed_admin()
    start_scheduler()
    # process any queued jobs once at boot
    process_queue(max_jobs=5)
    yield
    stop_scheduler()


app = FastAPI(title=settings.APP_NAME, version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])
app.include_router(auth.router, prefix=settings.API_V1_PREFIX + "/auth", tags=["auth"])
app.include_router(routes.router, prefix=settings.API_V1_PREFIX, tags=["core"])
app.include_router(routes.public_router, prefix=settings.API_V1_PREFIX)

import os
from fastapi.staticfiles import StaticFiles

_FRONTEND = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "frontend")
if os.path.isdir(_FRONTEND):
    app.mount("/", StaticFiles(directory=_FRONTEND, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
