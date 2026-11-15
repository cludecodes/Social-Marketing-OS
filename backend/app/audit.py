"""Audit log + system notifications helpers."""
from __future__ import annotations

from datetime import datetime

from .db import db_session
from .models import AuditLog, SystemNotification


def log_audit(db, actor: str, action: str, entity: str | None = None, entity_id: str | None = None, detail: str | None = None, ip: str | None = None) -> None:
    db.add(AuditLog(actor=actor, action=action, entity=entity, entity_id=str(entity_id) if entity_id else None, detail=detail, ip=ip))


def notify(db, level: str, title: str, message: str) -> None:
    db.add(SystemNotification(level=level, title=title, message=message))


def now_iso() -> str:
    return datetime.utcnow().isoformat()
