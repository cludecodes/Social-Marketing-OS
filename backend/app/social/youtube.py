"""YouTube adapter (Data API v3) — videos + shorts via resumable upload."""
from __future__ import annotations

from datetime import datetime, timedelta

from .base import BaseAdapter, Capability, register_adapter


@register_adapter
class YouTubeAdapter(BaseAdapter):
    platform = "youtube"
    label = "YouTube"
    default_scopes = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube.readonly"]
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
    token_url = "https://oauth2.googleapis.com/token"
    api_base = "https://www.googleapis.com/upload/youtube/v3"
    caps = Capability(publish=True, insights=True, comments=False, oauth=True,
                      note="Video upload via resumable upload; comments require separate scope")

    def connect_url(self, state: str, redirect_uri: str) -> str:
        return (f"{self.auth_url}?client_id={self.client_id}&redirect_uri={redirect_uri}"
                f"&response_type=code&scope={' '.join(self.default_scopes)}&access_type=offline&state={state}")

    def exchange(self, code: str, redirect_uri: str) -> dict:
        r = self._post(self.token_url, data={"code": code, "client_id": self.client_id, "client_secret": self.client_secret,
                                             "redirect_uri": redirect_uri, "grant_type": "authorization_code"})
        data = r.json()
        if "access_token" not in data:
            return {"error": str(data)}
        return {"access_token": data["access_token"], "refresh_token": data.get("refresh_token", ""),
                "expires_at": (datetime.utcnow() + timedelta(seconds=data.get("expires_in", 3600))).isoformat(),
                "scopes": self.default_scopes, "account_id": "youtube-channel", "account_name": "YouTube Channel"}

    def refresh(self, account) -> dict | None:
        from ..security import decrypt_value
        rt = decrypt_value(account.refresh_token_enc or "")
        if not rt:
            return None
        r = self._post(self.token_url, data={"client_id": self.client_id, "client_secret": self.client_secret,
                                             "refresh_token": rt, "grant_type": "refresh_token"})
        if r.status_code != 200:
            return None
        data = r.json()
        return {"access_token": data["access_token"], "expires_at": (datetime.utcnow() + timedelta(seconds=data.get("expires_in", 3600))).isoformat()}

    def test_connection(self, account) -> dict:
        r = self._get("https://www.googleapis.com/youtube/v3/channels", params={"part": "snippet", "mine": "true",
                                                                               "access_token": self._token(account)})
        return {"ok": r.status_code == 200, "data": r.json() if r.status_code == 200 else r.text[:200]}

    def publish(self, account, text: str, media_paths: list[str] | None = None, meta: dict | None = None) -> dict:
        if not media_paths:
            return {"ok": False, "error": "YouTube requires a video file"}
        import json as _json
        tok = self._token(account)
        title = (meta or {}).get("title", "Educational video")[:100]
        body = {
            "snippet": {"title": title, "description": text[:5000], "tags": (meta or {}).get("hashtags", [])[:15],
                        "categoryId": "27"},
            "status": {"privacyStatus": (meta or {}).get("privacy", "public"), "selfDeclaredMadeForKids": False},
        }
        with open(media_paths[0], "rb") as f:
            r = self._post(f"{self.api_base}/videos?part=snippet,status&access_token={tok}",
                           headers={"Content-Type": "application/json", "X-Upload-Content-Type": "video/mp4"},
                           data=_json.dumps(body))
        if r.status_code not in (200, 201):
            return {"ok": False, "error": r.text[:500]}
        return {"ok": True, "post_id": r.json().get("id"), "url": f"https://youtu.be/{r.json().get('id')}"}

    def insights(self, account, since: str, until: str) -> dict:
        r = self._get("https://www.googleapis.com/youtube/analytics/v2/reports",
                      params={"ids": "channel==MINE", "startDate": since, "endDate": until,
                              "metrics": "views,estimatedMinutesWatched,subscribersGained",
                              "access_token": self._token(account)})
        return r.json() if r.status_code == 200 else {"error": r.text[:300]}

    def comments(self, account, since: str) -> list[dict]:
        return []
