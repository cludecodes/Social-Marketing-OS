"""LinkedIn adapter (Marketing Developer Platform shares API)."""
from __future__ import annotations

from datetime import datetime, timedelta

from .base import BaseAdapter, Capability, register_adapter


@register_adapter
class LinkedInAdapter(BaseAdapter):
    platform = "linkedin"
    label = "LinkedIn"
    default_scopes = ["w_member_social", "r_liteprofile", "r_emailaddress"]
    auth_url = "https://www.linkedin.com/oauth/v2/authorization"
    token_url = "https://www.linkedin.com/oauth/v2/accessToken"
    api_base = "https://api.linkedin.com/rest"
    caps = Capability(publish=True, insights=True, comments=False, oauth=True,
                      note="Share via /shares; analytics via /analytics with approved app")

    def connect_url(self, state: str, redirect_uri: str) -> str:
        return (f"{self.auth_url}?response_type=code&client_id={self.client_id}&redirect_uri={redirect_uri}"
                f"&state={state}&scope={' '.join(self.default_scopes)}")

    def exchange(self, code: str, redirect_uri: str) -> dict:
        r = self._post(self.token_url, data={"grant_type": "authorization_code", "code": code,
                                             "redirect_uri": redirect_uri, "client_id": self.client_id,
                                             "client_secret": self.client_secret})
        data = r.json()
        if "access_token" not in data:
            return {"error": str(data)}
        return {"access_token": data["access_token"], "refresh_token": "",
                "expires_at": (datetime.utcnow() + timedelta(seconds=data.get("expires_in", 3600))).isoformat(),
                "scopes": self.default_scopes, "account_id": "linkedin-member", "account_name": "LinkedIn Member"}

    def test_connection(self, account) -> dict:
        r = self._get(f"{self.api_base}/userinfo", headers={"Authorization": f"Bearer {self._token(account)}"})
        return {"ok": r.status_code == 200, "data": r.json() if r.status_code == 200 else r.text[:200]}

    def publish(self, account, text: str, media_paths: list[str] | None = None, meta: dict | None = None) -> dict:
        tok = self._token(account)
        body = {"author": f"urn:li:person:{account.account_id}", "lifecycleState": "PUBLISHED",
                "specificContent": {"com.linkedin.ugc.ShareContent": {"shareCommentary": {"text": text[:1300]},
                                                                       "shareMediaCategory": "NONE"}},
                "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}}
        r = self._post(f"{self.api_base}/shares", headers={"Authorization": f"Bearer {tok}",
                                                            "Content-Type": "application/json",
                                                            "X-Restli-Protocol-Version": "2.0.0"}, json=body)
        if r.status_code not in (200, 201):
            return {"ok": False, "error": r.text[:500]}
        return {"ok": True, "post_id": r.json().get("id"), "url": ""}

    def insights(self, account, since: str, until: str) -> dict:
        return {"unavailable": "LinkedIn analytics requires approved marketing app"}

    def comments(self, account, since: str) -> list[dict]:
        return []
