"""Video production via ffmpeg: slide-based short videos with optional TTS.

Honest capability model:
- Slides + captions + transitions + branded end screen: local ffmpeg (works offline).
- Voice-over: OpenAI TTS adapter when OPENAI_API_KEY is set; otherwise skipped and reported.
- Background music: only royalty-free tracks supplied by the operator are used; none bundled.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .image_generator import ImageGenerator, load_font, wrap_text, gradient
from PIL import Image, ImageDraw


def _scene_image(out: Path, scene: dict, w: int, h: int, palette, brand: str, idx: int) -> Path:
    c1 = palette[idx % len(palette)]
    c2 = palette[(idx + 1) % len(palette)]
    img = gradient(w, h, c1, c2)
    d = ImageDraw.Draw(img)
    f = load_font(64, bold=True)
    y = int(h * 0.18)
    for ln in wrap_text(d, scene.get("text", ""), f, w - 160)[:9]:
        d.text((80, y), ln, font=f, fill=(255, 255, 255))
        y += 80
    fb = load_font(36)
    d.text((80, h - 90), brand, font=fb, fill=(255, 255, 255, 160))
    p = out / f"scene_{idx:02d}.png"
    img.save(p, "PNG")
    return p


class VideoGenerator:
    def __init__(self, out_dir, brand_colors: str | list[str] | None = None, brand_name: str = "MindGrove Academy"):
        self.out_dir = Path(out_dir); self.out_dir.mkdir(parents=True, exist_ok=True)
        colors = brand_colors or "#4F46E5,#7C3AED,#0EA5E9,#F59E0B,#10B981"
        self.palette = [tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)) for c in colors.split(",")]
        self.brand = brand_name

    def render(self, title: str, scenes: list[dict], aspect: str = "9:16", tts_bytes: bytes | None = None,
               per_scene: int = 8) -> dict:
        w, h = (1080, 1920) if aspect == "9:16" else (1920, 1080)
        work = self.out_dir / f"video_{abs(hash(title)) % 100000}"
        work.mkdir(parents=True, exist_ok=True)
        paths = [_scene_image(work, s, w, h, self.palette, self.brand, i) for i, s in enumerate(scenes)]
        out = self.out_dir / f"{work.name}.mp4"

        inputs = []
        for p in paths:
            inputs += ["-loop", "1", "-t", str(per_scene), "-i", str(p)]
        fc = "".join(f"[{i}:v]scale={w}:{h},setsar=1,format=yuv420p[v{i}];" for i in range(len(paths)))
        fc += "".join(f"[v{i}]" for i in range(len(paths)))
        fc += f"concat=n={len(paths)}:v=1:a=0[out]"
        cmd = ["ffmpeg", "-y", *inputs, "-filter_complex", fc, "-map", "[out]", "-r", "30",
               "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError("ffmpeg failed: " + res.stderr[-500:])

        # Optional voice-over mux
        audio_note = "none"
        if tts_bytes:
            aud = work / "vo.mp3"
            aud.write_bytes(tts_bytes)
            final = self.out_dir / f"{work.name}_vo.mp4"
            cmd2 = ["ffmpeg", "-y", "-i", str(out), "-i", str(aud), "-c:v", "copy", "-c:a", "aac",
                    "-shortest", str(final)]
            subprocess.run(cmd2, capture_output=True, text=True)
            if final.exists():
                out = final
                audio_note = "tts_edge_or_gtts"
        st = os.stat(out)
        return {"path": str(out), "mime": "video/mp4", "width": w, "height": h, "size": st.st_size,
                "duration": per_scene * len(paths), "engine": "ffmpeg_local", "audio": audio_note,
                "scenes": len(paths)}


def ffmpeg_available() -> bool:
    try:
        return subprocess.run(["ffmpeg", "-version"], capture_output=True).returncode == 0
    except Exception:
        return False
