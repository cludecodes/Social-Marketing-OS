"""Agent 08 — Copywriting Agent: headlines, captions, hashtags per platform."""
from __future__ import annotations

from ..models import ContentItem, ContentVersion
from ..ai.content_engine import TOPICS, caption_for, headline, hashtags_for, topic_by_id
from .base import BaseAgent, register


@register
class CopywriterAgent(BaseAgent):
    key = "copywriter"
    name = "Copywriting Agent"
    role = "Writes platform-native headlines, captions, CTAs, hashtags; avoids clickbait and keyword stuffing."


    def run(self, task_type: str, payload: dict | None = None) -> dict:
        db = self.db
        items = db.query(ContentItem).filter(ContentItem.status == "draft").limit(payload.get("limit", 10)).all()
        written = 0
        for item in items:
            if not item.body:
                continue
            topic = next((t for t in TOPICS if t["title"] == item.topic), None)
            if topic is None:
                topic = {"id": "custom", "title": item.topic, "fact": item.body, "audience": ["parents"], "evidence": "educational"}
            variants = {}
            for platform in ("instagram", "facebook", "pinterest", "youtube", "threads", "linkedin", "x", "tiktok"):
                variants[platform] = caption_for(platform, topic, variant=written % 3)
            item.caption_variants = variants
            item.hashtags = hashtags_for(topic, "instagram")
            if not item.title:
                item.title = headline(topic, variant=written)
            # Refresh per-platform versions
            for v in db.query(ContentVersion).filter(ContentVersion.content_id == item.id).all():
                v.caption = variants.get(v.platform, variants["instagram"])
                v.hashtags = hashtags_for(topic, v.platform)
            written += 1
        return {"status": "done", "items_written": written}
