# API Reference

Base URL: `http://127.0.0.1:8000/api/v1`

All endpoints require JWT auth via header `Authorization: Bearer <token>`, except
`GET /health`.

## Auth

| Method | Path | Purpose |
|---|---|---|
| POST | `/auth/login` | Body `{username, password}` -> `{token, ...}` |
| POST | `/auth/change-password` | Change current user password |
| GET | `/auth/me` | Current user info |

## Public

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness probe |

## Core

| Method | Path | Purpose |
|---|---|---|
| GET | `/status` | Provider/automation status |
| GET | `/overview` | Dashboard summary (accounts, published, scheduled, QA pending) |
| GET | `/agents` | List agents with enabled state |
| POST | `/agents/{key}/toggle` | Enable/disable agent |
| POST | `/agents/{key}/run` | Run agent once, body `{task_type: "run"}` |
| GET | `/tasks` | Task list |
| GET | `/jobs` | Job queue entries |
| POST | `/jobs/process` | Process queued jobs now |
| GET | `/research` | Research reports |
| POST | `/research/run` | Run research, query `?kind=audience` |
| GET | `/personas` | Audience personas |
| GET | `/ideas` | Content ideas with scores |
| POST | `/ideas/score` | Rescore ideas |
| GET | `/content` | Content items, query `?limit=` |
| POST | `/content` | Create draft, body `{topic, format, title, body}` |
| GET | `/content/{id}` | One item |
| PUT | `/content/{id}` | Update item |
| POST | `/content/{id}/approve` | Approve item |
| POST | `/content/generate` | AI-generate batch, query `?count=N` |
| POST | `/content/{id}/schedule` | Body `{account_id, scheduled_at}` (ISO, must be future) |
| GET | `/calendar` | Upcoming scheduled rows (includes `content_id`) |
| GET | `/media` | Media assets |
| POST | `/media/generate-image` | Body `{title}` |
| POST | `/media/generate-video` | Body `{title, scenes, per_scene, voice}` |
| GET | `/media/{id}/file` | Stream media file |
| POST | `/media/guide-pdf` | Body `{title, subtitle, ...}` |
| GET | `/media/{id}/download` | Download asset |
| GET | `/accounts` | Social accounts |
| POST | `/accounts` | Body `{platform, account_id, name, handle, daily_limit}` |
| DELETE | `/accounts/{id}` | Remove account |
| POST | `/accounts/{id}/toggle` | Flip active state |
| POST | `/accounts/{id}/test` | Test connection |
| GET | `/oauth/platforms` | OAuth platform list |
| GET | `/oauth/{platform}/connect` | Start OAuth connect |
| GET | `/oauth/{platform}/callback` | OAuth callback |
| POST | `/oauth/credentials` | Store app creds `{platform, client_id, client_secret, scopes}` |
| GET | `/schedule` | Publish schedules |
| POST | `/schedule` | Body `{content_id, account_id, scheduled_at}` |
| PUT | `/schedule/{id}` | Update schedule |
| DELETE | `/schedule/{id}` | Delete schedule |
| GET | `/campaigns` | Campaigns |
| POST | `/campaigns` | Body `{name, theme, budget, start_date, end_date}` |
| GET | `/published` | Published posts |
| GET | `/published/{id}/metrics` | Post metrics |
| GET | `/analytics` | Analytics summary |
| GET | `/comments` | Comment inbox |
| POST | `/comments/{id}/reply` | Body `{reply}` |
| POST | `/comments/{id}/escalate` | Escalate comment |
| GET | `/landing` | Landing page payload |
| GET | `/leads` | Leads |
| POST | `/leads` | Body `{name, email, interest, source}` |
| GET | `/settings` | App settings |
| PUT | `/settings` | Body `{brand_name, qa_min_score, ...}` |
| GET | `/automation` | Automation state |
| POST | `/automation/publishing-toggle` | Body `{enabled}` (kill switch) |
| POST | `/automation/run-step` | Body `{step}` |
| POST | `/automation/reschedule` | Reschedule pipeline |
| GET | `/logs` | Audit logs, query `?limit=` |
| GET | `/notifications` | Notifications |
| POST | `/notifications/read` | Mark read |

## Errors

`401` missing/invalid token, `400` validation (e.g. past `scheduled_at`, unknown account),
`404` missing resource, `500` unexpected. Body: `{"detail": "..."}`.

## Example flow

```bash
TOKEN=$(curl -s -X POST localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}' | python -c "import sys,json;print(json.load(sys.stdin)['token'])")

curl -s localhost:8000/api/v1/overview -H "Authorization: Bearer $TOKEN"
curl -s -X POST localhost:8000/api/v1/content/generate?count=2 -H "Authorization: Bearer $TOKEN"
curl -s -X POST localhost:8000/api/v1/content/1/approve -H "Authorization: Bearer $TOKEN"
curl -s -X POST localhost:8000/api/v1/content/1/schedule \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"account_id":1,"scheduled_at":"2030-01-01T10:00:00Z"}'
```
