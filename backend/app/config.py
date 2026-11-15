"""Application configuration from environment / .env file."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent
STORAGE_DIR = PROJECT_ROOT / "storage"
MEDIA_DIR = STORAGE_DIR / "media"
DATA_DIR = STORAGE_DIR / "data"
LOGS_DIR = STORAGE_DIR / "logs"
for _d in (MEDIA_DIR, DATA_DIR, LOGS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

load_dotenv(BASE_DIR / ".env")
load_dotenv(PROJECT_ROOT / ".env")


@lru_cache
def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default)


class Settings:
    # --- General ---
    APP_NAME: str = "Shophippy Social Media Marketing OS"
    ENV: str = _env("APP_ENV", "development")
    SECRET_KEY: str = _env("SECRET_KEY", "dev-change-me-to-a-long-random-string")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(_env("ACCESS_TOKEN_EXPIRE_MINUTES", "10080"))
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: list[str] = [o.strip() for o in _env("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",") if o.strip()]

    # --- Database ---
    DATABASE_URL: str = _env("DATABASE_URL", f"sqlite:///{DATA_DIR / 'shophippy.db'}")

    # --- Auth ---
    ADMIN_USERNAME: str = _env("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD: str = _env("ADMIN_PASSWORD", "admin123")

    # --- Timezone / automation ---
    TIMEZONE: str = _env("TIMEZONE", "Asia/Karachi")  # PKT default
    AUTOMATION_ENABLED: bool = _env("AUTOMATION_ENABLED", "true").lower() in {"1", "true", "yes"}
    AUTONOMOUS_PUBLISHING: bool = _env("AUTONOMOUS_PUBLISHING", "false").lower() in {"1", "true", "yes"}
    AUTO_CONTENT_GENERATION: bool = _env("AUTO_CONTENT_GENERATION", "true").lower() in {"1", "true", "yes"}
    AUTO_SCHEDULING: bool = _env("AUTO_SCHEDULING", "true").lower() in {"1", "true", "yes"}
    AUTO_COMMUNITY_RESPONSES: bool = _env("AUTO_COMMUNITY_RESPONSES", "false").lower() in {"1", "true", "yes"}
    REQUIRE_APPROVAL: bool = _env("REQUIRE_APPROVAL", "true").lower() in {"1", "true", "yes"}
    MAX_DAILY_POSTS: int = int(_env("MAX_DAILY_POSTS", "6"))
    QA_MIN_SCORE: float = float(_env("QA_MIN_SCORE", "80"))
    MAX_JOB_ATTEMPTS: int = int(_env("MAX_JOB_ATTEMPTS", "3"))

    # Automation schedule (PKT) — configurable via admin UI
    SCHEDULE: dict = {
        "research": _env("SCHED_RESEARCH", "06:00"),
        "strategy": _env("SCHED_STRATEGY", "07:00"),
        "create": _env("SCHED_CREATE", "08:00"),
        "qa": _env("SCHED_QA", "09:00"),
        "publish_1": _env("SCHED_PUBLISH_1", "10:00"),
        "publish_2": _env("SCHED_PUBLISH_2", "13:00"),
        "publish_3": _env("SCHED_PUBLISH_3", "17:00"),
        "analytics": _env("SCHED_ANALYTICS", "20:00"),
        "optimize": _env("SCHED_OPTIMIZE", "21:00"),
    }

    # --- AI providers ---
    OPENAI_API_KEY: str = _env("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: str = _env("OPENAI_BASE_URL", "https://api.openai.com/v1")
    OPENAI_MODEL: str = _env("OPENAI_MODEL", "gpt-4o-mini")
    OPENAI_IMAGE_MODEL: str = _env("OPENAI_IMAGE_MODEL", "dall-e-3")
    OPENAI_TTS_MODEL: str = _env("OPENAI_TTS_MODEL", "tts-1")
    IMAGE_PROVIDER: str = _env("IMAGE_PROVIDER", "auto")  # auto -> openai if key else local
    TTS_PROVIDER: str = _env("TTS_PROVIDER", "auto")

    # --- Social app credentials (OAuth) ---
    FACEBOOK_APP_ID: str = _env("FACEBOOK_APP_ID", "")
    FACEBOOK_APP_SECRET: str = _env("FACEBOOK_APP_SECRET", "")
    GOOGLE_CLIENT_ID: str = _env("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = _env("GOOGLE_CLIENT_SECRET", "")
    PINTEREST_APP_ID: str = _env("PINTEREST_APP_ID", "")
    PINTEREST_APP_SECRET: str = _env("PINTEREST_APP_SECRET", "")
    LINKEDIN_CLIENT_ID: str = _env("LINKEDIN_CLIENT_ID", "")
    LINKEDIN_CLIENT_SECRET: str = _env("LINKEDIN_CLIENT_SECRET", "")
    X_CLIENT_ID: str = _env("X_CLIENT_ID", "")
    X_CLIENT_SECRET: str = _env("X_CLIENT_SECRET", "")
    TIKTOK_CLIENT_KEY: str = _env("TIKTOK_CLIENT_KEY", "")
    TIKTOK_CLIENT_SECRET: str = _env("TIKTOK_CLIENT_SECRET", "")
    THREADS_CLIENT_ID: str = _env("THREADS_CLIENT_ID", "")
    THREADS_CLIENT_SECRET: str = _env("THREADS_CLIENT_SECRET", "")
    OAUTH_REDIRECT_BASE: str = _env("OAUTH_REDIRECT_BASE", "http://localhost:8000")

    # --- Brand ---
    BRAND_NAME: str = _env("BRAND_NAME", "MindGrove Academy")
    BRAND_INDUSTRY: str = _env("BRAND_INDUSTRY", "Developmental Psychology Education")
    BRAND_COLORS: str = _env("BRAND_COLORS", "#4F46E5,#7C3AED,#0EA5E9,#F59E0B,#10B981")
    BRAND_FONT: str = _env("BRAND_FONT", "C:\\Windows\\Fonts\\segoeui.ttf")

    # --- Email / lead magnets (optional) ---
    SMTP_HOST: str = _env("SMTP_HOST", "")
    SMTP_PORT: int = int(_env("SMTP_PORT", "587"))
    SMTP_USER: str = _env("SMTP_USER", "")
    SMTP_PASSWORD: str = _env("SMTP_PASSWORD", "")
    SITE_URL: str = _env("SITE_URL", "http://localhost:5173")

    # --- Storage ---
    MEDIA_DIR: Path = MEDIA_DIR
    DB_PATH: Path = DATA_DIR / "shophippy.db"


settings = Settings()
