"""Threads adapter (Instagram Graph API threads endpoints)."""
from __future__ import annotations

from .base import BaseAdapter, Capability, register_adapter


@register_adapter
class ThreadsAdapter(BaseAdapter):
    platform = "threads"
    label = "Threads"
    default_scopes = ["threads_basic", "threads_manage_threads", "instagram_basic"]
    auth_url = "https://www.facebook.com/v21.0/dialog/oauth"
    token_url = "https://graph.facebook.com/v21.0/oauth/access_token"
    api_base = "https://graph.facebook.com/v21.0"
    caps = Capability(publish=True, insights=False, comments=False, oauth=True,
                      note="Text posts via container flow; media posts require further app review")

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
        return {"access_token": data["access_token"], "refresh_token": "",
                "expires_at": "", "scopes": self.default_scopes,
                "account_id": "threads-user", "account_name": "Threads Account"}

    def test_connection(self, account) -> dict:
        r = self._get(f"{self.api_base}/me", params={"access_token": self._token(account), "fields": "id,username"})
        return {"ok": r.status_code == 200, "data": r.json() if r.status_code == 200 else r.text[:200]}

    def publish(self, account, text: str, media_paths: list[str] | None = None, meta: dict | None = None) -> dict:
        tok = self._token(account)
        r = self._post(f"{self.api_base}/{account.account_id}/threads",
                       data={"text": text[:500], "access_token": tok})
        data = r.json()
        if "id" not in data:
            return {"ok": False, "error": str(data)[:500]}
        r2 = self._post(f"{self.api_base}/{account.account_id}/threads_publish",
                        data={"creation_id": data["id"], "access_token": tok})
        pub = r2.json()
        if "id" not in pub:
            return {"ok": False, "error": str(pub)[:500]}
        return {"ok": True, "post_id": pub["id"], "url": f"https://www.threads.net/@{(account.handle or '')}/post/{pub['id']}"}

    def insights(self, account, since: str, until: str) -> dict:
        return {"unavailable": "Threads insights not publicly available yet"}

    def comments(self, account, since: str) -> list[dict]:
        return []
