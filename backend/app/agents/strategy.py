"""Agent 05 — Content Strategy Agent: calendars, campaigns, platform-specific plans."""
from __future__ import annotations

from datetime import datetime, timedelta

from ..models import Campaign, ContentIdea, ContentItem, ContentVersion
from ..ai.content_engine import TOPICS, topic_by_id, daily_plan, caption_for, headline, hashtags_for, hedged_body
from .base import BaseAgent, register


@register
class StrategyAgent(BaseAgent):
    key = "strategy"
    name = "Content Strategy Agent"
    role = "Builds daily/weekly calendars, campaigns, series; assigns formats; creates platform-specific drafts."

    def run(self, task_type: str, payload: dict | None = None) -> dict:
        db = self.db
        plan = daily_plan(datetime.utcnow())
        if payload.get("plan"):
            plan = payload["plan"]

        # Ensure a campaign exists
        campaign = db.query(Campaign).filter(Campaign.status == "active").first()
        if campaign is None:
            campaign = Campaign(name="Evergreen Developmental Psychology Education", theme="Science of growing minds",
                                objective="awareness+leads", start_date=datetime.utcnow().strftime("%Y-%m-%d"),
                                end_date=(datetime.utcnow() + timedelta(days=30)).strftime("%Y-%m-%d"),
                                budget=0.0, status="active", config={"source": "strategy_agent"})
            db.add(campaign)
            db.flush()

        created = 0
        for item in plan:
            topic = topic_by_id(item["topic_id"])
            fmt = item["format"]
            title = headline(topic, variant=created)
            # dedupe by topic+format+day
            dup_key = f"{topic['id']}:{fmt}:{datetime.utcnow().strftime('%Y%m%d')}"
            existing = db.query(ContentItem).filter(ContentItem.duplicate_key == dup_key).first()
            if existing:
                continue
            body = hedged_body(topic)
            content = ContentItem(idea_id=None, campaign_id=campaign.id, topic=topic["title"], format=fmt,
                                  title=title, body=body, caption_variants={}, hashtags=hashtags_for(topic, "instagram"),
                                  status="draft", approval_required=bool(payload.get("approval_required", True)),
                                  duplicate_key=dup_key)
            db.add(content)
            db.flush()
            # Platform-specific versions (not blind duplication)
            for platform in item["platforms"]:
                cap = caption_for(platform, topic, variant=created)
                db.add(ContentVersion(content_id=content.id, platform=platform, headline=headline(topic, variant=created + 1),
                                      caption=cap, hashtags=hashtags_for(topic, platform), status="pending"))
            created += 1

        self.log("strategy_created", f"{created} content items drafted for campaign '{campaign.name}'")
        return {"status": "done", "created": created, "campaign": campaign.name, "plan_size": len(plan)}
