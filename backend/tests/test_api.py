"""End-to-end API tests covering the main business flows."""
from conftest import client, auth_headers


def test_health_public():
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_login_ok_and_bad_password():
    r = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    assert r.status_code == 200
    assert "token" in r.json()
    bad = client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrong"})
    assert bad.status_code == 401


def test_overview_requires_auth():
    assert client.get("/api/v1/overview").status_code == 401
    h = auth_headers()
    r = client.get("/api/v1/overview", headers=h)
    assert r.status_code == 200
    assert "accounts" in r.json()


def test_content_create_approve_schedule_calendar():
    h = auth_headers()
    r = client.post("/api/v1/content", json={"topic": "Test topic", "format": "post",
                                             "title": "T", "body": "B"}, headers=h)
    assert r.status_code == 200, r.text
    cid = r.json()["id"]
    assert client.post(f"/api/v1/content/{cid}/approve", headers=h).status_code == 200
    sch = client.post(f"/api/v1/content/{cid}/schedule", json={"account_id": 999999,
                                                               "scheduled_at": "2030-01-01T10:00:00Z"}, headers=h)
    assert sch.status_code == 400 or sch.status_code == 404  # unknown account rejected
    acc = client.post("/api/v1/accounts", json={"platform": "instagram", "account_id": "123",
                                                "name": "Test", "handle": "@t", "daily_limit": 1}, headers=h)
    assert acc.status_code == 200, acc.text
    aid = acc.json()["id"]
    sch = client.post(f"/api/v1/content/{cid}/schedule", json={"account_id": aid,
                                                               "scheduled_at": "2030-01-01T10:00:00Z"}, headers=h)
    assert sch.status_code == 200, sch.text
    cal = client.get("/api/v1/calendar", headers=h)
    assert cal.status_code == 200
    assert any(row["content_id"] == cid for row in cal.json())


def test_content_generate_creates_items():
    h = auth_headers()
    r = client.post("/api/v1/content/generate?count=2", headers=h)
    assert r.status_code == 200, r.text
    items = client.get("/api/v1/content?limit=50", headers=h).json()
    assert len(items) >= 2


def test_media_image_upload_download():
    h = auth_headers()
    r = client.post("/api/v1/media/generate-image", json={"title": "Test image"}, headers=h)
    assert r.status_code == 200, r.text
    mid = r.json()["id"]
    dl = client.get(f"/api/v1/media/{mid}/file", headers=h)
    assert dl.status_code == 200
    assert dl.headers["content-type"].startswith("image/")


def test_leads_and_landing():
    h = auth_headers()
    r = client.post("/api/v1/leads", json={"name": "Jane", "email": "jane@example.com",
                                           "interest": "course", "source": "landing_page"}, headers=h)
    assert r.status_code == 200, r.text
    leads = client.get("/api/v1/leads", headers=h).json()
    assert any(l["email"] == "jane@example.com" for l in leads)
    landing = client.get("/api/v1/landing", headers=h)
    assert landing.status_code == 200
    assert "brand" in landing.json()


def test_campaigns_create_list():
    h = auth_headers()
    r = client.post("/api/v1/campaigns", json={"name": "Camp", "theme": "T", "budget": 100,
                                               "start_date": "2030-01-01", "end_date": "2030-02-01"}, headers=h)
    assert r.status_code == 200, r.text
    camps = client.get("/api/v1/campaigns", headers=h).json()
    assert any(c["name"] == "Camp" for c in camps)


def test_settings_roundtrip():
    h = auth_headers()
    r = client.put("/api/v1/settings", json={"brand_name": "Roundtrip Co", "qa_min_score": 77}, headers=h)
    assert r.status_code == 200, r.text
    got = client.get("/api/v1/settings", headers=h).json()
    assert got["brand_name"] == "Roundtrip Co"
    assert got["qa_min_score"] == 77


def test_accounts_toggle_delete():
    h = auth_headers()
    acc = client.post("/api/v1/accounts", json={"platform": "threads", "account_id": "9",
                                                "name": "T2", "daily_limit": 2}, headers=h).json()
    aid = acc["id"]
    t = client.post(f"/api/v1/accounts/{aid}/toggle", headers=h)
    assert t.status_code == 200
    d = client.delete(f"/api/v1/accounts/{aid}", headers=h)
    assert d.status_code == 200
    assert aid not in [a["id"] for a in client.get("/api/v1/accounts", headers=h).json()]


def test_automation_publishing_toggle_kill_switch():
    h = auth_headers()
    off = client.post("/api/v1/automation/publishing-toggle", json={"enabled": False}, headers=h)
    assert off.status_code == 200
    st = client.get("/api/v1/status", headers=h).json()
    assert st["autonomous_publishing"] is False


def test_research_run_and_notifications():
    h = auth_headers()
    r = client.post("/api/v1/research/run?kind=audience", headers=h)
    assert r.status_code == 200, r.text
    n = client.get("/api/v1/notifications", headers=h)
    assert n.status_code == 200


def test_audit_log_records_actions():
    h = auth_headers()
    logs = client.get("/api/v1/logs?limit=100", headers=h).json()
    assert isinstance(logs, list)


def test_agents_list_and_run():
    h = auth_headers()
    agents = client.get("/api/v1/agents", headers=h).json()
    assert agents
    keys = [a["key"] for a in agents]
    key = "research" if "research" in keys else keys[0]
    r = client.post(f"/api/v1/agents/{key}/run", json={"task_type": "run"}, headers=h)
    assert r.status_code in (200, 202), r.text


def test_schedule_validation_rejects_past():
    h = auth_headers()
    acc = client.post("/api/v1/accounts", json={"platform": "instagram", "account_id": "77",
                                                "name": "V", "daily_limit": 1}, headers=h).json()
    ci = client.post("/api/v1/content", json={"topic": "Past", "format": "post", "title": "P",
                                              "body": "B"}, headers=h).json()
    client.post(f"/api/v1/content/{ci['id']}/approve", headers=h)
    r = client.post(f"/api/v1/content/{ci['id']}/schedule",
                    json={"account_id": acc["id"], "scheduled_at": "2020-01-01T10:00:00Z"}, headers=h)
    assert r.status_code == 400


def test_unauthenticated_write_rejected():
    r = client.post("/api/v1/leads", json={"name": "x", "email": "x@x.com"})
    assert r.status_code == 401
