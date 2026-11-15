"""Agent 03 — Viral Trend Intelligence Agent: scores opportunities."""
from __future__ import annotations

import random
from datetime import datetime, timedelta

from ..models import ContentIdea, PlatformMetric, ResearchReport
from ..ai.content_engine import TOPICS, idea_score, pick_topics
from .base import BaseAgent, register


@register
class TrendsAgent(BaseAgent):
    key = "trends"
    name = "Viral Trend Intelligence Agent"
    role = "Researches trending educational topics, formats, keywords, hashtags and competitor signals; scores opportunities."

    def run(self, task_type: str, payload: dict | None = None) -> dict:
        db = self.db
        # Trend signal: engagement growth on own posts (lawful aggregate), plus freshness jitter.
        since = (datetime.utcnow() - timedelta(days=14)).strftime("%Y-%m-%d")
        metrics = db.query(PlatformMetric).filter(PlatformMetric.date >= since).all()
        by_date: dict[str, int] = {}
        for m in metrics:
            by_date[m.date] = by_date.get(m.date, 0) + m.impressions
        dates = sorted(by_date)
        growth = 0.0
        if len(dates) >= 2 and by_date[dates[0]] > 0:
            growth = (by_date[dates[-1]] - by_date[dates[0]]) / by_date[dates[0]]
        growth = max(-0.5, min(growth, 1.0))

        rng = random.Random(datetime.utcnow().strftime("%Y%m%d"))
        picked = pick_topics(6, seed=rng.randint(0, 10 ** 9))
        scored = []
        for t in picked:
            score = idea_score(t, trend=growth if growth > 0 else 0.2, seed=rng.randint(0, 10 ** 9))
            scored.append({"topic": t["title"], "score": score, "format": t["formats"][0]})
            existing = db.query(ContentIdea).filter(ContentIdea.topic == t["title"]).first()
            if existing is None:
                db.add(ContentIdea(topic=t["title"], angle=t["fact"], format=t["formats"][0],
                                   platform_targets=t["formats"], score=score, trend_score=round(score / 100, 2),
                                   status="new", source="trends_agent"))
        # Opportunity scoring rubric is documented; external trend APIs are marked unavailable without credentials.
        report = {
            "signals": {"own_engagement_growth_14d": round(growth, 3)},
            "opportunities": scored,
            "scoring": {"relevance": 0.22, "audience_interest": 0.16, "shareability": 0.16,
                        "educational_value": 0.18, "freshness": 0.12, "feasibility": 0.16},
            "external_sources": {
                "google_trends": "unavailable - no API credentials configured",
                "platform_trending_apis": "unavailable - platform tokens required",
            },
        }
        db.add(ResearchReport(title="Trend intelligence scan", kind="trend", topic="Educational psychology content",
                              summary=f"{len(scored)} opportunities scored; top: {scored[0]['topic'] if scored else 'n/a'}.",
                              data=report, source="trends_agent"))
        return {"status": "done", "opportunities": len(scored), "growth_signal": growth}
