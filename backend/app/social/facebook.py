"""Facebook Pages adapter (Graph API)."""
from __future__ import annotations

from datetime import datetime, timedelta

from .base import BaseAdapter, Capability, register_adapter


@register_adapter
class FacebookAdapter(BaseAdapter):
    platform = "facebook"
    label = "Facebook Pages"
    default_scopes = ["pages_show_list", "pages_manage_posts", "pages_read_engagement", "pages_manage_metadata"]
    auth_url = "https://www.facebook.com/v21.0/dialog/oauth"
    token_url = "https://graph.facebook.com/v21.0/oauth/access_token"
    api_base = "https://graph.facebook.com/v21.0"
    caps = Capability(publish=True, insights=True, comments=True, oauth=True,
                      note="Requires Facebook App + page role; publish via /{page_id}/photos or /feed")

    def __init__(self, client_id: str = "", client_secret: str = "", redirect_base: str = ""):
        super().__init__(client_id, client_secret, redirect_base)
        self.caps = Capability(publish=bool(client_id), insights=bool(client_id), comments=bool(client_id), oauth=True, note=self.caps.note)

    def connect_url(self, state: str, redirect_uri: str) -> str:
        return (f"{self.auth_url}?client_id={self.client_id}&redirect_uri={redirect_uri}"
                f"&state={state}&scope={','.join(self.default_scopes)}&response_type=code")

    def exchange(self, code: str, redirect_uri: str) -> dict:
        r = self._get(self.token_url, params={"client_id": self.client_id, "redirect_uri": redirect_uri,
                                              "client_secret": self.client_secret, "code": code})
        data = r.json()
        if "access_token" not in data:
            return {"error": str(data)}
        # Long-lived exchange
        r2 = self._get(self.token_url, params={"grant_type": "fb_exchange_token", "client_id": self.client_id,
                                               "client_secret": self.client_secret,
                                               "fb_exchange_token": data["access_token"]})
        long = r2.json()
        token = long.get("access_token", data["access_token"])
        expires = datetime.utcnow() + timedelta(seconds=int(long.get("expires_in", data.get("expires_in", 3600))))
        me = self._get(f"{self.api_base}/me", params={"access_token": token, "fields": "id,name,accounts{access_token,id,name}"}).json()
        page = (me.get("accounts", {}).get("data") or [{}])[0]
        return {"access_token": page.get("access_token", token), "refresh_token": "",
                "expires_at": expires.isoformat(), "scopes": self.default_scopes,
                "account_id": page.get("id", me.get("id")), "account_name": page.get("name", me.get("name")),
                "page_token": page.get("access_token", token)}

    def test_connection(self, account) -> dict:
        tok = self._token(account)
        r = self._get(f"{self.api_base}/me", params={"access_token": tok, "fields": "id,name"})
        return {"ok": r.status_code == 200, "data": r.json() if r.status_code == 200 else r.text[:200]}

    def publish(self, account, text: str, media_paths: list[str] | None = None, meta: dict | None = None) -> dict:
        tok = self._token(account)
        if media_paths:
            with open(media_paths[0], "rb") as f:
                r = self._post(f"{self.api_base}/{account.account_id}/photos",
                               data={"message": text, "access_token": tok}, files={"source": f})
        else:
            r = self._post(f"{self.api_base}/{account.account_id}/feed",
                           data={"message": text, "access_token": tok})
        data = r.json()
        if r.status_code // 100 != 2 or "id" not in data:
            return {"ok": False, "error": str(data)[:500]}
        return {"ok": True, "post_id": data["id"], "url": f"https://www.facebook.com/{account.account_id}/posts/{data['id']}"}

    def insights(self, account, since: str, until: str) -> dict:
        tok = self._token(account)
        metrics = "page_impressions,page_engaged_users,page_followers,post_engagements"
        r = self._get(f"{self.api_base}/{account.account_id}/insights",
                      params={"access_token": tok, "metric": metrics, "since": since, "until": until, "period": "day"})
        return r.json() if r.status_code == 200 else {"error": r.text[:300]}

    def comments(self, account, since: str) -> list[dict]:
        tok = self._token(account)
        r = self._get(f"{self.api_base}/{account.account_id}/feed", params={"access_token": tok, "fields": "comments{from,message,created_time}", "since": since, "limit": 50})
        out = []
        if r.status_code != 200:
            return out
        for post in r.json().get("data", []):
            for c in post.get("comments", {}).get("data", []):
                out.append({"id": c["id"], "author": c.get("from", {}).get("name", ""), "text": c.get("message", ""),
                            "created_at": c.get("created_time"), "post_id": post.get("id")})
        return out
