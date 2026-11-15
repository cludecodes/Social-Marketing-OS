"""All REST API routes for the Shophippy Marketing OS admin control center."""
from __future__ import annotations

import json
import os
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse

from ..ai import content_engine as ce
from ..ai.providers import registry
from ..audit import log_audit, notify
from ..automation import queue as jobq
from ..automation.scheduler import reschedule
from ..config import settings
from ..db import db_session
from ..media.image_generator import ImageGenerator
from ..media.pdf import make_pdf
from ..media.video_generator import VideoGenerator, ffmpeg_available
from ..models import (AuditLog, AIAgent, AgentTask, AudiencePersona, Campaign, Comment, ContentIdea, ContentItem,
                      ContentVersion, JobQueue, Lead, MediaAsset, OAuthCredential, PlatformMetric, PublishSchedule,
                      PublishedPost, ResearchReport, Setting, SocialAccount, SystemNotification, User)
from ..orchestrator import run_agent, run_step, run_single_agent
from ..security import decrypt_value, encrypt_value
from ..settings_store import get_schedule, get_settings, set_settings
from ..social import factory as social_factory
from .auth import get_current_user

router = APIRouter(dependencies=[Depends(get_current_user)])
public_router = APIRouter()


def _serialize(row) -> dict:
    if row is None:
        return {}
    out = {}
    for c in row.__table__.columns:
        v = getattr(row, c.name)
        if isinstance(v, datetime):
            v = v.isoformat()
        out[c.name] = v
    return out


def _list(rows):
    return [_serialize(r) for r in rows]


# ---------- Health / status ----------
@public_router.get("/health")
def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat(), "app": settings.APP_NAME}


@router.get("/status")
def status():
    with db_session() as db:
        accounts = db.query(SocialAccount).count()
        drafts = db.query(ContentItem).filter(ContentItem.status == "draft").count()
        scheduled = db.query(PublishSchedule).filter(PublishSchedule.status == "scheduled").count()
        published = db.query(PublishedPost).count()
        failed = db.query(JobQueue).filter(JobQueue.status == "dead").count()
        s = get_settings()
    return {"provider": registry.status(), "accounts": accounts, "drafts": drafts, "scheduled": scheduled,
            "published": published, "dead_jobs": failed, "autonomous_publishing": s.get("autonomous_publishing"),
            "automation_enabled": s.get("automation_enabled"), "schedule": get_schedule(),
            "schedule_source": "settings store (PKT default)", "timezone": settings.TIMEZONE}


@router.get("/overview")
def overview():
    with db_session() as db:
        today = datetime.utcnow().strftime("%Y-%m-%d")
        published_today = db.query(PublishedPost).filter(PublishedPost.published_at >= datetime.utcnow().replace(hour=0, minute=0, second=0)).count()
        scheduled = db.query(PublishSchedule).filter(PublishSchedule.status == "scheduled").count()
        pending_qa = db.query(ContentItem).filter(ContentItem.status == "qa_pending").count()
        accounts = db.query(SocialAccount).count()
        metrics = db.query(PlatformMetric).filter(PlatformMetric.date >= (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")).all()
        impressions = sum(m.impressions for m in metrics)
        engagements = sum(m.likes + m.comments + m.shares + m.saves for m in metrics)
        followers = sum(m.followers for m in metrics) or db.query(SocialAccount).count() * 100
        leads = db.query(Lead).count()
        campaigns = db.query(Campaign).filter(Campaign.status == "active").count()
        failed_jobs = db.query(JobQueue).filter(JobQueue.status == "dead").count()
        er = round(100 * engagements / max(impressions, 1), 2)
    return {"accounts": accounts, "published_today": published_today, "scheduled": scheduled, "pending_qa": pending_qa,
            "impressions_30d": impressions, "engagement_rate_pct": er, "followers": followers, "leads": leads,
            "active_campaigns": campaigns, "failed_jobs": failed_jobs}


# ---------- Agents & tasks ----------
@router.get("/agents")
def agents():
    with db_session() as db:
        return _list(db.query(AIAgent).order_by(AIAgent.id).all())


@router.post("/agents/{key}/toggle")
def agent_toggle(key: str):
    with db_session() as db:
        a = db.query(AIAgent).filter_by(key=key).first()
        if not a:
            raise HTTPException(404)
        a.enabled = not a.enabled
        log_audit(db, "admin", "agent_toggle", "agent", a.id, f"enabled={a.enabled}")
        return _serialize(a)


@router.post("/agents/{key}/run")
def agent_run(key: str, payload: dict | None = None):
    with db_session() as db:
        res = run_agent(db, key, (payload or {}).get("task_type", "run"), payload or {})
    return res


@router.get("/tasks")
def tasks():
    with db_session() as db:
        return _list(db.query(AgentTask).order_by(AgentTask.id.desc()).limit(50).all())


@router.get("/jobs")
def jobs():
    with db_session() as db:
        rows = db.query(JobQueue).order_by(JobQueue.id.desc()).limit(50).all()
        return _list(rows)


@router.post("/jobs/process")
def jobs_process():
    from ..orchestrator import process_queue
    return process_queue(max_jobs=10)


# ---------- Research ----------
@router.get("/research")
def research():
    with db_session() as db:
        return _list(db.query(ResearchReport).order_by(ResearchReport.id.desc()).limit(50).all())


@router.post("/research/run")
def research_run(kind: str = "audience"):
    mapping = {"audience": "audience", "trend": "trends", "education": "research", "analytics": "analytics"}
    key = mapping.get(kind, "audience")
    return run_single_agent(key, "run")


@router.get("/personas")
def personas():
    with db_session() as db:
        return _list(db.query(AudiencePersona).all())


@router.get("/ideas")
def ideas():
    with db_session() as db:
        return _list(db.query(ContentIdea).order_by(ContentIdea.id.desc()).limit(100).all())


@router.post("/ideas/score")
def ideas_score():
    return run_single_agent("trends", "trend_scan")


# ---------- Content ----------
@router.get("/content")
def content_list(status: str | None = None, limit: int = 50):
    with db_session() as db:
        q = db.query(ContentItem)
        if status:
            q = q.filter(ContentItem.status == status)
        return _list(q.order_by(ContentItem.id.desc()).limit(limit).all())


@router.post("/content")
def content_create(item: dict):
    with db_session() as db:
        ci = ContentItem(topic=item.get("topic", "New topic"), format=item.get("format", "post"),
                         title=item.get("title"), body=item.get("body"),
                         caption_variants=item.get("caption_variants", {}), hashtags=item.get("hashtags", []),
                         status=item.get("status", "draft"), approval_required=bool(item.get("approval_required", True)),
                         duplicate_key=ce.duplicate_key(item.get("body") or item.get("topic", "")))
        db.add(ci)
        db.flush()
        for platform in item.get("platforms", ["instagram"]):
            db.add(ContentVersion(content_id=ci.id, platform=platform, headline=item.get("title"),
                                  caption=item.get("caption") or item.get("body") or "", hashtags=item.get("hashtags", [])))
        log_audit(db, "admin", "content_create", "content", ci.id, item.get("topic"))
        return _serialize(ci)


@router.get("/content/{id}")
def content_get(id: int):
    with db_session() as db:
        ci = db.query(ContentItem).filter_by(id=id).first()
        if not ci:
            raise HTTPException(404)
        data = _serialize(ci)
        data["versions"] = _list(db.query(ContentVersion).filter(ContentVersion.content_id == id).all())
        data["media"] = _list(db.query(MediaAsset).filter(MediaAsset.id.in_(ci.media_ids or [])).all())
        return data


@router.put("/content/{id}")
def content_update(id: int, patch: dict):
    with db_session() as db:
        ci = db.query(ContentItem).filter_by(id=id).first()
        if not ci:
            raise HTTPException(404)
        for k in ("topic", "format", "title", "body", "caption_variants", "hashtags", "status", "media_ids"):
            if k in patch:
                setattr(ci, k, patch[k])
        log_audit(db, "admin", "content_update", "content", id, list(patch.keys()))
        return _serialize(ci)


@router.post("/content/{id}/approve")
def content_approve(id: int):
    with db_session() as db:
        ci = db.query(ContentItem).filter_by(id=id).first()
        if not ci:
            raise HTTPException(404)
        ci.status = "approved"
        log_audit(db, "admin", "content_approve", "content", id)
        return _serialize(ci)


@router.post("/content/generate")
def content_generate(count: int = 5):
    plan = ce.daily_plan(max_posts=count)
    res = run_step("strategy", {"plan": plan, "approval_required": bool(get_settings().get("require_approval"))})
    return res


@router.post("/content/{id}/schedule")
def content_schedule(id: int, sched: dict):
    account_id = sched.get("account_id")
    if not sched.get("scheduled_at"):
        raise HTTPException(400, "scheduled_at is required")
    at = datetime.fromisoformat(sched["scheduled_at"].replace("Z", "+00:00").replace("+00:00", ""))
    if at < datetime.utcnow():
        raise HTTPException(400, "scheduled_at must be in the future")
    with db_session() as db:
        ci = db.query(ContentItem).filter_by(id=id).first()
        if not ci:
            raise HTTPException(404, "content not found")
        if ci.status not in ("approved", "scheduled"):
            raise HTTPException(400, "only approved content can be scheduled")
        if not account_id:
            raise HTTPException(400, "account_id is required")
        account = db.query(SocialAccount).filter_by(id=account_id).first()
        if not account:
            raise HTTPException(404, "social account not found")
        ps = PublishSchedule(content_id=id, account_id=account_id, scheduled_at=at, status="scheduled")
        db.add(ps)
        db.flush()
        log_audit(db, "admin", "content_schedule", "schedule", ps.id, f"at {at.isoformat()} account {account_id}")
        return {"ok": True, "schedule_id": ps.id}


@router.get("/calendar")
def calendar(start: str = Query(None), end: str = Query(None)):
    with db_session() as db:
        q = db.query(PublishSchedule, ContentItem).join(ContentItem, PublishSchedule.content_id == ContentItem.id)
        rows = q.order_by(PublishSchedule.scheduled_at).limit(200).all()
        out = []
        for s, ci in rows:
            out.append({"id": s.id, "content_id": s.content_id, "title": ci.title or ci.topic, "status": s.status,
                        "scheduled_at": s.scheduled_at.isoformat(), "account_id": s.account_id,
                        "platform": (db.query(SocialAccount).filter_by(id=s.account_id).first() or SocialAccount(platform="")).platform})
        return out


# ---------- Media ----------
@router.get("/media")
def media_list():
    with db_session() as db:
        return _list(db.query(MediaAsset).order_by(MediaAsset.id.desc()).limit(100).all())


@router.post("/media/generate-image")
def media_image(payload: dict):
    gen = ImageGenerator(settings.MEDIA_DIR, settings.BRAND_COLORS, settings.BRAND_NAME)
    out = gen.render(payload.get("format", "infographic"), payload.get("title", "Educational graphic"),
                     payload.get("subtitle", ""), brand=settings.BRAND_NAME)
    with db_session() as db:
        asset = MediaAsset(kind="image", path=out["path"], filename=os.path.basename(out["path"]), mime=out["mime"],
                           width=out["width"], height=out["height"], size=out["size"],
                           meta={"template": out["template"], "engine": out["engine"]})
        db.add(asset)
        db.flush()
        return _serialize(asset)


@router.post("/media/generate-video")
def media_video(payload: dict):
    if not ffmpeg_available():
        raise HTTPException(400, "ffmpeg not available")
    scenes = payload.get("scenes") or [{"text": s} for s in [payload.get("title", "Hook"), "Key fact", "Practical tip", "Follow us"]]
    gen = VideoGenerator(settings.MEDIA_DIR, settings.BRAND_COLORS, settings.BRAND_NAME)
    tts_bytes = None
    if payload.get("voice", True):
        try:
            tts_bytes = registry.tts(" ".join(s["text"] if isinstance(s, dict) else s for s in scenes))
        except Exception:
            tts_bytes = None
    out = gen.render(payload.get("title", "Lesson"), scenes, aspect=payload.get("aspect", "9:16"),
                     tts_bytes=tts_bytes, per_scene=int(payload.get("per_scene", 8)))
    with db_session() as db:
        asset = MediaAsset(kind="video", path=out["path"], filename=os.path.basename(out["path"]), mime=out["mime"],
                           width=out["width"], height=out["height"], size=out["size"],
                            meta={"engine": out["engine"], "audio": out["audio"], "scenes": out["scenes"]})
        db.add(asset)
        db.flush()
        return _serialize(asset)


@router.get("/media/{id}/file")
def media_file(id: int):
    with db_session() as db:
        a = db.query(MediaAsset).filter_by(id=id).first()
        if not a:
            raise HTTPException(404)
        return FileResponse(a.path)


@router.post("/media/guide-pdf")
def media_guide(content_id: int | None = None, topic: str | None = None):
    topic = topic or "Developmental Psychology Guide"
    lines = [f"{settings.BRAND_NAME} - Free Guide", topic, ""]
    if content_id:
        with db_session() as db:
            ci = db.query(ContentItem).filter_by(id=content_id).first()
            if ci:
                lines += [ci.title or "", ci.body or "", ""]
    lines += ["Key takeaways:", "- Development follows predictable sequences with wide normal ranges.",
              "- Use age-appropriate expectations; avoid labels.", "- Evidence beats anecdotes.",
              "", "This guide is educational only and is not medical advice."]
    fname = f"guide_{abs(hash(topic)) % 100000}.pdf"
    path = settings.MEDIA_DIR / fname
    make_pdf(path, topic, lines)
    return {"path": str(path), "filename": fname}


@router.get("/media/{id}/download")
def media_download(id: int):
    with db_session() as db:
        a = db.query(MediaAsset).filter_by(id=id).first()
        if not a:
            raise HTTPException(404)
        return FileResponse(a.path, filename=a.filename)


# ---------- Social accounts & OAuth ----------
@router.get("/accounts")
def accounts():
    with db_session() as db:
        rows = db.query(SocialAccount).all()
        out = []
        for r in rows:
            d = _serialize(r)
            d["scopes"] = (r.scopes or "").split(",") if r.scopes else []
            out.append(d)
        return out


@router.post("/accounts")
def account_create(acc: dict):
    with db_session() as db:
        row = SocialAccount(platform=acc["platform"], account_id=acc.get("account_id", str(uuid.uuid4())[:8]),
                            name=acc.get("name", acc["platform"]), handle=acc.get("handle", ""),
                            access_token_enc=encrypt_value(acc.get("access_token", "")),
                            refresh_token_enc=encrypt_value(acc.get("refresh_token", "")),
                            scopes=acc.get("scopes", ""), status="active",
                            auto_publish=bool(acc.get("auto_publish", True)), daily_limit=int(acc.get("daily_limit", 3)),
                            config=acc.get("config", {}))
        db.add(row)
        db.flush()
        log_audit(db, "admin", "account_connect", "account", row.id, acc["platform"])
        return _serialize(row)


@router.delete("/accounts/{id}")
def account_delete(id: int):
    with db_session() as db:
        row = db.query(SocialAccount).filter_by(id=id).first()
        if not row:
            raise HTTPException(404)
        db.delete(row)
        log_audit(db, "admin", "account_disconnect", "account", id)
        return {"ok": True}


@router.post("/accounts/{id}/toggle")
def account_toggle(id: int):
    with db_session() as db:
        row = db.query(SocialAccount).filter_by(id=id).first()
        if not row:
            raise HTTPException(404)
        row.auto_publish = not row.auto_publish
        log_audit(db, "admin", "account_auto_publish", "account", id, f"auto_publish={row.auto_publish}")
        return _serialize(row)


@router.post("/accounts/{id}/test")
def account_test(id: int):
    with db_session() as db:
        row = db.query(SocialAccount).filter_by(id=id).first()
        if not row:
            raise HTTPException(404)
        adapter = social_factory.adapter_for(row.platform)
        return adapter.test_connection(row)


@router.get("/oauth/platforms")
def oauth_platforms():
    return [social_factory.adapter_for(p).status() for p in social_factory.ADAPTERS]


_oauth_states: dict[str, str] = {}


@router.get("/oauth/{platform}/connect")
def oauth_connect(platform: str):
    adapter = social_factory.adapter_for(platform)
    if not adapter.configured():
        return {"error": f"No app credentials configured for {platform}. Set {platform.upper()} env vars or POST /oauth/credentials.", "configured": False}
    state = secrets.token_urlsafe(16)
    _oauth_states[state] = platform
    redirect = f"{settings.OAUTH_REDIRECT_BASE}/api/v1/oauth/{platform}/callback"
    return {"url": adapter.connect_url(state, redirect), "state": state}


@router.get("/oauth/{platform}/callback")
def oauth_callback(platform: str, code: str = "", state: str = ""):
    if _oauth_states.get(state) != platform:
        return JSONResponse({"error": "invalid state"}, status_code=400)
    adapter = social_factory.adapter_for(platform)
    redirect = f"{settings.OAUTH_REDIRECT_BASE}/api/v1/oauth/{platform}/callback"
    data = adapter.exchange(code, redirect)
    if "error" in data:
        return JSONResponse({"error": data["error"]}, status_code=400)
    with db_session() as db:
        row = SocialAccount(platform=platform, account_id=str(data.get("account_id", uuid.uuid4())[:8]),
                            name=data.get("account_name", platform), handle="",
                            access_token_enc=encrypt_value(data["access_token"]),
                            refresh_token_enc=encrypt_value(data.get("refresh_token", "")),
                            token_expires_at=data.get("expires_at"), scopes=",".join(data.get("scopes", [])),
                            status="active", auto_publish=True, daily_limit=3, config={})
        db.add(row)
        log_audit(db, "admin", "oauth_connected", "account", row.id, platform)
    return {"ok": True, "account_id": row.id, "close": True}


@router.post("/oauth/credentials")
def oauth_credentials(payload: dict):
    with db_session() as db:
        row = db.query(OAuthCredential).filter_by(platform=payload["platform"]).first()
        if row is None:
            row = OAuthCredential(platform=payload["platform"])
            db.add(row)
        row.client_id_enc = encrypt_value(payload.get("client_id", ""))
        row.client_secret_enc = encrypt_value(payload.get("client_secret", ""))
        row.scopes = payload.get("scopes", "")
    return {"ok": True}


# ---------- Schedule ----------
@router.get("/schedule")
def schedule_list():
    with db_session() as db:
        return _list(db.query(PublishSchedule).order_by(PublishSchedule.scheduled_at).limit(100).all())


@router.post("/schedule")
def schedule_create(payload: dict):
    if not payload.get("scheduled_at"):
        raise HTTPException(400, "scheduled_at is required")
    at = datetime.fromisoformat(payload["scheduled_at"].replace("Z", ""))
    with db_session() as db:
        if not db.query(ContentItem).filter_by(id=payload.get("content_id")).first():
            raise HTTPException(404, "content not found")
        if not db.query(SocialAccount).filter_by(id=payload.get("account_id")).first():
            raise HTTPException(404, "social account not found")
        ps = PublishSchedule(content_id=payload["content_id"], account_id=payload["account_id"], scheduled_at=at, status="scheduled")
        db.add(ps)
        db.flush()
        return _serialize(ps)


@router.put("/schedule/{id}")
def schedule_update(id: int, payload: dict):
    with db_session() as db:
        ps = db.query(PublishSchedule).filter_by(id=id).first()
        if not ps:
            raise HTTPException(404)
        if "status" in payload:
            ps.status = payload["status"]
        if "scheduled_at" in payload:
            ps.scheduled_at = datetime.fromisoformat(payload["scheduled_at"])
        return _serialize(ps)


@router.delete("/schedule/{id}")
def schedule_delete(id: int):
    with db_session() as db:
        ps = db.query(PublishSchedule).filter_by(id=id).first()
        if not ps:
            raise HTTPException(404)
        db.delete(ps)
        return {"ok": True}


# ---------- Campaigns ----------
@router.get("/campaigns")
def campaigns():
    with db_session() as db:
        return _list(db.query(Campaign).order_by(Campaign.id.desc()).all())


@router.post("/campaigns")
def campaign_create(payload: dict):
    with db_session() as db:
        c = Campaign(name=payload["name"], theme=payload.get("theme", ""), objective=payload.get("objective", ""),
                     start_date=payload.get("start_date", ""), end_date=payload.get("end_date", ""),
                      budget=float(payload.get("budget", 0)), status=payload.get("status", "planned"), config=payload.get("config", {}))
        db.add(c)
        db.flush()
        return _serialize(c)


# ---------- Published + analytics ----------
@router.get("/published")
def published_list():
    with db_session() as db:
        return _list(db.query(PublishedPost).order_by(PublishedPost.id.desc()).limit(100).all())


@router.get("/published/{id}/metrics")
def published_metrics(id: int):
    with db_session() as db:
        p = db.query(PublishedPost).filter_by(id=id).first()
        if not p:
            raise HTTPException(404)
        return _serialize(p)


@router.get("/analytics")
def analytics():
    with db_session() as db:
        metrics = db.query(PlatformMetric).order_by(PlatformMetric.date).all()
        series = {}
        for m in metrics:
            day = series.setdefault(m.date, {"impressions": 0, "engagement": 0, "followers": 0})
            day["impressions"] += m.impressions
            day["engagement"] += m.likes + m.comments + m.shares + m.saves
            day["followers"] = max(day["followers"], m.followers)
        top = db.query(PublishedPost).all()
        scored = []
        for p in top:
            score = sum((p.metrics or {}).get(k, 0) for k in ("likes", "comments", "shares", "saves"))
            ci = db.query(ContentItem).filter_by(id=p.content_id).first()
            scored.append({"id": p.id, "topic": ci.topic if ci else "", "score": score,
                           "published_at": p.published_at.isoformat() if p.published_at else ""})
        scored.sort(key=lambda x: x["score"], reverse=True)
    return {"series": series, "top_posts": scored[:10]}


# ---------- Comments / community ----------
@router.get("/comments")
def comments():
    with db_session() as db:
        return _list(db.query(Comment).order_by(Comment.id.desc()).limit(100).all())


@router.post("/comments/{id}/reply")
def comment_reply(id: int, payload: dict):
    with db_session() as db:
        c = db.query(Comment).filter_by(id=id).first()
        if not c:
            raise HTTPException(404)
        c.reply = payload.get("reply", "")
        c.status = "replied"
        return _serialize(c)


@router.post("/comments/{id}/escalate")
def comment_escalate(id: int):
    with db_session() as db:
        c = db.query(Comment).filter_by(id=id).first()
        if not c:
            raise HTTPException(404)
        c.status = "escalated"
        c.risk_flag = True
        notify(db, "warning", "Comment escalated", f"Comment #{id} requires human review")
        return _serialize(c)


# ---------- Leads & landing ----------
@router.get("/landing")
def landing():
    s = get_settings()
    return {"brand": s.get("brand_name"), "industry": s.get("brand_industry"),
            "cta": "Get the free Developmental Psychology milestones guide", "colors": s.get("brand_colors")}


@router.get("/leads")
def leads():
    with db_session() as db:
        return _list(db.query(Lead).order_by(Lead.id.desc()).limit(100).all())


@router.post("/leads")
def lead_create(payload: dict):
    email = (payload.get("email") or "").strip()
    if not email or "@" not in email:
        raise HTTPException(400, "valid email required")
    with db_session() as db:
        lead = Lead(name=payload.get("name", ""), email=email, phone=payload.get("phone", ""),
                    source=payload.get("source", "landing_page"), campaign_id=payload.get("campaign_id"),
                    interest=payload.get("interest", ""))
        db.add(lead)
        notify(db, "info", "New lead", f"{email} via {lead.source}")
        return {"ok": True, "lead_id": lead.id}


# ---------- Settings / automation ----------
@router.get("/settings")
def settings_get():
    return get_settings()


@router.put("/settings")
def settings_put(payload: dict):
    new = set_settings(payload)
    if any(k in payload for k in ("schedule_research", "schedule_strategy", "schedule_create", "schedule_qa",
                                  "schedule_publish_1", "schedule_publish_2", "schedule_publish_3",
                                  "schedule_analytics", "schedule_optimize")):
        reschedule()
    return new


@router.get("/automation")
def automation_status():
    return get_settings()


@router.post("/automation/publishing-toggle")
def automation_publishing_toggle(payload: dict):
    enabled = bool(payload.get("enabled"))
    set_settings({"autonomous_publishing": enabled})
    with db_session() as db:
        log_audit(db, "admin", "publishing_toggle", "automation", None, f"enabled={enabled}")
        notify(db, "info" if enabled else "warning", "Autonomous publishing", f"Enabled={enabled}")
    return {"autonomous_publishing": enabled}


@router.post("/automation/run-step")
def automation_run_step(payload: dict):
    step = payload.get("step", "research")
    return run_step(step, payload.get("payload") or {})


@router.post("/automation/reschedule")
def automation_reschedule():
    return reschedule()


# ---------- Logs / notifications ----------
@router.get("/logs")
def logs(limit: int = 100):
    with db_session() as db:
        return _list(db.query(AuditLog).order_by(AuditLog.id.desc()).limit(limit).all())


@router.get("/notifications")
def notifications():
    with db_session() as db:
        return _list(db.query(SystemNotification).order_by(SystemNotification.id.desc()).limit(50).all())


@router.post("/notifications/read")
def notifications_read():
    with db_session() as db:
        for n in db.query(SystemNotification).filter(SystemNotification.read == False).all():
            n.read = True
        return {"ok": True}
