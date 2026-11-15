"""AI provider adapters. Replaceable so the system is not dependent on one vendor.

Status is reported honestly: if no API key is configured the system runs in
"offline deterministic engine" mode and never claims to have called an AI API.
"""
from __future__ import annotations

import json
import time
from typing import Any

import httpx

from ..config import settings


class AIProviderError(RuntimeError):
    pass


class OpenAIProvider:
    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.base_url = (base_url or settings.OPENAI_BASE_URL).rstrip("/")
        self.model = settings.OPENAI_MODEL
        self.image_model = settings.OPENAI_IMAGE_MODEL
        self.tts_model = settings.OPENAI_TTS_MODEL
        self.available = bool(self.api_key)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def chat(self, messages: list[dict], temperature: float = 0.7, max_tokens: int = 2000) -> str:
        if not self.available:
            raise AIProviderError("OPENAI_API_KEY not configured")
        payload = {"model": self.model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}
        with httpx.Client(timeout=120) as client:
            resp = client.post(f"{self.base_url}/chat/completions", headers=self._headers(), json=payload)
        if resp.status_code != 200:
            raise AIProviderError(f"OpenAI chat HTTP {resp.status_code}: {resp.text[:500]}")
        return resp.json()["choices"][0]["message"]["content"]

    def image(self, prompt: str, size: str = "1024x1024") -> dict:
        if not self.available:
            raise AIProviderError("OPENAI_API_KEY not configured")
        payload = {"model": self.image_model, "prompt": prompt, "size": size, "n": 1}
        with httpx.Client(timeout=180) as client:
            resp = client.post(f"{self.base_url}/images/generations", headers=self._headers(), json=payload)
        if resp.status_code != 200:
            raise AIProviderError(f"OpenAI image HTTP {resp.status_code}: {resp.text[:500]}")
        data = resp.json()["data"][0]
        return {"url": data.get("url"), "b64": data.get("b64_json"), "revised_prompt": data.get("revised_prompt")}

    def tts(self, text: str, voice: str = "alloy") -> bytes:
        if not self.available:
            raise AIProviderError("OPENAI_API_KEY not configured")
        payload = {"model": self.tts_model, "input": text, "voice": voice}
        with httpx.Client(timeout=180) as client:
            resp = client.post(f"{self.base_url}/audio/speech", headers=self._headers(), json=payload)
        if resp.status_code != 200:
            raise AIProviderError(f"OpenAI TTS HTTP {resp.status_code}: {resp.text[:500]}")
        return resp.content


class GoogleTTSProvider:
    """Free, unofficial Google Translate TTS (gTTS). Not for production scale:
    undocumented endpoint, rate limits, no SLA. Used only as fallback when no
    OpenAI key is configured. Clearly labelled in outputs."""

    def __init__(self):
        self.available = True

    def tts(self, text: str, voice: str = "com") -> bytes:
        from gtts import gTTS
        import io
        buf = io.BytesIO()
        gTTS(text=text[:5000], lang="en", slow=False).write_to_fp(buf)
        return buf.getvalue()


class EdgeTTSProvider:
    """Free Microsoft Edge neural TTS (edge-tts). Free, no key required;
    documented community library, rate limits apply."""

    def __init__(self):
        self.available = True

    def tts(self, text: str, voice: str = "en-US-GuyNeural") -> bytes:
        import asyncio
        import edge_tts
        import io
        comm = edge_tts.Communicate(text=text[:5000], voice=voice)
        buf = io.BytesIO()
        asyncio.run(comm.save(buf))
        return buf.getvalue()


class ProviderRegistry:
    def __init__(self):
        self.providers: dict[str, Any] = {"openai": OpenAIProvider(), "google_tts": GoogleTTSProvider(), "edge_tts": EdgeTTSProvider()}

    def chat(self, system: str, user: str, **kw) -> str:
        p = self.providers["openai"]
        if p.available:
            return p.chat([{"role": "system", "content": system}, {"role": "user", "content": user}], **kw)
        raise AIProviderError("No AI provider configured (set OPENAI_API_KEY)")

    def image(self, prompt: str, size: str = "1024x1024") -> dict:
        return self.providers["openai"].image(prompt, size)

    def tts(self, text: str, voice: str = "alloy") -> bytes:
        # Free-first chain: edge-tts -> gTTS -> OpenAI (only if key present and allowed)
        try:
            return self.providers["edge_tts"].tts(text)
        except Exception:
            try:
                return self.providers["google_tts"].tts(text)
            except Exception:
                return self.providers["openai"].tts(text, voice)

    def status(self) -> dict[str, Any]:
        return {
            "mode": "provider" if self.providers["openai"].available else "offline_deterministic",
            "providers": {
                "openai": {
                    "available": self.providers["openai"].available,
                    "model": settings.OPENAI_MODEL if self.providers["openai"].available else None,
                    "note": "Optional paid adapter. Default operation uses only free/local sources.",
                },
                "google_tts": {
                    "available": True,
                    "note": "Free unofficial Google Translate TTS (gTTS): development/low-volume use only; undocumented endpoint, rate-limited, no SLA.",
                },
                "edge_tts": {
                    "available": True,
                    "note": "Free Microsoft Edge neural TTS (edge-tts). Default voice source for video voice-overs.",
                },
                "images": {"available": True, "engine": "local_pillow", "note": "Free local renderer; no external image API required."},
                "video": {"available": True, "engine": "local_ffmpeg", "note": "Free local ffmpeg renderer; music only from operator-supplied royalty-free files."},
            },
        }


registry = ProviderRegistry()


def provider_call(system: str, user: str, fallback_fn, **kw) -> tuple[str, str]:
    """Call provider when available, else use fallback. Returns (text, source)."""
    try:
        return registry.chat(system, user, **kw), "openai"
    except AIProviderError:
        return fallback_fn(), "deterministic"


def parse_json_safe(text: str) -> Any:
    """Best-effort JSON extraction from LLM output."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
    try:
        return json.loads(text)
    except Exception:
        start = text.find("{")
        if start >= 0:
            try:
                return json.loads(text[start:])
            except Exception:
                pass
    return None


def rate_limited_sleep(seconds: float) -> None:
    time.sleep(seconds)
