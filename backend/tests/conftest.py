import os
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="smmo_test_"))
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP / 'test.db'}"
os.environ.setdefault("SECRET_KEY", "test-secret-key")

from fastapi.testclient import TestClient  # noqa: E402

from app.db import init_db  # noqa: E402
from app.api.auth import seed_admin  # noqa: E402
from app.main import app  # noqa: E402

init_db()

from app.db import db_session  # noqa: E402
from app.agents.base import ensure_all_registered  # noqa: E402

with db_session() as db:
    ensure_all_registered(db)
seed_admin()

client = TestClient(app)


def auth_headers() -> dict:
    r = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}
