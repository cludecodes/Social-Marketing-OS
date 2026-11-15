"""Agent 07 — Video Production Agent: shorts/reels via free local render + free TTS."""
from __future__ import annotations

import os

from ..media.video_generator import VideoGenerator, ffmpeg_available
from ..ai.providers import registry
from ..ai.content_engine import video_script
from ..models import ContentItem, MediaAsset
from ..config import settings
from .base import BaseAgent, register


@register
class VideoAgent(BaseAgent):
    key = "video"
    name = "Video Production Agent"
    role = "Creates short educational videos (Reels/Shorts): scripts, scenes, free neural voice-over, captions, branded end screens."

    def run(self, task_type: str, payload: dict | None = None) -> dict:
        db = self.db
        if not ffmpeg_available():
            return {"status": "failed", "reason": "ffmpeg not available"}
        gen = VideoGenerator(settings.MEDIA_DIR, settings.BRAND_COLORS, settings.BRAND_NAME)
        items = db.query(ContentItem).filter(ContentItem.format.in_(["reel", "short_video", "video"]),
                                             ContentItem.status.in_(["draft", "qa_pending"])).limit(payload.get("limit", 3)).all()
        made = []
        for item in items:
            existing = db.query(MediaAsset).filter(MediaAsset.meta.contains({"content_id": item.id, "kind": "video"})).first()
            if existing:
                continue
            script = video_script({"id": "x", "title": item.topic, "fact": item.body})
            tts = None
            try:
                tts = registry.tts(" ".join(s["text"] for s in script["scenes"]))
            except Exception as e:  # noqa: BLE001
                self.log("tts_unavailable", str(e)[:200])
            out = gen.render(script["title"], script["scenes"], aspect="9:16", tts_bytes=tts, per_scene=8)
            asset = MediaAsset(kind="video", path=out["path"], filename=os.path.basename(out["path"]), mime=out["mime"],
                               width=out["width"], height=out["height"], size=out["size"],
                               meta={"content_id": item.id, "kind": "video", "engine": out["engine"], "audio": out["audio"], "scenes": out["scenes"]})
            db.add(asset)
            db.flush()
            item.media_ids = (item.media_ids or []) + [asset.id]
            made.append({"content_id": item.id, "asset": asset.id, "audio": out["audio"]})
        return {"status": "done", "videos": len(made), "items": made}
