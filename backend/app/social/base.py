"""Social platform adapter base class + capabilities registry.

Every adapter implements real official-API calls. When app credentials or
tokens are missing, methods return explicit "unavailable" results — never a
fake success. Each adapter declares what it supports.
"""
from __future__ import annotations

import abc
from datetime import datetime, timedelta
from typing import Any

import httpx

from ..security import decrypt_value


class Capability:
    def __init__(self, publish: bool, insights: bool, comments: bool, oauth: bool, note: str = ""):
        self.publish = publish
        self.insights = insights
        self.comments = comments
        self.oauth = oauth
        self.note = note

    def as_dict(self) -> dict:
        return {"publish": self.publish, "insights": self.insights, "comments": self.comments,
                "oauth": self.oauth, "note": self.note}


class BaseAdapter(abc.ABC):
    platform: str = ""
    label: str = ""
    default_scopes: list[str] = []
    auth_url: str = ""
    token_url: str = ""
    api_base: str = ""
    caps: Capability = Capability(False, False, False, False)

    def __init__(self, client_id: str = "", client_secret: str = "", redirect_base: str = ""):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_base = redirect_base

    def configured(self) -> bool:
        return bool(self.client_id)

    def connect_url(self, state: str, redirect_uri: str) -> str:
        raise NotImplementedError

    def exchange(self, code: str, redirect_uri: str) -> dict:
        raise NotImplementedError

    def refresh(self, account) -> dict | None:
        return None

    def _token(self, account) -> str:
        return decrypt_value(account.access_token_enc or "")

    def test_connection(self, account) -> dict:
        return {"ok": False, "reason": "not implemented"}

    def publish(self, account, text: str, media_paths: list[str] | None = None, meta: dict | None = None) -> dict:
        raise NotImplementedError

    def insights(self, account, since: str, until: str) -> dict:
        raise NotImplementedError

    def comments(self, account, since: str) -> list[dict]:
        raise NotImplementedError

    def _post(self, url: str, **kw) -> httpx.Response:
        with httpx.Client(timeout=60) as c:
            return c.post(url, **kw)

    def _get(self, url: str, **kw) -> httpx.Response:
        with httpx.Client(timeout=60) as c:
            return c.get(url, **kw)

    def status(self) -> dict:
        return {"platform": self.platform, "label": self.label, "configured": self.configured(),
                "capabilities": self.caps.as_dict()}


ADAPTERS: dict[str, type[BaseAdapter]] = {}


def register_adapter(cls):
    ADAPTERS[cls.platform] = cls
    return cls


def get_adapter(platform: str, **creds) -> BaseAdapter:
    cls = ADAPTERS.get(platform)
    if cls is None:
        raise KeyError(f"No adapter for {platform}")
    return cls(**creds)


def all_status() -> list[dict]:
    out = []
    for p, cls in ADAPTERS.items():
        out.append(cls().status())
    return out
