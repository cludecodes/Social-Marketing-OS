"""Orchestrator: maps pipeline steps to agents; runs sequentially or via job queue."""
from __future__ import annotations

from typing import Any

from .db import db_session
from .models import AgentTask, JobQueue
from .automation.queue import enqueue
from .audit import log_audit
from .agents.base import run_agent

STEPS: dict[str, list[tuple[str, str]]] = {
    "research": [("audience", "audience_scan"), ("trends", "trend_scan"), ("research", "education_brief")],
    "strategy": [("strategy", "build_calendar")],
    "create": [("copywriter", "write_variants"), ("designer", "generate_visuals"), ("video", "produce_videos")],
    "qa": [("qa", "review_content")],
    "publish": [("publisher", "publish_due")],
    "analytics": [("analytics", "collect_metrics")],
    "optimize": [("cmo", "weekly_objective")],
}

STEP_TIMES = ["research", "strategy", "create", "qa", "publish", "analytics", "optimize"]


def run_step(step: str, payload: dict | None = None, use_queue: bool = False) -> dict:
    payload = payload or {}
    results = []
    with db_session() as db:
        for key, task_type in STEPS.get(step, []):
            if use_queue:
                enqueue(db, agent=key, task_type=task_type, payload=payload)
                results.append({"agent": key, "status": "queued"})
                continue
            try:
                res = run_agent(db, key, task_type, payload)
            except Exception as exc:  # noqa: BLE001
                res = {"agent": key, "status": "failed", "error": str(exc)[:300]}
            results.append(res)
        db.commit()
    return {"step": step, "results": results}


def run_pipeline(use_queue: bool = False) -> dict:
    out = {}
    for step in STEP_TIMES:
        out[step] = run_step(step, use_queue=use_queue)
    return out


def run_single_agent(key: str, task_type: str, payload: dict | None = None) -> dict:
    with db_session() as db:
        return run_agent(db, key, task_type, payload or {})


def process_queue(max_jobs: int = 5) -> dict:
    """Worker loop: claim, execute, complete/fail with retry + stale lock release."""
    from .automation.queue import claim_next, complete, fail, release_stale
    done, failed = [], []
    with db_session() as db:
        release_stale(db)
        for _ in range(max_jobs):
            job = claim_next(db)
            if job is None:
                break
            try:
                res = run_agent(db, job.agent, job.task_type, job.payload or {})
                complete(db, job, res)
                done.append({"job": job.id, "agent": job.agent})
            except Exception as exc:  # noqa: BLE001
                fail(db, job, str(exc)[:500])
                failed.append({"job": job.id, "agent": job.agent, "error": str(exc)[:200]})
    return {"done": done, "failed": failed}


def enqueue_step(step: str, run_at=None) -> dict:
    with db_session() as db:
        for key, task_type in STEPS.get(step, []):
            enqueue(db, agent=key, task_type=task_type, payload={}, run_at=run_at)
    return {"queued": step}
