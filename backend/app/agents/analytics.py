"""Agent 11 — Analytics & Growth Agent."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta

from ..models import ContentIdea, ContentItem, PlatformMetric, PublishedPost, PublishSchedule, SocialAccount
from ..social.factory import adapter_for
from ..audit import log_audit
from .base import BaseAgent, register


@register
class AnalyticsAgent(BaseAgent):
    key = "analytics"
    name = "Analytics & Growth Agent"
    role = "Collects metrics from authorized APIs; computes engagement rates, top content, best times; feeds optimization back into strategy."

    def run(self, task_type: str, payload: dict | None = None) -> dict:
        db = self.db
        since = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
        until = datetime.utcnow().strftime("%Y-%m-%d")
        accounts = db.query(SocialAccount).filter(SocialAccount.status == "active").all()
        collected = 0
        for acc in accounts:
            try:
                adapter = adapter_for(acc.platform)
                data = adapter.insights(acc, since, until)
            except Exception as e:  # noqa: BLE001
                self.log("insights_failed", f"{acc.platform}: {str(e)[:120]}")
                continue
            if not data or "error" in data or "unavailable" in data:
                continue
            # Map platform metrics into PlatformMetric (best-effort normalization)
            impressions = reach = likes = comments_ = shares = saves = followers = clicks = views = 0
            for entry in (data.get("data") or []):
                name = entry.get("name", "")
                val = entry.get("values", [{}])[0].get("value", 0)
                if isinstance(val, dict):
                    val = val.get("value", 0)
                val = int(val or 0)
                if "impression" in name:
                    impressions += val
                if "reach" in name:
                    reach += val
                if "engaged" in name or "engagement" in name:
                    likes += val
                if "follower" in name:
                    followers += val
            row = db.query(PlatformMetric).filter_by(account_id=acc.id, date=until).first()
            if row is None:
                row = PlatformMetric(account_id=acc.id, date=until)
                db.add(row)
            row.impressions, row.reach, row.likes, row.comments, row.shares, row.saves = impressions, reach, likes, comments_, shares, saves
            row.followers, row.views, row.clicks = followers, views, clicks
            collected += 1

        # Engagement rate + top posts + best times
        metrics = db.query(PlatformMetric).filter(PlatformMetric.date >= since).all()
        impressions = sum(m.impressions for m in metrics)
        engagements = sum(m.likes + m.comments + m.shares + m.saves for m in metrics)
        er = round(100 * engagements / max(impressions, 1), 2)

        hour_scores = Counter()
        for p in db.query(PublishedPost).all():
            if p.published_at:
                score = sum((p.metrics or {}).get(k, 0) for k in ("likes", "comments", "shares", "saves"))
                hour_scores[p.published_at.hour] += score
        best_hours = [h for h, _ in hour_scores.most_common(3)]

        top = []
        for p in db.query(PublishedPost).all():
            score = sum((p.metrics or {}).get(k, 0) for k in ("likes", "comments", "shares", "saves"))
            ci = db.query(ContentItem).filter_by(id=p.content_id).first()
            if ci:
                top.append({"content_id": ci.id, "topic": ci.topic, "score": score})
        top.sort(key=lambda x: x["score"], reverse=True)

        # Feed back: boost ideas matching top topics
        for t in top[:3]:
            idea = db.query(ContentIdea).filter(ContentIdea.topic.ilike(f"%{t['topic'][:30]}%")).first()
            if idea:
                idea.score = min(100, idea.score + 5)

        report = {"engagement_rate_pct": er, "impressions_1d": impressions, "engagements_1d": engagements,
                  "best_hours": best_hours, "top_posts": top[:5], "accounts_measured": collected,
                  "method": "Aggregated authorized platform insights where APIs expose them; fallback uses local engagement heuristics."}
        from ..models import ResearchReport
        db.add(ResearchReport(title="Daily analytics digest", kind="analytics", topic="Performance",
                              summary=f"ER {er}%; best hours {best_hours}; top: {top[0]['topic'] if top else 'n/a'}",
                              data=report, source="analytics_agent"))
        return {"status": "done", "engagement_rate": er, "best_hours": best_hours, "accounts_measured": collected}
