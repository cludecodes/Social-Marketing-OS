"""Automation scheduler: configurable daily workflow (PKT default), job queue processor."""
from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler

from ..config import settings
from ..orchestrator import run_step, process_queue
from ..agents.base import ensure_all_registered
from ..db import db_session
from ..settings_store import get_schedule, get_settings

_scheduler: BackgroundScheduler | None = None


def _step(step: str):
    def job():
        s = get_settings()
        if not s.get("automation_enabled", True):
            return
        run_step(step)
    return job


def _queue_worker():
    process_queue(max_jobs=5)


def start_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler
    sched = BackgroundScheduler(timezone=settings.TIMEZONE)
    times = get_schedule()
    for step, hhmm in times.items():
        try:
            hour, minute = [int(x) for x in hhmm.split(":")]
        except Exception:
            continue
        sched.add_job(_step(step), "cron", hour=hour, minute=minute, id=f"step_{step}", replace_existing=True,
                      timezone=settings.TIMEZONE, max_instances=1, coalesce=True)
    sched.add_job(_queue_worker, "interval", minutes=2, id="queue_worker", replace_existing=True, max_instances=1)
    sched.start()
    _scheduler = sched
    return sched


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None


def reschedule() -> dict:
    """Re-read times from settings store (called after admin changes schedule)."""
    stop_scheduler()
    with db_session() as db:
        ensure_all_registered(db)
    start_scheduler()
    return get_schedule()
