"""Security helpers: password hashing (bcrypt w/ fallback) and Fernet field encryption."""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
from typing import Optional

from .config import settings

try:
    import bcrypt  # type: ignore
    _HAS_BCRYPT = True
except Exception:  # pragma: no cover
    bcrypt = None
    _HAS_BCRYPT = False

try:
    from cryptography.fernet import Fernet, InvalidToken
    _HAS_FERNET = True
except Exception:  # pragma: no cover
    Fernet = None
    InvalidToken = Exception
    _HAS_FERNET = False


def hash_password(password: str) -> str:
    if _HAS_BCRYPT:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()
    # Fallback: PBKDF2-HMAC-SHA256 (used only when bcrypt wheel unavailable)
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 600_000)
    return "pbkdf2$" + base64.b64encode(salt + dk).decode()


def verify_password(password: str, hashed: str) -> bool:
    if hashed.startswith("pbkdf2$"):
        raw = base64.b64decode(hashed.split("$", 1)[1])
        salt, dk = raw[:16], raw[16:]
        return hmac.compare_digest(hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 600_000), dk)
    if _HAS_BCRYPT:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    return False


def new_token() -> str:
    return secrets.token_urlsafe(32)


# --- Encryption at rest for OAuth tokens / secrets ---
_FERNET: Optional["Fernet"] = None


def _get_fernet() -> Optional["Fernet"]:
    global _FERNET
    if _FERNET is not None or not _HAS_FERNET:
        return _FERNET
    key = settings.SECRET_KEY.encode()
    if len(key) < 32:
        key = hashlib.sha256(key).digest()
    else:
        key = key[:32]
    _FERNET = Fernet(base64.urlsafe_b64encode(key))
    return _FERNET


def encrypt_value(plain: str) -> str:
    f = _get_fernet()
    if f is None:
        return "enc$plain$" + plain  # Clearly marked insecure dev mode
    return "enc$" + f.encrypt(plain.encode()).decode()


def decrypt_value(stored: str) -> str:
    if not stored:
        return ""
    if stored.startswith("enc$plain$"):
        return stored[len("enc$plain$"):]
    if not stored.startswith("enc$"):
        return stored
    f = _get_fernet()
    if f is None:
        return stored[4:]
    try:
        return f.decrypt(stored[4:].encode()).decode()
    except Exception:
        return ""
