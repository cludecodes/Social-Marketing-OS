"""Persistent models for the Shophippy Marketing OS."""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, Index
from sqlalchemy.orm import relationship

from .db import Base


def _now() -> datetime:
    return datetime.utcnow()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(80), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="admin")
    created_at = Column(DateTime, default=_now)
    last_login = Column(DateTime, nullable=True)


class OAuthCredential(Base):
    """App-level OAuth credentials per platform (client id/secret encrypted)."""
    __tablename__ = "oauth_credentials"
    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(40), unique=True, nullable=False)
    client_id_enc = Column(Text, nullable=True)
    client_secret_enc = Column(Text, nullable=True)
    scopes = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=_now, onupdate=_now)


class SocialAccount(Base):
    __tablename__ = "social_accounts"
    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(40), nullable=False, index=True)  # pinterest|facebook|instagram|youtube|threads|tiktok|linkedin|x
    account_id = Column(String(120), nullable=False)
    name = Column(String(160), nullable=False)
    handle = Column(String(160), nullable=True)
    access_token_enc = Column(Text, nullable=True)
    refresh_token_enc = Column(Text, nullable=True)
    token_expires_at = Column(DateTime, nullable=True)
    scopes = Column(Text, nullable=True)
    status = Column(String(20), default="active")  # active|paused|expired|error
    auto_publish = Column(Boolean, default=True)
    daily_limit = Column(Integer, default=3)
    config = Column(JSON, default=dict)
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)
    __table_args__ = (UniqueConstraint("platform", "account_id", name="uq_account_platform_id"),)


class AIAgent(Base):
    __tablename__ = "ai_agents"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(40), unique=True, nullable=False)  # cmo, audience, trends, research, strategy, designer, video, copywriter, publisher, community, analytics, qa
    name = Column(String(120), nullable=False)
    role = Column(String(200), nullable=False)
    enabled = Column(Boolean, default=True)
    config = Column(JSON, default=dict)
    last_run_at = Column(DateTime, nullable=True)
    status = Column(String(20), default="idle")


class AgentTask(Base):
    __tablename__ = "agent_tasks"
    id = Column(Integer, primary_key=True, index=True)
    agent_key = Column(String(40), nullable=False, index=True)
    task_type = Column(String(60), nullable=False, index=True)
    payload = Column(JSON, default=dict)
    status = Column(String(20), default="queued")  # queued|running|done|failed|dead
    result = Column(JSON, nullable=True)
    attempts = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)
    last_error = Column(Text, nullable=True)
    locked_by = Column(String(64), nullable=True)
    locked_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=_now)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)


class ResearchReport(Base):
    __tablename__ = "research_reports"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(300), nullable=False)
    kind = Column(String(40), nullable=False)  # audience|trend|education
    topic = Column(String(300), nullable=True)
    summary = Column(Text, nullable=True)
    data = Column(JSON, default=dict)
    source = Column(String(120), nullable=True)
    created_at = Column(DateTime, default=_now)


class AudiencePersona(Base):
    __tablename__ = "audience_personas"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    segment = Column(String(120), nullable=True)
    demographics = Column(Text, nullable=True)
    interests = Column(JSON, default=list)
    pain_points = Column(JSON, default=list)
    content_hooks = Column(JSON, default=list)
    created_at = Column(DateTime, default=_now)


class ContentIdea(Base):
    __tablename__ = "content_ideas"
    id = Column(Integer, primary_key=True, index=True)
    topic = Column(String(300), nullable=False)
    angle = Column(Text, nullable=True)
    format = Column(String(40), nullable=True)  # infographic|carousel|pin|reel|short|post|video|guide
    platform_targets = Column(JSON, default=list)
    score = Column(Float, default=0.0)
    trend_score = Column(Float, default=0.0)
    status = Column(String(20), default="new")  # new|selected|drafted|published|rejected
    source = Column(String(60), nullable=True)
    created_at = Column(DateTime, default=_now)


class ContentItem(Base):
    __tablename__ = "content_items"
    id = Column(Integer, primary_key=True, index=True)
    idea_id = Column(Integer, ForeignKey("content_ideas.id"), nullable=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=True)
    topic = Column(String(300), nullable=False)
    format = Column(String(40), nullable=False)
    title = Column(String(400), nullable=True)
    body = Column(Text, nullable=True)
    caption_variants = Column(JSON, default=dict)
    hashtags = Column(JSON, default=list)
    media_ids = Column(JSON, default=list)
    citations = Column(JSON, default=list)
    status = Column(String(20), default="draft")  # draft|qa_pending|approved|scheduled|published|failed|rejected
    qa_report = Column(JSON, nullable=True)
    approval_required = Column(Boolean, default=True)
    approved_by = Column(Integer, nullable=True)
    duplicate_key = Column(String(128), index=True)
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)


class ContentVersion(Base):
    """Per-platform publishing version of a ContentItem."""
    __tablename__ = "content_versions"
    id = Column(Integer, primary_key=True, index=True)
    content_id = Column(Integer, ForeignKey("content_items.id"), nullable=False, index=True)
    platform = Column(String(40), nullable=False)
    headline = Column(String(300), nullable=True)
    caption = Column(Text, nullable=True)
    hashtags = Column(JSON, default=list)
    media_ids = Column(JSON, default=list)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=_now)


class MediaAsset(Base):
    __tablename__ = "media_assets"
    id = Column(Integer, primary_key=True, index=True)
    kind = Column(String(20), nullable=False)  # image|video|pdf
    path = Column(String(500), nullable=False)
    filename = Column(String(200), nullable=False)
    mime = Column(String(80), nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    size = Column(Integer, default=0)
    meta = Column(JSON, default=dict)
    created_at = Column(DateTime, default=_now)


class Campaign(Base):
    __tablename__ = "campaigns"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    theme = Column(String(200), nullable=True)
    objective = Column(String(200), nullable=True)
    start_date = Column(String(20), nullable=True)
    end_date = Column(String(20), nullable=True)
    budget = Column(Float, nullable=True)
    spent = Column(Float, default=0.0)
    status = Column(String(20), default="planned")  # planned|active|paused|completed
    config = Column(JSON, default=dict)
    created_at = Column(DateTime, default=_now)


class PublishSchedule(Base):
    __tablename__ = "publish_schedules"
    id = Column(Integer, primary_key=True, index=True)
    content_id = Column(Integer, ForeignKey("content_items.id"), nullable=False, index=True)
    account_id = Column(Integer, ForeignKey("social_accounts.id"), nullable=False, index=True)
    scheduled_at = Column(DateTime, nullable=False, index=True)
    status = Column(String(20), default="scheduled")  # scheduled|publishing|published|failed|cancelled
    published_at = Column(DateTime, nullable=True)
    post_url = Column(String(500), nullable=True)
    post_id = Column(String(200), nullable=True)
    error = Column(Text, nullable=True)
    attempts = Column(Integer, default=0)
    created_at = Column(DateTime, default=_now)


class PublishedPost(Base):
    __tablename__ = "published_posts"
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("social_accounts.id"), nullable=False, index=True)
    content_id = Column(Integer, ForeignKey("content_items.id"), nullable=True)
    platform_post_id = Column(String(200), nullable=True)
    url = Column(String(500), nullable=True)
    published_at = Column(DateTime, default=_now)
    metrics = Column(JSON, default=dict)
    created_at = Column(DateTime, default=_now)


class PlatformMetric(Base):
    __tablename__ = "platform_metrics"
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("social_accounts.id"), nullable=False, index=True)
    date = Column(String(10), nullable=False, index=True)
    impressions = Column(Integer, default=0)
    reach = Column(Integer, default=0)
    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    saves = Column(Integer, default=0)
    followers = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    __table_args__ = (UniqueConstraint("account_id", "date", name="uq_metric_account_date"),)


class Comment(Base):
    __tablename__ = "comments"
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("social_accounts.id"), nullable=False, index=True)
    platform_comment_id = Column(String(200), nullable=True)
    author = Column(String(200), nullable=True)
    text = Column(Text, nullable=False)
    sentiment = Column(String(20), nullable=True)
    risk_flag = Column(Boolean, default=False)
    status = Column(String(20), default="open")  # open|replied|escalated|ignored
    reply = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_now)


class Lead(Base):
    __tablename__ = "leads"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=True)
    email = Column(String(200), nullable=False, index=True)
    phone = Column(String(60), nullable=True)
    source = Column(String(120), nullable=True)  # landing_page|pdf|form|campaign
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=True)
    interest = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=_now)


class AutomationRule(Base):
    __tablename__ = "automation_rules"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    trigger = Column(String(120), nullable=False)
    condition = Column(JSON, default=dict)
    action = Column(JSON, default=dict)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=_now)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    actor = Column(String(120), nullable=True)
    action = Column(String(120), nullable=False, index=True)
    entity = Column(String(80), nullable=True)
    entity_id = Column(String(80), nullable=True)
    detail = Column(Text, nullable=True)
    ip = Column(String(60), nullable=True)
    created_at = Column(DateTime, default=_now)
    __table_args__ = (Index("ix_audit_action_time", "action", "created_at"),)


class SystemNotification(Base):
    __tablename__ = "system_notifications"
    id = Column(Integer, primary_key=True, index=True)
    level = Column(String(20), default="info")  # info|warning|error|critical
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=True)
    read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=_now)


class JobQueue(Base):
    __tablename__ = "job_queue"
    id = Column(Integer, primary_key=True, index=True)
    agent = Column(String(40), nullable=False, index=True)
    task_type = Column(String(60), nullable=False)
    payload = Column(JSON, default=dict)
    status = Column(String(20), default="queued")  # queued|running|done|failed|dead
    attempts = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)
    next_run_at = Column(DateTime, nullable=True)
    locked_by = Column(String(64), nullable=True)
    locked_until = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)


class Setting(Base):
    __tablename__ = "settings"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(120), unique=True, nullable=False)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=_now, onupdate=_now)
