"""X (Twitter) adapter — OAuth1.0a user-context posting (HMAC-SHA1 signing)."""
from __future__ import annotations

import base64
import hashlib
import hmac
import random
import string
from urllib.parse import quote

from .base import BaseAdapter, Capability, register_adapter


def _oauth_header(method: str, url: str, params: dict, consumer_key: str, consumer_secret: str,
                  token: str, token_secret: str) -> str:
    oauth = {
        "oauth_consumer_key": consumer_key,
        "oauth_nonce": "".join(random.choices(string.ascii_letters + string.digits, k=16)),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(__import__("time").time())),
        "oauth_token": token,
        "oauth_version": "1.0",
    }
    allp = {**oauth, **{k: v for k, v in params.items()}}
    enc = "&".join(f"{quote(k, safe='')}={quote(str(v), safe='')}" for k, v in sorted(allp.items()))
    base = f"{method.upper()}&{quote(url, safe='')}&{quote(enc, safe='')}"
    key = f"{quote(consumer_secret, safe='')}&{quote(token_secret, safe='')}"
    sig = base64.b64encode(hmac.new(key.encode(), base.encode(), hashlib.sha1).digest()).decode()
    oauth["oauth_signature"] = sig
    return "OAuth " + ", ".join(f'{k}="{quote(str(v), safe="")}"' for k, v in sorted(oauth.items()))


@register_adapter
class XAdapter(BaseAdapter):
    platform = "x"
    label = "X"
    default_scopes = ["tweet.read", "tweet.write", "users.read", "offline.access"]
    auth_url = "https://twitter.com/i/oauth2/authorize"
    token_url = "https://api.twitter.com/2/oauth2/token"
    api_base = "https://api.twitter.com/2"
    caps = Capability(publish=True, insights=True, comments=False, oauth=True,
                      note="Posting uses OAuth1.0a user tokens; store oauth_token_secret in config")

    def connect_url(self, state: str, redirect_uri: str) -> str:
        return (f"{self.auth_url}?response_type=code&client_id={self.client_id}&redirect_uri={redirect_uri}"
                f"&scope={'%20'.join(self.default_scopes)}&state={state}&code_challenge=challenge&code_challenge_method=plain")

    def exchange(self, code: str, redirect_uri: str) -> dict:
        r = self._post(self.token_url, data={"code": code, "grant_type": "authorization_code",
                                             "client_id": self.client_id, "redirect_uri": redirect_uri},
                       headers={"Content-Type": "application/x-www-form-urlencoded"})
        data = r.json()
        if "access_token" not in data:
            return {"error": str(data)}
        return {"access_token": data["access_token"], "refresh_token": data.get("refresh_token", ""),
                "expires_at": "", "scopes": self.default_scopes, "account_id": "x-user", "account_name": "X Account"}

    def test_connection(self, account) -> dict:
        r = self._get(f"{self.api_base}/users/me", headers={"Authorization": f"Bearer {self._token(account)}"})
        return {"ok": r.status_code == 200, "data": r.json() if r.status_code == 200 else r.text[:200]}

    def publish(self, account, text: str, media_paths: list[str] | None = None, meta: dict | None = None) -> dict:
        secret = (account.config or {}).get("oauth_token_secret", "")
        if not secret:
            return {"ok": False, "error": "oauth_token_secret missing in account config (OAuth1.0a user context required)"}
        url = f"{self.api_base}/tweets"
        payload = {"text": text[:280]}
        hdr = _oauth_header("POST", url, payload, self.client_id, self.client_secret, self._token(account), secret)
        r = self._post(url, json=payload, headers={"Authorization": hdr})
        if r.status_code not in (200, 201):
            return {"ok": False, "error": r.text[:500]}
        return {"ok": True, "post_id": r.json().get("data", {}).get("id"),
                "url": f"https://x.com/i/status/{r.json().get('data', {}).get('id')}"}

    def insights(self, account, since: str, until: str) -> dict:
        return {"unavailable": "X analytics requires approved developer access"}

    def comments(self, account, since: str) -> list[dict]:
        return []
