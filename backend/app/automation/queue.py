"""Persistent job queue with task locking, retries, backoff and dead-lettering."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from ..db import db_session
from ..models import JobQueue

WORKER_ID = "worker-1"


def enqueue(db, agent: str, task_type: str, payload: dict | None = None, run_at: datetime | None = None, max_attempts: int = 3) -> JobQueue:
    job = JobQueue(agent=agent, task_type=task_type, payload=payload or {}, status="queued",
                   max_attempts=max_attempts, next_run_at=run_at)
    db.add(job)
    db.flush()
    return job


def claim_next(db, worker_id: str = WORKER_ID) -> JobQueue | None:
    now = datetime.utcnow()
    rows = (
        db.query(JobQueue)
        .filter(
            JobQueue.status == "queued",
            (JobQueue.next_run_at.is_(None)) | (JobQueue.next_run_at <= now),
            ((JobQueue.locked_until.is_(None)) | (JobQueue.locked_until <= now)),
        )
        .order_by(JobQueue.id)
        .limit(1)
        .all()
    )
    if not rows:
        return None
    job = rows[0]
    job.status = "running"
    job.locked_by = worker_id
    job.locked_until = now + timedelta(minutes=10)
    job.attempts += 1
    db.flush()
    return job


def complete(db, job: JobQueue, result: dict | None = None) -> None:
    job.status = "done"
    job.payload = {**(job.payload or {}), "result": result or {}}
    job.locked_by = None
    job.locked_until = None
    db.flush()


def fail(db, job: JobQueue, error: str) -> None:
    if job.attempts >= job.max_attempts:
        job.status = "dead"
        job.last_error = error
        job.locked_by = None
        job.locked_until = None
    else:
        job.status = "queued"
        job.last_error = error
        job.locked_by = None
        delay = min(60 * (2 ** (job.attempts - 1)), 3600)
        job.next_run_at = datetime.utcnow() + timedelta(seconds=delay)
    db.flush()


def release_stale(db, stale_minutes: int = 15) -> int:
    now = datetime.utcnow()
    rows = db.query(JobQueue).filter(JobQueue.status == "running", JobQueue.locked_until <= now).all()
    for r in rows:
        r.status = "queued"
        r.locked_by = None
        r.locked_until = None
    return len(rows)


def stats(db) -> dict[str, int]:
    from sqlalchemy import func
    q = db.query(JobQueue.status, func.count(JobQueue.id)).group_by(JobQueue.status).all()
    return {s: c for s, c in q}
