# MASTER_SKILLS.md — capability map

What the Shophippy Social Media Marketing OS can do, and where to trigger each skill.

| Skill | What it does | UI page | API |
|---|---|---|---|
| Content engine | Ideas, scoring, daily plans, drafts, AI batch generation, approval | Ideas, Content | `/ideas`, `/ideas/score`, `/content`, `/content/generate`, `/content/{id}/approve` |
| Agent workforce | 12 toggleable agents (copywriter, designer, researcher, strategist, QA, publisher, CMO, analytics, audience, community, trends, video) | Agents | `/agents`, `/agents/{key}/toggle`, `/agents/{key}/run` |
| Automation pipeline | APScheduler research->strategy->create->QA->publish->analytics->optimize on PKT schedule | Automation | `/automation`, `/automation/run-step`, `/automation/reschedule` |
| Scheduling | Approve then schedule to accounts; past dates rejected | Calendar, Schedule | `/content/{id}/schedule`, `/schedule`, `/calendar` |
| Publishing | Multi-platform posts via social accounts; kill switch `autonomous_publishing` (default OFF) | Accounts, Publish | `/accounts`, `/accounts/{id}/test`, `/automation/publishing-toggle`, `/jobs/process` |
| OAuth connect | Facebook, Instagram, LinkedIn, Pinterest, Threads, TikTok, X, YouTube | Accounts | `/oauth/platforms`, `/oauth/{platform}/connect`, `/oauth/credentials` |
| Media production | AI images, videos (scenes/voice), PDF lead-magnet guides | Media | `/media/generate-image`, `/media/generate-video`, `/media/guide-pdf`, `/media/{id}/file`, `/media/{id}/download` |
| Research & audience | Audience/trend research runs, reports, personas | Research | `/research`, `/research/run`, `/personas` |
| Analytics | Post metrics, published history, analytics summary | Analytics | `/analytics`, `/published`, `/published/{id}/metrics` |
| Community | Comment inbox with reply/escalate | Community | `/comments`, `/comments/{id}/reply`, `/comments/{id}/escalate` |
| Landing & leads | Landing page payload + lead capture | Leads | `/landing`, `/leads` |
| Campaigns | Theme/budget/date campaign tracking | Campaigns | `/campaigns` |
| Settings | Brand, timezone, QA threshold, automation toggles | Settings | `/settings`, `/status` |
| Notifications & logs | System notifications + audit trail | Logs | `/notifications`, `/notifications/read`, `/logs` |

Safety rails:

- Autonomous publishing is OFF by default; the publisher runs only via manual force or an
  explicit toggle.
- `REQUIRE_APPROVAL` default true: nothing publishes without an approval step.
- Schedules are validated against the configured timezone; past timestamps return 400.
