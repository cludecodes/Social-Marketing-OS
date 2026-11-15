"""Pinterest adapter (v5 API)."""
from __future__ import annotations

from datetime import datetime, timedelta

from .base import BaseAdapter, Capability, register_adapter


@register_adapter
class PinterestAdapter(BaseAdapter):
    platform = "pinterest"
    label = "Pinterest"
    default_scopes = ["pins:create", "boards:read", "user_accounts:read", "analytics:read"]
    auth_url = "https://www.pinterest.com/oauth/"
    token_url = "https://api.pinterest.com/v5/oauth/token"
    api_base = "https://api.pinterest.com/v5"
    caps = Capability(publish=True, insights=True, comments=False, oauth=True,
                      note="Pin creation requires board_id in account config; SEO description recommended")

    def __init__(self, client_id: str = "", client_secret: str = "", redirect_base: str = ""):
        super().__init__(client_id, client_secret, redirect_base)

    def connect_url(self, state: str, redirect_uri: str) -> str:
        return (f"{self.auth_url}?response_type=code&client_id={self.client_id}&redirect_uri={redirect_uri}"
                f"&state={state}&scope={','.join(self.default_scopes)}")

    def exchange(self, code: str, redirect_uri: str) -> dict:
        r = self._post(self.token_url, data={"grant_type": "authorization_code", "code": code,
                                             "redirect_uri": redirect_uri, "client_id": self.client_id,
                                             "client_secret": self.client_secret})
        data = r.json()
        if "access_token" not in data:
            return {"error": str(data)}
        return {"access_token": data["access_token"], "refresh_token": data.get("refresh_token", ""),
                "expires_at": (datetime.utcnow() + timedelta(seconds=data.get("expires_in", 3600))).isoformat(),
                "scopes": self.default_scopes, "account_id": "pinterest-user", "account_name": "Pinterest Account"}

    def refresh(self, account) -> dict | None:
        from ..security import decrypt_value
        rt = decrypt_value(account.refresh_token_enc or "")
        if not rt:
            return None
        r = self._post(self.token_url, data={"grant_type": "refresh_token", "refresh_token": rt,
                                             "client_id": self.client_id, "client_secret": self.client_secret})
        if r.status_code != 200:
            return None
        d = r.json()
        return {"access_token": d["access_token"], "expires_at": (datetime.utcnow() + timedelta(seconds=d.get("expires_in", 3600))).isoformat()}

    def test_connection(self, account) -> dict:
        r = self._get(f"{self.api_base}/user_account", headers={"Authorization": f"Bearer {self._token(account)}"})
        return {"ok": r.status_code == 200, "data": r.json() if r.status_code == 200 else r.text[:200]}

    def publish(self, account, text: str, media_paths: list[str] | None = None, meta: dict | None = None) -> dict:
        tok = self._token(account)
        board_id = (account.config or {}).get("board_id")
        if not board_id:
            return {"ok": False, "error": "board_id not configured on account"}
        if not media_paths:
            return {"ok": False, "error": "Pinterest pin requires media"}
        payload = {
            "board_id": board_id,
            "title": (meta or {}).get("title", text[:100])[:100],
            "description": text[:500],
            "media": {"source": {"url": (meta or {}).get("image_url", "")}} if (meta or {}).get("image_url") else None,
            "alt_text": (meta or {}).get("alt_text", ""),
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        r = self._post(f"{self.api_base}/pins", headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
                       json=payload)
        if r.status_code not in (200, 201):
            return {"ok": False, "error": r.text[:500]}
        data = r.json()
        return {"ok": True, "post_id": data.get("id"), "url": data.get("link", "")}

    def insights(self, account, since: str, until: str) -> dict:
        return {"unavailable": "Pinterest analytics requires business account + approved app; metrics via /v5/user_account/analytics"}

    def comments(self, account, since: str) -> list[dict]:
        return []
