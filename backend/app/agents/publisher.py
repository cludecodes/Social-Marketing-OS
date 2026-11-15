"""Agent 09 — Publishing & Distribution Agent."""
from __future__ import annotations

from datetime import datetime, timedelta

from ..models import ContentItem, ContentVersion, MediaAsset, PublishSchedule, PublishedPost, SocialAccount, Setting
from ..social.factory import adapter_for
from ..settings_store import get_settings
from ..audit import log_audit, notify
from .base import BaseAgent, register


@register
class PublisherAgent(BaseAgent):
    key = "publisher"
    name = "Publishing & Distribution Agent"
    role = "Publishes approved content to connected accounts via official APIs; respects limits, schedules, kill switch; retries safely; prevents duplicates."

    def run(self, task_type: str, payload: dict | None = None) -> dict:
        db = self.db
        s = get_settings()
        autonomous = bool(s.get("autonomous_publishing", False))
        if not autonomous and not payload.get("force"):
            return {"status": "skipped", "reason": "autonomous publishing disabled (kill switch)"}

        now = datetime.utcnow()
        due = db.query(PublishSchedule).filter(PublishSchedule.scheduled_at <= now,
                                               PublishSchedule.status == "scheduled").limit(payload.get("limit", 10)).all()
        published, failed, skipped = [], [], []
        for sched in due:
            item = db.query(ContentItem).filter_by(id=sched.content_id).first()
            account = db.query(SocialAccount).filter_by(id=sched.account_id).first()
            if not item or not account:
                sched.status = "cancelled"
                continue
            if item.status not in ("approved", "published"):
                skipped.append({"schedule": sched.id, "reason": f"content status {item.status}"}); continue
            if account.status != "active" or not account.auto_publish:
                skipped.append({"schedule": sched.id, "reason": "account inactive/auto_publish off"}); continue
            # Daily limit
            day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            today_count = db.query(PublishedPost).filter(PublishedPost.account_id == account.id,
                                                         PublishedPost.published_at >= day_start).count()
            if today_count >= int(account.daily_limit or 0):
                skipped.append({"schedule": sched.id, "reason": "daily limit reached"}); continue
            # Duplicate prevention
            dup = db.query(PublishedPost).filter_by(account_id=account.id, content_id=item.id).first()
            if dup:
                sched.status = "published"
                sched.post_url = dup.url
                continue
            version = db.query(ContentVersion).filter(ContentVersion.content_id == item.id,
                                                      ContentVersion.platform == account.platform).first()
            text = version.caption if version else (item.body or "")
            media = [db.query(MediaAsset).filter_by(id=m).first() for m in (item.media_ids or [])]
            media = [m for m in media if m]
            try:
                sched.status = "publishing"
                adapter = adapter_for(account.platform)
                meta = {"title": item.title, "hashtags": version.hashtags if version else item.hashtags,
                        "alt_text": item.title, "image_url": (account.config or {}).get("media_host_url", "")}
                paths = [m.path for m in media if m.path]
                result = adapter.publish(account, text, paths if paths else None, meta)
                if result.get("ok"):
                    sched.status = "published"
                    sched.published_at = now
                    sched.post_id = result.get("post_id")
                    sched.post_url = result.get("url")
                    db.add(PublishedPost(account_id=account.id, content_id=item.id, platform_post_id=result.get("post_id"),
                                         url=result.get("url"), published_at=now, metrics={"result": "ok"}))
                    published.append({"schedule": sched.id, "post_id": result.get("post_id")})
                    notify(db, "info", "Published", f"{account.platform} post for '{item.topic[:40]}'")
                else:
                    raise RuntimeError(result.get("error", "publish failed"))
            except Exception as exc:  # noqa: BLE001
                sched.attempts += 1
                sched.error = str(exc)[:500]
                sched.status = "failed" if sched.attempts >= 3 else "scheduled"
                if sched.status == "scheduled":
                    sched.scheduled_at = now + timedelta(minutes=15 * sched.attempts)
                failed.append({"schedule": sched.id, "error": sched.error})
                log_audit(db, "agent:publisher", "publish_failed", "schedule", sched.id, sched.error)
        return {"status": "done", "published": published, "failed": failed, "skipped": skipped,
                "autonomous": autonomous}
