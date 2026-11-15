"""Agent 01 — Chief Marketing Officer: strategy, objectives, resource allocation."""
from __future__ import annotations

from datetime import datetime, timedelta

from ..db import db_session
from ..models import Campaign, ContentItem, PlatformMetric, ResearchReport, Setting
from ..audit import log_audit, notify
from .base import BaseAgent, register


@register
class CMOAgent(BaseAgent):
    key = "cmo"
    name = "Chief Marketing Officer"
    role = "Coordinates marketing agents, sets weekly/monthly growth objectives, allocates production resources, monitors campaigns."

    def run(self, task_type: str, payload: dict | None = None) -> dict:
        db = self.db
        s = {r.key: r.value for r in db.query(Setting).all()}
        max_daily = int(s.get("max_daily_posts", "6")) if isinstance(s.get("max_daily_posts"), str) else int(s.get("max_daily_posts", 6) or 6)

        # Aggregate last-7-day performance
        since = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
        metrics = db.query(PlatformMetric).filter(PlatformMetric.date >= since).all()
        impressions = sum(m.impressions for m in metrics)
        engagements = sum(m.likes + m.comments + m.shares + m.saves for m in metrics)
        followers = sum(m.followers for m in metrics)
        er = round(100.0 * engagements / max(impressions, 1), 2)

        published = db.query(ContentItem).filter(ContentItem.status == "published").count()
        active_campaigns = db.query(Campaign).filter(Campaign.status == "active").count()

        objective = {
            "period": "weekly",
            "generated_at": datetime.utcnow().isoformat(),
            "kpis": {
                "posts_per_day": max_daily,
                "engagement_rate_target_pct": 4.0,
                "current_engagement_rate_pct": er,
                "impressions_7d": impressions,
                "engagements_7d": engagements,
                "followers_total": followers,
                "leads_target_week": 20,
                "registrations_target_week": 5,
            },
            "allocations": {
                "research_pct": 10,
                "creation_pct": 40,
                "visuals_pct": 25,
                "qa_pct": 5,
                "publishing_pct": 10,
                "community_pct": 5,
                "analytics_pct": 5,
            },
            "actions": [
                "Prioritize formats with engagement rate above 4% (see Analytics Agent).",
                "Pause topics scoring below 50/100 in the opportunity score.",
                "Keep daily posts within admin-configured limit (%d)." % max_daily,
            ],
            "budget_note": "Budget is admin-configured; no spend occurs without a connected ad platform and explicit budget." if not active_campaigns else f"{active_campaigns} active campaign(s) monitored.",
        }

        db.add(ResearchReport(title="Weekly marketing objective", kind="strategy", topic="CMO review",
                              summary=f"Engagement rate {er}% over 7d; {published} posts published; {active_campaigns} campaigns active.",
                              data=objective, source="cmo_agent"))
        notify(db, "info", "CMO weekly objective set", f"Target ER 4% (current {er}%); daily post cap {max_daily}.")
        return {"status": "done", "objective": objective}
