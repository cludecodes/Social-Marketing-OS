"""Original branded visual generation with Pillow (offline, no external API needed).

When an image-provider API key is configured, agents call the provider adapter
instead; this module is the real local renderer used by default.
"""
from __future__ import annotations

import os
import random
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONT_CANDIDATES = [
    os.environ.get("BRAND_FONT", ""),
    "C:\\Windows\\Fonts\\segoeui.ttf",
    "C:\\Windows\\Fonts\\segoeuib.ttf",
    "C:\\Windows\\Fonts\\arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]

SIZES = {
    "infographic": (1080, 1350),
    "carousel": (1080, 1080),
    "pin": (1000, 1500),
    "post": (1200, 630),
    "quote": (1080, 1080),
    "thumbnail": (1280, 720),
    "reel": (1080, 1920),
    "short_video": (1080, 1920),
    "banner": (1500, 500),
    "guide": (1080, 1350),
}


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    paths = list(FONT_CANDIDATES)
    if bold:
        paths = [p.replace("segoeui", "segoeuib") if "segoeui" in p else p for p in paths]
    for p in paths:
        if p and os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def gradient(w: int, h: int, c1: tuple, c2: tuple) -> Image.Image:
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / max(h - 1, 1)
        d.line([(0, y), (w, y)], fill=tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3)))
    return img


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_w: int) -> list[str]:
    words = text.split()
    lines, cur = [], ""
    for w_ in words:
        trial = (cur + " " + w_).strip()
        if draw.textlength(trial, font=font) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w_
    if cur:
        lines.append(cur)
    return lines


class ImageGenerator:
    def __init__(self, out_dir, brand_colors: str | list[str] | None = None, brand_name: str = "MindGrove Academy"):
        self.out_dir = Path(out_dir); self.out_dir.mkdir(parents=True, exist_ok=True)
        colors = brand_colors or "#4F46E5,#7C3AED,#0EA5E9,#F59E0B,#10B981"
        self.palette = [hex_to_rgb(c.strip()) for c in (colors if isinstance(colors, list) else colors.split(",")) if c.strip()]
        self.brand = brand_name

    def _decorate(self, img: Image.Image, seed: int = 0) -> None:
        rng = random.Random(seed)
        d = ImageDraw.Draw(img, "RGBA")
        w, h = img.size
        for _ in range(6):
            r = rng.randint(60, 220)
            x, y = rng.randint(-50, w), rng.randint(-50, h)
            c = self.palette[rng.randrange(len(self.palette))]
            d.ellipse([x - r, y - r, x + r, y + r], fill=c + (18,))

    def _footer(self, img: Image.Image, dark: bool = True) -> None:
        d = ImageDraw.ImageDraw(img)
        w, h = img.size
        f = load_font(34)
        txt = self.brand
        tw = d.textlength(txt, font=f)
        d.rectangle([w - tw - 60, h - 70, w - 20, h - 16], fill=(255, 255, 255, 40))
        d.text((w - tw - 40, h - 58), txt, font=f, fill=(255, 255, 255) if dark else (40, 40, 60))

    def _title_block(self, d, w, title, top, max_w, color=(255, 255, 255)):
        f_title = load_font(64, bold=True)
        lines = wrap_text(d, title, f_title, max_w)
        y = top
        for ln in lines[:4]:
            d.text((80, y), ln, font=f_title, fill=color)
            y += 76
        return y

    def render(self, fmt: str, title: str, subtitle: str = "", slides: list[dict] | None = None, brand: str | None = None) -> dict:
        self.brand = brand or self.brand
        fmt = fmt or "post"
        if fmt == "carousel" and slides:
            return self._carousel(slides, title)
        w, h = SIZES.get(fmt, SIZES["post"])
        c1, c2 = self.palette[0], self.palette[1 % len(self.palette)]
        img = gradient(w, h, c1, c2)
        self._decorate(img, seed=hash(title) % 1000)
        d = ImageDraw.Draw(img)
        dark = fmt not in ("post", "thumbnail")
        top = int(h * 0.12)
        y = self._title_block(d, w, title, top, w - 160, (255, 255, 255) if dark else (30, 30, 50))
        if subtitle:
            f_sub = load_font(40)
            for ln in wrap_text(d, subtitle, f_sub, w - 160)[:6]:
                d.text((80, y + 24), ln, font=f_sub, fill=(235, 235, 245) if dark else (70, 70, 90))
                y += 54
        self._footer(img, dark=dark)
        return self._save(img, fmt)

    def _carousel(self, slides: list[dict], title: str) -> dict:
        paths = []
        for i, sl in enumerate(slides):
            w, h = SIZES["carousel"]
            c1 = self.palette[i % len(self.palette)]
            c2 = self.palette[(i + 1) % len(self.palette)]
            img = gradient(w, h, c1, c2)
            self._decorate(img, seed=i * 7 + 3)
            d = ImageDraw.Draw(img)
            f_h = load_font(56, bold=True)
            f_b = load_font(40)
            y = 120
            for ln in wrap_text(d, sl.get("heading", "Slide"), f_h, w - 160)[:3]:
                d.text((80, y), ln, font=f_h, fill=(255, 255, 255)); y += 66
            y += 30
            for b in sl.get("bullets", [])[:5]:
                for ln in wrap_text(d, b, f_b, w - 200)[:3]:
                    d.text((110, y), "• " + ln if ln == wrap_text(d, b, f_b, w - 200)[0] else ln, font=f_b, fill=(235, 235, 245)); y += 52
                y += 10
            # progress dots
            for j in range(len(slides)):
                x = w // 2 - (len(slides) - 1) * 22 + j * 44
                d.ellipse([x, h - 60, x + 18, h - 42], fill=(255, 255, 255) if j == i else (255, 255, 255, 90))
            self._footer(img, dark=True)
            paths.append(self._save(img, f"carousel_{i}")[ "path" ])
        return {"paths": paths, "mime": "image/png", "engine": "local_pillow", "template": "carousel", "path": paths[0], "count": len(paths)}

    def _save(self, img: Image.Image, fmt: str) -> dict:
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        fname = f"{fmt}_{ts}_{abs(hash(fmt + str(datetime.utcnow()))) % 100000}.png"
        path = self.out_dir / fname
        img.save(path, "PNG", optimize=True)
        st = os.stat(path)
        return {"path": str(path), "mime": "image/png", "width": img.size[0], "height": img.size[1],
                "size": st.st_size, "template": fmt, "engine": "local_pillow"}
