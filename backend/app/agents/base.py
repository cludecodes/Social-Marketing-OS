"""Agent base class + registry."""
from __future__ import annotations

from typing import Any

from ..db import db_session
from ..models import AIAgent, AgentTask
from ..audit import log_audit, notify


class BaseAgent:
    key: str = ""
    name: str = ""
    role: str = ""

    def __init__(self, db):
        self.db = db

    def ensure_registered(self) -> None:
        row = self.db.query(AIAgent).filter_by(key=self.key).first()
        if row is None:
            self.db.add(AIAgent(key=self.key, name=self.name, role=self.role, enabled=True))
            self.db.flush()

    def is_enabled(self) -> bool:
        row = self.db.query(AIAgent).filter_by(key=self.key).first()
        return bool(row and row.enabled)

    def mark_run(self, status: str = "idle") -> None:
        row = self.db.query(AIAgent).filter_by(key=self.key).first()
        if row:
            from datetime import datetime
            row.last_run_at = datetime.utcnow()
            row.status = status

    def log(self, action: str, detail: str = None) -> None:
        log_audit(self.db, actor=f"agent:{self.key}", action=action, entity="agent_task", detail=detail)

    def alert(self, level: str, title: str, message: str) -> None:
        notify(self.db, level=level, title=title, message=message)

    def run(self, task_type: str, payload: dict | None = None) -> dict:
        raise NotImplementedError


REGISTRY: dict[str, type[BaseAgent]] = {}


def register(cls):
    REGISTRY[cls.key] = cls
    return cls


def ensure_all_registered(db) -> None:
    for cls in REGISTRY.values():
        cls(db).ensure_registered()
    db.commit()


def run_agent(db, key: str, task_type: str, payload: dict | None = None) -> dict:
    cls = REGISTRY.get(key)
    if cls is None:
        raise KeyError(f"Unknown agent {key}")
    if db.query(AIAgent).filter_by(key=key).first() is None:
        cls(db).ensure_registered()
        db.commit()
    agent = cls(db)
    if not agent.is_enabled():
        return {"status": "skipped", "reason": "agent disabled", "agent": key}
    agent.mark_run("running")
    try:
        result = agent.run(task_type, payload or {})
        result["agent"] = key
        result["status"] = result.get("status", "done")
        agent.log("agent_run", f"{task_type} -> {result['status']}")
        return result
    except Exception as exc:  # noqa: BLE001
        agent.alert("error", f"Agent {key} failed", str(exc)[:500])
        raise
    finally:
        agent.mark_run("idle")
