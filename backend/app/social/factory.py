"""Adapter factory reading app credentials from DB + env."""
from __future__ import annotations

from . import base, facebook, instagram, youtube, pinterest, threads, linkedin, x, tiktok  # noqa: F401
from .base import ADAPTERS, get_adapter


def creds_for(platform: str) -> dict:
    """Credentials from env (fallback) — admin UI can override per-platform in oauth_credentials table."""
    import os
    map_ = {
        "facebook": ("FACEBOOK_APP_ID", "FACEBOOK_APP_SECRET"),
        "instagram": ("FACEBOOK_APP_ID", "FACEBOOK_APP_SECRET"),
        "threads": ("THREADS_CLIENT_ID", "THREADS_CLIENT_SECRET"),
        "youtube": ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"),
        "pinterest": ("PINTEREST_APP_ID", "PINTEREST_APP_SECRET"),
        "linkedin": ("LINKEDIN_CLIENT_ID", "LINKEDIN_CLIENT_SECRET"),
        "x": ("X_CLIENT_ID", "X_CLIENT_SECRET"),
        "tiktok": ("TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET"),
    }
    eid, esec = map_.get(platform, ("", ""))
    return {"client_id": os.getenv(eid, ""), "client_secret": os.getenv(esec, ""),
            "redirect_base": os.getenv("OAUTH_REDIRECT_BASE", "http://localhost:8000")}


def adapter_for(platform: str):
    return get_adapter(platform, **creds_for(platform))
