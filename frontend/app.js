/* Shophippy Social Media Marketing OS — dashboard SPA */
const $ = (sel) => document.querySelector(sel);
const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmt = (s) => (s && s.length > 60 ? s.slice(0, 60) + "…" : s || "");
const tag = (s) => `<span class="tag ${esc(s || "")}">${esc(s || "")}</span>`;

function api(method, path, body) {
  const opts = { method, headers: {} };
  if (body !== undefined) { opts.headers["Content-Type"] = "application/json"; opts.body = JSON.stringify(body); }
  const tok = localStorage.getItem("smmo_token");
  if (tok) opts.headers["Authorization"] = "Bearer " + tok;
  return fetch("/api/v1" + path, opts).then(async (r) => {
    let data = null;
    try { data = await r.json(); } catch (e) { data = null; }
    if (r.status === 401 && !path.startsWith("/auth/")) { logout(); throw new Error("unauthorized"); }
    if (!r.ok) throw new Error((data && data.detail) || ("HTTP " + r.status));
    return data;
  });
}

function toast(msg, kind) {
  const t = $("#toast");
  t.textContent = msg;
  t.className = "toast " + (kind || "");
  t.classList.remove("hidden");
  setTimeout(() => t.classList.add("hidden"), 4000);
}

function openModal(title, bodyHtml, onOk) {
  $("#modal-title").textContent = title;
  $("#modal-body").innerHTML = bodyHtml;
  $("#modal-backdrop").classList.remove("hidden");
  $("#modal-ok").onclick = onOk;
}
$("#modal-cancel").onclick = () => $("#modal-backdrop").classList.add("hidden");
$("#modal-backdrop").addEventListener("click", (e) => { if (e.target.id === "modal-backdrop") $("#modal-backdrop").classList.add("hidden"); });

function formVals(sel) {
  const out = {};
  document.querySelectorAll(sel + " [data-field]").forEach((el) => {
    let v = el.type === "checkbox" ? el.checked : el.value;
    if (el.dataset.json) { try { v = JSON.parse(v); } catch (e) { v = el.value; } }
    out[el.dataset.field] = v;
  });
  return out;
}

function login(username, password) {
  return api("POST", "/auth/login", { username, password }).then((d) => {
    localStorage.setItem("smmo_token", d.token);
    localStorage.setItem("smmo_user", JSON.stringify(d.user || {}));
    return d;
  });
}

function logout() {
  localStorage.removeItem("smmo_token");
  localStorage.removeItem("smmo_user");
  location.hash = "login";
  location.reload();
}

const NAV = [
  ["overview", "Overview"],
  ["content", "Content Pipeline"],
  ["calendar", "Calendar"],
  ["media", "Media Studio"],
  ["accounts", "Social Accounts"],
  ["analytics", "Analytics"],
  ["comments", "Community"],
  ["leads", "Leads & Landing"],
  ["campaigns", "Campaigns"],
  ["agents", "Agents & Tasks"],
  ["jobs", "Job Queue"],
  ["automation", "Automation"],
  ["settings", "Settings"],
  ["notifications", "Notifications"],
  ["research", "Research & Ideas"],
  ["published", "Published Posts"],
  ["logs", "Audit Log"],
  ["health", "System Health"],
];

const PAGES = {};
function page(name, fn) { PAGES[name] = fn; }

function route() {
  const hash = (location.hash || "#overview").replace("#", "");
  const name = PAGES[hash] ? hash : "overview";
  document.querySelectorAll("#nav button").forEach((b) => b.classList.toggle("active", b.dataset.page === name));
  $("#page-title").textContent = NAV.find((n) => n[0] === name)[1];
  PAGES[name]($("#page"));
}

function renderNav() {
  $("#nav").innerHTML = NAV.map(([id, label]) => `<button data-page="${id}">${esc(label)}</button>`).join("");
  document.querySelectorAll("#nav button").forEach((b) => (b.onclick = () => { location.hash = b.dataset.page; }));
}

function kpi(label, value) {
  return `<div class="card"><div class="kpi-label">${esc(label)}</div><div class="kpi">${esc(value)}</div></div>`;
}
function table(headers, rows) {
  if (!rows.length) return `<div class="empty">No records yet.</div>`;
  return `<div class="card"><table><thead><tr>${headers.map((h) => `<th>${esc(h)}</th>`).join("")}</tr></thead><tbody>${rows.map((r) => `<tr>${r.map((c) => `<td>${c}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
}
const iso = (s) => (s ? String(s).replace("T", " ").slice(0, 19) : "—");

page("overview", (el) => {
  Promise.all([api("GET", "/overview"), api("GET", "/status")]).then(([ov, st]) => {
    el.innerHTML = `
      <div class="grid cols-4 section">
        ${kpi("Accounts", ov.accounts)}${kpi("Scheduled", ov.scheduled)}${kpi("Pending QA", ov.pending_qa)}${kpi("Published today", ov.published_today)}
        ${kpi("Followers", ov.followers)}${kpi("Impressions 30d", ov.impressions_30d)}${kpi("Engagement rate", ov.engagement_rate_pct + "%")}${kpi("Leads", ov.leads)}
      </div>
      <div class="grid cols-2">
        <div class="card"><h3>System status</h3>
          <p>Provider: ${esc(st.provider?.mode || "unknown")}</p>
          <p>OpenAI available: ${st.provider?.providers?.openai?.available ? "yes" : "no"}</p>
          <p>Autonomous publishing: ${st.autonomous_publishing ? "ON" : "OFF (kill switch)"}</p>
          <p>Automation: ${st.automation_enabled ? "enabled" : "disabled"}</p>
          <p>Dead jobs: ${st.dead_jobs}</p>
          <p>Timezone: ${esc(st.timezone)}</p>
          <p>Schedule (PKT): ${Object.entries(st.schedule || {}).map(([k, v]) => `${esc(k)} ${esc(v)}`).join(" · ")}</p>
        </div>
        <div class="card"><h3>Quick actions</h3>
          <div class="row">
            <button class="btn primary" onclick="api('POST','/content/generate?count=3').then(()=>{toast('Generation queued','ok');route()})">Generate content batch</button>
            <button class="btn" onclick="api('POST','/jobs/process').then(()=>{toast('Queue processed','ok');route()})">Process job queue</button>
            <button class="btn" onclick="location.hash='research'">Run research</button>
            <button class="btn" onclick="location.hash='automation'">Automation</button>
          </div>
        </div>
      </div>`;
  }).catch((e) => { el.innerHTML = `<div class="error">${esc(e.message)}</div>`; });
});

page("health", (el) => {
  api("GET", "/health").then((h) => {
    el.innerHTML = `<div class="card"><h3>Health</h3><pre>${esc(JSON.stringify(h, null, 2))}</pre></div>`;
    $("#conn-status").textContent = "online";
    $("#conn-status").className = "pill ok";
  }).catch(() => { $("#conn-status").textContent = "offline"; });
});

page("status", (el) => {
  api("GET", "/status").then((s) => { el.innerHTML = `<div class="card"><pre>${esc(JSON.stringify(s, null, 2))}</pre></div>`; });
});

page("content", (el) => {
  api("GET", "/content?limit=50").then((items) => {
    const rows = items.map((i) => [
      i.id, esc(fmt(i.topic)), esc(i.format || ""), tag(i.status), esc(fmt(i.title)),
      `<div class="actions"><button class="btn small" onclick="approveItem(${i.id})">Approve</button>` +
      `<button class="btn small" onclick="scheduleItem(${i.id})">Schedule</button>` +
      `<button class="btn small" onclick="viewItem(${i.id})">View</button></div>`,
    ]);
    el.innerHTML = `
      <div class="row section">
        <button class="btn primary" onclick="generateContent()">Generate batch</button>
        <button class="btn" onclick="createContentForm()">New draft</button>
      </div>
      ${table(["ID", "Topic", "Format", "Status", "Title", "Actions"], rows)}`;
  }).catch((e) => { el.innerHTML = `<div class="error">${esc(e.message)}</div>`; });
});

function approveItem(id) {
  api("POST", "/content/" + id + "/approve").then(() => { toast("Approved", "ok"); route(); }).catch((e) => toast(e.message, "err"));
}
function viewItem(id) {
  api("GET", "/content/" + id).then((ci) => {
    openModal("Content #" + ci.id, `<div class="card"><h3>${esc(ci.title || ci.topic)}</h3><p>${esc(ci.body || "")}</p>` +
      `<p class="muted">Status: ${esc(ci.status)} · Format: ${esc(ci.format)}</p>` +
      `<p>Hashtags: ${esc((ci.hashtags || []).join(" "))}</p>` +
      `<p>Citations: ${(ci.citations || []).length}</p>` +
      `<h4>QA report</h4><pre>${esc(JSON.stringify(ci.qa_report, null, 2))}</pre></div>`, () => {
      $("#modal-backdrop").classList.add("hidden");
    });
  });
}
function scheduleItem(id) {
  api("GET", "/accounts").then((accs) => {
    if (!accs.length) { toast("Connect a social account first", "err"); return; }
    const opts = accs.map((a) => `<option value="${a.id}">${esc(a.platform)} / ${esc(a.name || a.handle || "")}</option>`).join("");
    openModal("Schedule content #" + id, `
      <label>Account</label><select data-field="account_id">${opts}</select>
      <label>Scheduled at (PKT ISO)</label><input data-field="scheduled_at" type="text" value="${new Date(Date.now() + 3600000).toISOString().slice(0, 19)}">
    `, () => {
      const v = formVals("#modal-body");
      api("POST", "/content/" + id + "/schedule", { account_id: Number(v["account_id"]), scheduled_at: v["scheduled_at"] + "Z" })
        .then(() => { toast("Scheduled", "ok"); $("#modal-backdrop").classList.add("hidden"); route(); })
        .catch((e) => toast(e.message, "err"));
    });
  });
}
function generateContent() {
  api("POST", "/content/generate?count=3").then(() => { toast("Content generation queued", "ok"); route(); }).catch((e) => toast(e.message, "err"));
}
function createContentForm() {
  openModal("New draft", `
    <label>Topic</label><input data-field="topic" value="New topic">
    <label>Format</label><select data-field="format"><option>post</option><option>carousel</option><option>reel</option><option>short</option><option>video</option><option>guide</option></select>
    <label>Title</label><input data-field="title">
    <label>Body</label><textarea data-field="body" rows="5"></textarea>
  `, () => {
    const v = formVals("#modal-body");
    api("POST", "/content", v).then(() => { toast("Draft created", "ok"); $("#modal-backdrop").classList.add("hidden"); route(); }).catch((e) => toast(e.message, "err"));
  });
}

page("calendar", (el) => {
  api("GET", "/calendar").then((rows) => {
    const data = rows.map((r) => [r.id, esc(fmt(r.title)), tag(r.status), iso(r.scheduled_at), esc(r.platform || ""), r.account_id]);
    el.innerHTML = table(["ID", "Content", "Status", "Scheduled at", "Platform", "Account"], data);
  }).catch((e) => { el.innerHTML = `<div class="error">${esc(e.message)}</div>`; });
});

page("media", (el) => {
  api("GET", "/media").then((assets) => {
    const cards = assets.map((a) => {
      const src = a.kind === "image" ? "/api/v1/media/" + a.id + "/file" : null;
      const body = src ? `<img src="${src}" style="width:100%;border-radius:8px">` :
        a.kind === "video" ? `<div class="empty">Video · ${esc(a.filename)}<br><span class="muted">${a.width}x${a.height}</span></div>` :
        `<div class="empty">PDF · ${esc(a.filename)}</div>`;
      return `<div class="card"><h3>${esc(a.kind)}</h3>${body}<p class="muted small">${esc(a.filename)} · ${(a.size / 1024).toFixed(1)} KB</p>` +
        `<div class="actions"><a class="btn small" href="/api/v1/media/${a.id}/download">Download</a></div></div>`;
    }).join("");
    el.innerHTML = `
      <div class="row section">
        <button class="btn primary" onclick="genImage()">Generate image</button>
        <button class="btn" onclick="genVideo()">Generate video</button>
        <button class="btn" onclick="genGuide()">Generate guide PDF</button>
      </div>
      <div class="grid cols-3">${cards || '<div class="empty">No media yet.</div>'}</div>`;
  }).catch((e) => { el.innerHTML = `<div class="error">${esc(e.message)}</div>`; });
});
function genImage() {
  api("POST", "/media/generate-image", { format: "infographic", title: "Milestones graphic", subtitle: "Research-based tips" })
    .then(() => { toast("Image generated", "ok"); route(); }).catch((e) => toast(e.message, "err"));
}
function genVideo() {
  api("POST", "/media/generate-video", { title: "Lesson", per_scene: 6, voice: false })
    .then(() => { toast("Video render queued", "ok"); route(); }).catch((e) => toast(e.message, "err"));
}
function genGuide() {
  api("POST", "/media/guide-pdf?topic=Developmental%20Psychology%20Guide")
    .then((r) => { toast("PDF: " + r.filename, "ok"); }).catch((e) => toast(e.message, "err"));
}

page("accounts", (el) => {
  Promise.all([api("GET", "/accounts"), api("GET", "/oauth/platforms")]).then(([accs, plats]) => {
    const rows = accs.map((a) => [
      a.id, esc(a.platform), esc(a.name || ""), esc(a.handle || ""), tag(a.status),
      a.auto_publish ? "on" : "off", a.daily_limit,
      `<div class="actions"><button class="btn small" onclick="api('POST','/accounts/${a.id}/toggle').then(route)">Toggle</button>` +
      `<button class="btn small" onclick="api('POST','/accounts/${a.id}/test').then(r=>toast(JSON.stringify(r),'ok')).catch(e=>toast(e.message,'err'))">Test</button>` +
      `<button class="btn small danger" onclick="api('DELETE','/accounts/${a.id}').then(route)">Delete</button></div>`,
    ]);
    el.innerHTML = `
      <div class="grid cols-2 section">
        <div class="card"><h3>Connected accounts</h3>${table(["ID", "Platform", "Name", "Handle", "Status", "Auto", "Limit", ""], rows)}</div>
        <div class="card"><h3>Connect account</h3>
          <label>Platform</label><select data-field="platform">${(plats.platforms || plats || []).map((p) => `<option>${esc(p)}</option>`).join("")}</select>
          <label>Account ID / page id</label><input data-field="account_id" placeholder="e.g. 17841400000000000">
          <label>Name</label><input data-field="name">
          <label>Handle</label><input data-field="handle">
          <label>Access token</label><input data-field="access_token">
          <label>Daily limit</label><input data-field="daily_limit" type="number" value="3">
          <p><button class="btn primary" onclick="addAccount()">Connect</button></p>
          <p class="muted small">OAuth: use /oauth/{platform}/connect in a browser; tokens are stored encrypted.</p>
        </div>
      </div>`;
  }).catch((e) => { el.innerHTML = `<div class="error">${esc(e.message)}</div>`; });
});
function addAccount() {
  const v = formVals("#modal-body") || {};
  const body = { platform: document.querySelector('[data-field="platform"]').value, account_id: document.querySelector('[data-field="account_id"]').value, name: document.querySelector('[data-field="name"]').value, handle: document.querySelector('[data-field="handle"]').value, access_token: document.querySelector('[data-field="access_token"]').value, daily_limit: Number(document.querySelector('[data-field="daily_limit"]').value) };
  api("POST", "/accounts", body).then(() => { toast("Account connected", "ok"); route(); }).catch((e) => toast(e.message, "err"));
}

page("analytics", (el) => {
  api("GET", "/analytics").then((a) => {
    const srows = Object.entries(a.series || {}).map(([d, v]) => [d, v.impressions, v.engagement, v.followers]);
    const trows = (a.top_posts || []).map((p) => [esc(fmt(p.topic)), p.score, iso(p.published_at)]);
    el.innerHTML = `
      <div class="grid cols-2">
        <div class="card"><h3>Daily series</h3>${table(["Date", "Impressions", "Engagement", "Followers"], srows)}</div>
        <div class="card"><h3>Top posts</h3>${table(["Topic", "Score", "Published"], trows)}</div>
      </div>`;
  }).catch((e) => { el.innerHTML = `<div class="error">${esc(e.message)}</div>`; });
});

page("comments", (el) => {
  api("GET", "/comments").then((cs) => {
    const rows = cs.map((c) => [
      c.id, esc(c.author || ""), esc(fmt(c.text)), tag(c.sentiment || ""), tag(c.status),
      c.risk_flag ? "YES" : "",
      `<div class="actions"><button class="btn small" onclick="replyComment(${c.id})">Reply</button>` +
      `<button class="btn small danger" onclick="api('POST','/comments/${c.id}/escalate').then(route)">Escalate</button></div>`,
    ]);
    el.innerHTML = table(["ID", "Author", "Text", "Sentiment", "Status", "Risk", ""], rows);
  }).catch((e) => { el.innerHTML = `<div class="error">${esc(e.message)}</div>`; });
});
function replyComment(id) {
  openModal("Reply to comment #" + id, `<label>Reply</label><textarea data-field="reply" rows="4"></textarea>`, () => {
    const v = formVals("#modal-body");
    api("POST", "/comments/" + id + "/reply", { reply: v.reply }).then(() => { toast("Replied", "ok"); $("#modal-backdrop").classList.add("hidden"); route(); }).catch((e) => toast(e.message, "err"));
  });
}

page("leads", (el) => {
  Promise.all([api("GET", "/leads"), api("GET", "/landing")]).then(([leads, landing]) => {
    const rows = leads.map((l) => [l.id, esc(l.name || ""), esc(l.email), esc(l.phone || ""), esc(l.source || ""), esc(l.interest || ""), iso(l.created_at)]);
    el.innerHTML = `
      <div class="grid cols-2 section">
        <div class="card"><h3>Landing page</h3><p><b>${esc(landing.brand)}</b> · ${esc(landing.industry)}</p><p>${esc(landing.cta)}</p><p class="muted">Colors: ${esc(JSON.stringify(landing.colors))}</p></div>
        <div class="card"><h3>Add lead</h3>
          <label>Name</label><input data-field="name">
          <label>Email</label><input data-field="email" type="email">
          <label>Phone</label><input data-field="phone">
          <label>Interest</label><input data-field="interest">
          <p><button class="btn primary" onclick="addLead()">Add lead</button></p>
        </div>
      </div>
      ${table(["ID", "Name", "Email", "Phone", "Source", "Interest", "Created"], rows)}`;
  }).catch((e) => { el.innerHTML = `<div class="error">${esc(e.message)}</div>`; });
});
function addLead() {
  const e = document.querySelector('[data-field="email"]').value;
  const body = { name: document.querySelector('[data-field="name"]').value, email: e, phone: document.querySelector('[data-field="phone"]').value, interest: document.querySelector('[data-field="interest"]').value, source: "landing_page" };
  api("POST", "/leads", body).then(() => { toast("Lead added", "ok"); route(); }).catch((err) => toast(err.message, "err"));
}

page("campaigns", (el) => {
  api("GET", "/campaigns").then((cs) => {
    const rows = cs.map((c) => [c.id, esc(c.name), esc(c.theme || ""), esc(c.status), c.budget, c.spent, esc(c.start_date || "")]);
    el.innerHTML = `
      <div class="row section"><button class="btn primary" onclick="createCampaign()">New campaign</button></div>
      ${table(["ID", "Name", "Theme", "Status", "Budget", "Spent", "Start"], rows)}`;
  }).catch((e) => { el.innerHTML = `<div class="error">${esc(e.message)}</div>`; });
});
function createCampaign() {
  openModal("New campaign", `
    <label>Name</label><input data-field="name">
    <label>Theme</label><input data-field="theme">
    <label>Objective</label><input data-field="objective">
    <label>Start date</label><input data-field="start_date" type="date">
    <label>End date</label><input data-field="end_date" type="date">
    <label>Budget</label><input data-field="budget" type="number">
  `, () => {
    const v = formVals("#modal-body");
    api("POST", "/campaigns", v).then(() => { toast("Campaign created", "ok"); $("#modal-backdrop").classList.add("hidden"); route(); }).catch((e) => toast(e.message, "err"));
  });
}

page("agents", (el) => {
  Promise.all([api("GET", "/agents"), api("GET", "/tasks")]).then(([agents, tasks]) => {
    const rows = agents.map((a) => [
      a.id, esc(a.key), esc(a.name), a.enabled ? "on" : "off", esc(a.status || ""),
      iso(a.last_run_at),
      `<div class="actions"><button class="btn small" onclick="runAgent('${esc(a.key)}')">Run</button>` +
      `<button class="btn small" onclick="api('POST','/agents/${a.key}/toggle').then(route)">Toggle</button></div>`,
    ]);
    const trows = tasks.map((t) => [t.id, esc(t.agent_key), esc(t.task_type), tag(t.status), t.attempts, iso(t.finished_at)]);
    el.innerHTML = `
      <div class="card section"><h3>Agents</h3>${table(["ID", "Key", "Name", "Enabled", "Status", "Last run", ""], rows)}</div>
      <div class="card"><h3>Recent tasks</h3>${table(["ID", "Agent", "Task", "Status", "Attempts", "Finished"], trows)}</div>`;
  }).catch((e) => { el.innerHTML = `<div class="error">${esc(e.message)}</div>`; });
});
function runAgent(key) {
  openModal("Run agent " + key, `<label>Task type</label><input data-field="task_type" value="run">` +
    `<label>Payload JSON (optional)</label><textarea data-field="payload" data-json="true" rows="4">{}</textarea>`, () => {
    const v = formVals("#modal-body");
    api("POST", "/agents/" + key + "/run", v).then((r) => { toast("Agent run done", "ok"); $("#modal-backdrop").classList.add("hidden"); route(); }).catch((e) => toast(e.message, "err"));
  });
}

page("jobs", (el) => {
  api("GET", "/jobs").then((jobs) => {
    const rows = jobs.map((j) => [j.id, esc(j.agent), esc(j.task_type), tag(j.status), j.attempts, esc(j.last_error || ""), iso(j.next_run_at)]);
    el.innerHTML = `
      <div class="row section"><button class="btn primary" onclick="api('POST','/jobs/process').then(route)">Process queue</button></div>
      ${table(["ID", "Agent", "Task", "Status", "Attempts", "Error", "Next run"], rows)}`;
  }).catch((e) => { el.innerHTML = `<div class="error">${esc(e.message)}</div>`; });
});

page("automation", (el) => {
  api("GET", "/automation").then((s) => {
    const schedKeys = ["research", "strategy", "create", "qa", "publish_1", "publish_2", "publish_3", "analytics", "optimize"];
    const inputs = schedKeys.map((k) => `<label>schedule_${k}</label><input data-field="schedule_${k}" value="${esc(s["schedule_" + k] || "")}">`).join("");
    el.innerHTML = `<div class="card"><h3>Automation settings</h3>
      <label>Automation enabled</label><input type="checkbox" data-field="automation_enabled" ${s.automation_enabled ? "checked" : ""}>
      <label>Autonomous publishing</label><input type="checkbox" data-field="autonomous_publishing" ${s.autonomous_publishing ? "checked" : ""}>
      <label>Auto content generation</label><input type="checkbox" data-field="auto_content_generation" ${s.auto_content_generation ? "checked" : ""}>
      <label>Auto scheduling</label><input type="checkbox" data-field="auto_scheduling" ${s.auto_scheduling ? "checked" : ""}>
      <label>Auto community responses</label><input type="checkbox" data-field="auto_community_responses" ${s.auto_community_responses ? "checked" : ""}>
      <label>Require approval</label><input type="checkbox" data-field="require_approval" ${s.require_approval ? "checked" : ""}>
      <label>QA min score</label><input data-field="qa_min_score" type="number" value="${s.qa_min_score || 80}">
      <label>Max daily posts</label><input data-field="max_daily_posts" type="number" value="${s.max_daily_posts || 3}">
      ${inputs}
      <p><button class="btn primary" onclick="saveSettings()">Save</button>
      <button class="btn" onclick="api('POST','/automation/reschedule').then(()=>toast('Rescheduled','ok'))">Reschedule</button>
      <button class="btn" onclick="api('POST','/automation/publishing-toggle',{enabled:true}).then(route)">Enable autonomous publishing</button>
      <button class="btn danger" onclick="api('POST','/automation/publishing-toggle',{enabled:false}).then(route)">Disable</button></p></div>`;
  }).catch((e) => { el.innerHTML = `<div class="error">${esc(e.message)}</div>`; });
});

page("settings", (el) => {
  api("GET", "/settings").then((s) => {
    el.innerHTML = `<div class="card"><h3>Settings</h3>
      <label>Brand name</label><input data-field="brand_name" value="${esc(s.brand_name || "")}">
      <label>Industry</label><input data-field="brand_industry" value="${esc(s.brand_industry || "")}">
      <label>Brand colors (comma-separated)</label><input data-field="brand_colors" value="${esc(Array.isArray(s.brand_colors) ? s.brand_colors.join(", ") : s.brand_colors || "")}">
      <label>Timezone</label><input data-field="timezone" value="${esc(s.timezone || "")}">
      <label>Campaign budget</label><input data-field="campaign_budget" type="number" value="${s.campaign_budget || 0}">
      <label>Posting window start</label><input data-field="posting_window_start" value="${esc(s.posting_window_start || "")}">
      <label>Posting window end</label><input data-field="posting_window_end" value="${esc(s.posting_window_end || "")}">
      <label>Email notifications</label><input type="checkbox" data-field="email_notifications" ${s.email_notifications ? "checked" : ""}>
      <p><button class="btn primary" onclick="saveSettings()">Save settings</button></p></div>`;
  }).catch((e) => { el.innerHTML = `<div class="error">${esc(e.message)}</div>`; });
});
function saveSettings() {
  const body = formVals("#page");
  if (body.brand_colors && typeof body.brand_colors === "string") body.brand_colors = body.brand_colors.split(",").map((x) => x.trim()).filter(Boolean);
  api("PUT", "/settings", body).then(() => { toast("Settings saved", "ok"); route(); }).catch((e) => toast(e.message, "err"));
}

page("notifications", (el) => {
  api("GET", "/notifications").then((ns) => {
    const rows = ns.map((n) => [n.id, tag(n.level), esc(n.title), esc(n.message || ""), n.read ? "yes" : "no", iso(n.created_at)]);
    el.innerHTML = `<div class="row section"><button class="btn" onclick="api('POST','/notifications/read').then(()=>toast('Marked read','ok')).then(route)">Mark all read</button></div>` +
      table(["ID", "Level", "Title", "Message", "Read", "Created"], rows);
  }).catch((e) => { el.innerHTML = `<div class="error">${esc(e.message)}</div>`; });
});

page("research", (el) => {
  Promise.all([api("GET", "/research"), api("GET", "/ideas"), api("GET", "/personas")]).then(([reports, ideas, personas]) => {
    const rrows = reports.map((r) => [r.id, esc(fmt(r.title)), esc(r.kind || ""), esc(r.source || ""), iso(r.created_at)]);
    const irows = ideas.map((i) => [i.id, esc(fmt(i.topic)), esc(i.format || ""), i.score, tag(i.status)]);
    const prows = personas.map((p) => [p.id, esc(p.name), esc(p.segment || ""), esc(fmt((p.pain_points || []).join("; ")))]);
    el.innerHTML = `
      <div class="row section">
        <button class="btn primary" onclick="api('POST','/research/run?kind=audience').then(()=>toast('Audience research queued','ok')).then(route)">Run audience research</button>
        <button class="btn" onclick="api('POST','/research/run?kind=trend').then(()=>toast('Trend scan queued','ok')).then(route)">Trend scan</button>
        <button class="btn" onclick="api('POST','/research/run?kind=education').then(()=>toast('Education research queued','ok')).then(route)">Education research</button>
        <button class="btn" onclick="api('POST','/ideas/score').then(()=>toast('Ideas scored','ok')).then(route)">Score ideas</button>
      </div>
      <div class="card section"><h3>Research reports</h3>${table(["ID", "Title", "Kind", "Source", "Created"], rrows)}</div>
      <div class="card section"><h3>Content ideas</h3>${table(["ID", "Topic", "Format", "Score", "Status"], irows)}</div>
      <div class="card"><h3>Audience personas</h3>${table(["ID", "Name", "Segment", "Pain points"], prows)}</div>`;
  }).catch((e) => { el.innerHTML = `<div class="error">${esc(e.message)}</div>`; });
});

page("published", (el) => {
  api("GET", "/published").then((ps) => {
    const rows = ps.map((p) => [p.id, p.account_id, esc(p.platform_post_id || ""), esc(p.url || ""), iso(p.published_at), esc(JSON.stringify(p.metrics || {}))]);
    el.innerHTML = table(["ID", "Account", "Platform post id", "URL", "Published at", "Metrics"], rows);
  }).catch((e) => { el.innerHTML = `<div class="error">${esc(e.message)}</div>`; });
});

page("logs", (el) => {
  api("GET", "/logs?limit=100").then((logs) => {
    const rows = logs.map((l) => [l.id, iso(l.created_at), esc(l.actor || ""), esc(l.action), esc(l.entity || ""), esc(l.entity_id || ""), esc(fmt(l.detail || ""))]);
    el.innerHTML = table(["ID", "Time", "Actor", "Action", "Entity", "Entity id", "Detail"], rows);
  }).catch((e) => { el.innerHTML = `<div class="error">${esc(e.message)}</div>`; });
});

function boot() {
  const tok = localStorage.getItem("smmo_token");
  if (!tok) { $("#login-screen").classList.remove("hidden"); return; }
  $("#login-screen").classList.add("hidden");
  $("#app").classList.remove("hidden");
  $("#user-label").textContent = (JSON.parse(localStorage.getItem("smmo_user") || "{}").username) || "admin";
  renderNav();
  window.addEventListener("hashchange", route);
  $("#refresh-btn").onclick = () => route();
  $("#logout-btn").onclick = logout;
  route();
}
$("#login-form").addEventListener("submit", (e) => {
  e.preventDefault();
  login($("#login-username").value, $("#login-password").value)
    .then(() => { location.hash = "overview"; boot(); })
    .catch((err) => { $("#login-error").textContent = String(err.message || err); });
});
boot();
