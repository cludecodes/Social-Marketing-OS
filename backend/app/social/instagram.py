"""Instagram Professional adapter via Instagram Graph API (container flow)."""
from __future__ import annotations

from datetime import datetime, timedelta

from .base import BaseAdapter, Capability, register_adapter


@register_adapter
class InstagramAdapter(BaseAdapter):
    platform = "instagram"
    label = "Instagram Professional"
    default_scopes = ["instagram_basic", "pages_show_list", "pages_manage_posts", "instagram_content_publish"]
    auth_url = "https://www.facebook.com/v21.0/dialog/oauth"
    token_url = "https://graph.facebook.com/v21.0/oauth/access_token"
    api_base = "https://graph.facebook.com/v21.0"
    caps = Capability(publish=True, insights=True, comments=True, oauth=True,
                      note="Requires linked FB Page + Instagram Business account; photo via container flow")

    def __init__(self, client_id: str = "", client_secret: str = "", redirect_base: str = ""):
        super().__init__(client_id, client_secret, redirect_base)

    def connect_url(self, state: str, redirect_uri: str) -> str:
        return (f"{self.auth_url}?client_id={self.client_id}&redirect_uri={redirect_uri}"
                f"&state={state}&scope={','.join(self.default_scopes)}&response_type=code")

    def exchange(self, code: str, redirect_uri: str) -> dict:
        r = self._get(self.token_url, params={"client_id": self.client_id, "redirect_uri": redirect_uri,
                                              "client_secret": self.client_secret, "code": code})
        data = r.json()
        if "access_token" not in data:
            return {"error": str(data)}
        long_r = self._get(self.token_url, params={"grant_type": "fb_exchange_token", "client_id": self.client_id,
                                                   "client_secret": self.client_secret,
                                                   "fb_exchange_token": data["access_token"]})
        long = long_r.json()
        token = long.get("access_token", data["access_token"])
        # Discover IG user id linked to page
        me = self._get(f"{self.api_base}/me", params={"access_token": token, "fields": "id,name,accounts{instagram_business_account{id,username}}"}).json()
        ig = (me.get("accounts", {}).get("data") or [{}])[0].get("instagram_business_account") or {}
        return {"access_token": token, "refresh_token": "",
                "expires_at": (datetime.utcnow() + timedelta(seconds=int(long.get("expires_in", 3600)))).isoformat(),
                "scopes": self.default_scopes,
                "account_id": ig.get("id", me.get("id")), "account_name": ig.get("username", me.get("name"))}

    def test_connection(self, account) -> dict:
        r = self._get(f"{self.api_base}/{account.account_id}", params={"access_token": self._token(account), "fields": "id,username"})
        return {"ok": r.status_code == 200, "data": r.json() if r.status_code == 200 else r.text[:200]}

    def publish(self, account, text: str, media_paths: list[str] | None = None, meta: dict | None = None) -> dict:
        tok = self._token(account)
        if not media_paths:
            return {"ok": False, "error": "Instagram requires image/video media for publish"}
        # Container create
        r = self._post(f"{self.api_base}/{account.account_id}/media",
                       data={"image_url": meta.get("image_url", ""), "caption": text[:2200], "access_token": tok})
        data = r.json()
        if "id" not in data:
            return {"ok": False, "error": str(data)[:500]}
        container = data["id"]
        # Poll status
        import time
        for _ in range(10):
            st = self._get(f"{self.api_base}/{container}", params={"access_token": tok, "fields": "status_code"}).json()
            if st.get("status_code") == "ERROR":
                return {"ok": False, "error": f"container error: {st}"}
            if st.get("status_code") == "FINISHED":
                break
            time.sleep(2)
        r2 = self._post(f"{self.api_base}/{account.account_id}/media_publish",
                        data={"creation_id": container, "access_token": tok})
        pub = r2.json()
        if "id" not in pub:
            return {"ok": False, "error": str(pub)[:500]}
        return {"ok": True, "post_id": pub["id"], "url": f"https://www.instagram.com/p/{pub['id']}/"}

    def insights(self, account, since: str, until: str) -> dict:
        tok = self._token(account)
        r = self._get(f"{self.api_base}/{account.account_id}/insights",
                      params={"access_token": tok, "metric": "impressions,reach,engagement,followers_count",
                              "since": since, "until": until, "period": "day"})
        return r.json() if r.status_code == 200 else {"error": r.text[:300]}

    def comments(self, account, since: str) -> list[dict]:
        tok = self._token(account)
        r = self._get(f"{self.api_base}/{account.account_id}/media", params={"access_token": tok, "fields": "id,comments{username,text,timestamp}", "limit": 10})
        out = []
        if r.status_code != 200:
            return out
        for m in r.json().get("data", []):
            for c in m.get("comments", {}).get("data", []):
                out.append({"id": c.get("id"), "author": c.get("username", ""), "text": c.get("text", ""),
                            "created_at": c.get("timestamp"), "post_id": m.get("id")})
        return out
