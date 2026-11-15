"""Agent 10 — Community Engagement Agent (safe, escalation-first)."""
from __future__ import annotations

from datetime import datetime, timedelta

from ..models import Comment, SocialAccount, SystemNotification
from ..social.factory import adapter_for
from ..settings_store import get_settings
from ..audit import log_audit, notify
from .base import BaseAgent, register

RISK_KEYWORDS = ["suicide", "kill myself", "self-harm", "self harm", "end it all", "no reason to live",
                 "hopeless", "abuse", "emergency", "panic attack", "overdose", "cutting", "die"]

SAFE_REPLIES = [
    "Thanks for sharing — great question. This is general educational info, not medical advice; please consult a qualified professional for personal concerns.",
    "Good question! We cover this in our free guide — link in bio. For personal concerns, please speak with a licensed professional.",
    "Appreciate you asking. Every child is different; wide ranges are normal. For specific concerns, a professional evaluation is best.",
]


@register
class CommunityAgent(BaseAgent):
    key = "community"
    name = "Community Engagement Agent"
    role = "Monitors comments/questions where APIs allow; drafts safe educational replies; escalates crisis/sensitive messages to a human; never fakes engagement."

    def run(self, task_type: str, payload: dict | None = None) -> dict:
        db = self.db
        s = get_settings()
        auto = bool(s.get("auto_community_responses", False))
        since = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
        accounts = db.query(SocialAccount).filter(SocialAccount.status == "active").all()
        fetched, replied, escalated = 0, 0, 0
        for acc in accounts:
            try:
                adapter = adapter_for(acc.platform)
                comments = adapter.comments(acc, since)
            except Exception as e:  # noqa: BLE001
                self.log("comments_fetch_failed", f"{acc.platform}: {str(e)[:120]}")
                continue
            for c in comments:
                fetched += 1
                exists = db.query(Comment).filter_by(account_id=acc.id, platform_comment_id=c.get("id")).first()
                if exists:
                    continue
                text = (c.get("text") or "").lower()
                risk = any(k in text for k in RISK_KEYWORDS)
                row = Comment(account_id=acc.id, platform_comment_id=c.get("id"), author=c.get("author", ""),
                              text=c.get("text", ""), sentiment="risk" if risk else "neutral",
                              risk_flag=risk, status="escalated" if risk else "open")
                if risk:
                    escalated += 1
                    notify(db, "critical", "Sensitive comment escalated",
                           f"{acc.platform} comment by {c.get('author')}: {c.get('text')[:200]} — human review required")
                elif auto and adapter.caps.publish:
                    reply = SAFE_REPLIES[fetched % len(SAFE_REPLIES)]
                    # Auto-reply only via supported comment endpoints; most platforms lack them -> stored for review
                    row.reply = reply
                    row.status = "open"  # stays open; admin sends via approved flow
                    replied += 1
                db.add(row)
        db.flush()
        return {"status": "done", "comments_fetched": fetched, "replies_drafted": replied, "escalated": escalated,
                "auto_responses": auto}
