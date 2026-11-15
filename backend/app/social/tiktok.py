"""TikTok adapter — OAuth + read APIs; posting requires TikTok partner approval."""
from __future__ import annotations

from datetime import datetime, timedelta

from .base import BaseAdapter, Capability, register_adapter


@register_adapter
class TikTokAdapter(BaseAdapter):
    platform = "tiktok"
    label = "TikTok"
    default_scopes = ["user.info.basic", "video.list", "video.upload"]
    auth_url = "https://www.tiktok.com/auth/authorize"
    token_url = "https://open.tiktokapis.com/v2/oauth/token/"
    api_base = "https://open.tiktokapis.com/v2"
    caps = Capability(publish=False, insights=True, comments=False, oauth=True,
                      note="Publishing requires TikTok Business/partner approval; connector implements auth + read APIs only")

    def connect_url(self, state: str, redirect_uri: str) -> str:
        return (f"{self.auth_url}?client_key={self.client_id}&response_type=code&scope={','.join(self.default_scopes)}"
                f"&redirect_uri={redirect_uri}&state={state}")

    def exchange(self, code: str, redirect_uri: str) -> dict:
        r = self._post(self.token_url, data={"client_key": self.client_id, "client_secret": self.client_secret,
                                             "code": code, "grant_type": "authorization_code",
                                             "redirect_uri": redirect_uri})
        data = r.json()
        if "access_token" not in data:
            return {"error": str(data)}
        return {"access_token": data["access_token"], "refresh_token": data.get("refresh_token", ""),
                "expires_at": (datetime.utcnow() + timedelta(seconds=data.get("expires_in", 3600))).isoformat(),
                "scopes": self.default_scopes, "account_id": "tiktok-user", "account_name": "TikTok Account"}

    def test_connection(self, account) -> dict:
        r = self._get(f"{self.api_base}/user/", headers={"Authorization": f"Bearer {self._token(account)}"})
        return {"ok": r.status_code == 200, "data": r.json() if r.status_code == 200 else r.text[:200]}

    def publish(self, account, text: str, media_paths: list[str] | None = None, meta: dict | None = None) -> dict:
        return {"ok": False, "error": "TikTok publishing requires partner approval; not available for this account. Content remains queued for manual posting."}

    def insights(self, account, since: str, until: str) -> dict:
        r = self._get(f"{self.api_base}/video/list/", headers={"Authorization": f"Bearer {self._token(account)}"})
        return r.json() if r.status_code == 200 else {"error": r.text[:300]}

    def comments(self, account, since: str) -> list[dict]:
        return []
