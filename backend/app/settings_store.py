"""Runtime settings store (persisted admin-configurable settings)."""
from __future__ import annotations

import json
from typing import Any

from .config import settings
from .db import db_session
from .models import Setting

DEFAULTS: dict[str, Any] = {
    "brand_name": settings.BRAND_NAME,
    "brand_industry": settings.BRAND_INDUSTRY,
    "brand_colors": settings.BRAND_COLORS,
    "timezone": settings.TIMEZONE,
    "automation_enabled": True,
    "autonomous_publishing": settings.AUTONOMOUS_PUBLISHING,
    "auto_content_generation": settings.AUTO_CONTENT_GENERATION,
    "auto_scheduling": settings.AUTO_SCHEDULING,
    "auto_community_responses": settings.AUTO_COMMUNITY_RESPONSES,
    "require_approval": settings.REQUIRE_APPROVAL,
    "max_daily_posts": settings.MAX_DAILY_POSTS,
    "qa_min_score": settings.QA_MIN_SCORE,
    "schedule_research": settings.SCHEDULE["research"],
    "schedule_strategy": settings.SCHEDULE["strategy"],
    "schedule_create": settings.SCHEDULE["create"],
    "schedule_qa": settings.SCHEDULE["qa"],
    "schedule_publish_1": settings.SCHEDULE["publish_1"],
    "schedule_publish_2": settings.SCHEDULE["publish_2"],
    "schedule_publish_3": settings.SCHEDULE["publish_3"],
    "schedule_analytics": settings.SCHEDULE["analytics"],
    "schedule_optimize": settings.SCHEDULE["optimize"],
    "campaign_budget": 0.0,
    "posting_window_start": "09:00",
    "posting_window_end": "21:00",
    "best_times": "",
    "email_notifications": True,
}


def get_settings() -> dict[str, Any]:
    rows: dict[str, str] = {}
    with db_session() as db:
        for r in db.query(Setting).all():
            rows[r.key] = r.value
    out = dict(DEFAULTS)
    for k, v in rows.items():
        try:
            out[k] = json.loads(v)
        except Exception:
            out[k] = v
    return out


def set_settings(values: dict[str, Any]) -> dict[str, Any]:
    with db_session() as db:
        for k, v in values.items():
            if k not in DEFAULTS:
                continue
            row = db.query(Setting).filter_by(key=k).first()
            if row is None:
                row = Setting(key=k)
                db.add(row)
            row.value = json.dumps(v) if not isinstance(v, str) else v
    return get_settings()


def get_setting(key: str) -> Any:
    return get_settings().get(key, DEFAULTS.get(key))


def get_schedule() -> dict[str, str]:
    s = get_settings()
    return {
        "research": s.get("schedule_research", "06:00"),
        "strategy": s.get("schedule_strategy", "07:00"),
        "create": s.get("schedule_create", "08:00"),
        "qa": s.get("schedule_qa", "09:00"),
        "publish_1": s.get("schedule_publish_1", "10:00"),
        "publish_2": s.get("schedule_publish_2", "13:00"),
        "publish_3": s.get("schedule_publish_3", "17:00"),
        "analytics": s.get("schedule_analytics", "20:00"),
        "optimize": s.get("schedule_optimize", "21:00"),
    }
