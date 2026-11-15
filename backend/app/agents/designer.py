"""Agent 06 — AI Graphic Designer: original branded visual assets."""
from __future__ import annotations

import os

from ..media.image_generator import ImageGenerator
from ..models import ContentItem, MediaAsset
from ..config import settings
from .base import BaseAgent, register


@register
class DesignerAgent(BaseAgent):
    key = "designer"
    name = "AI Graphic Designer"
    role = "Generates original visual assets: infographics, carousels, pins, thumbnails, quote cards, banners."

    def run(self, task_type: str, payload: dict | None = None) -> dict:
        db = self.db
        gen = ImageGenerator(settings.MEDIA_DIR)
        items = db.query(ContentItem).filter(ContentItem.status.in_(["draft", "qa_pending"])).limit(payload.get("limit", 8)).all()
        produced = []
        for item in items:
            existing = db.query(MediaAsset).filter(MediaAsset.meta.contains({"content_id": item.id})).first()
            if existing:
                continue
            fmt = item.format or "post"
            slides = None
            if fmt == "carousel":
                from ..ai.content_engine import carousel_slides
                slides = carousel_slides({"title": item.topic, "fact": item.body, "id": "custom"})
            out = gen.render(fmt=fmt, title=item.topic, subtitle=item.body, slides=slides, brand=settings.BRAND_NAME)
            asset = MediaAsset(kind="image", path=out["path"], filename=os.path.basename(out["path"]),
                               mime=out.get("mime", "image/png"), width=out.get("width", 1080), height=out.get("height", 1080),
                               size=out.get("size", 0),
                               meta={"content_id": item.id, "format": fmt, "template": out.get("template", fmt),
                                     "engine": out.get("engine", "local_pillow"), "slide_count": out.get("count")})
            db.add(asset)
            db.flush()
            item.media_ids = (item.media_ids or []) + [asset.id]
            produced.append({"content_id": item.id, "asset_id": asset.id, "template": out["template"]})
        self.log("visuals_generated", f"{len(produced)} assets")
        return {"status": "done", "assets": len(produced), "items": produced}
