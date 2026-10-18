const $ = (sel) => document.querySelector(sel);

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

const day = (iso) => iso ? new Date(iso).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" }) : "";

const SOURCE_LABEL = { chatgpt: "ChatGPT", claude_code: "Claude Code", transcript: "Transcript" };

async function api(path, opts = {}) {
  const res = await fetch(path, opts);
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || res.statusText);
  return res.json();
}
const post = (path, body) => api(path, {
  method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
});

function citation(src) {
  return `<blockquote>“${esc(src.quote)}”
    <cite>${esc(SOURCE_LABEL[src.type] || src.type)} · ${esc(src.title)} · ${esc(src.locator)}</cite>
  </blockquote>`;
}

async function loadStats() {
  const s = await api("/api/stats");
  const pct = (x) => `${Math.round(x * 100)}%`;
  $("#stats").innerHTML = `
    <div class="stat"><b>${s.by_status.settled || 0}</b><span>settled</span></div>
    <div class="stat"><b>${s.by_status.proposed || 0}</b><span>to review</span></div>
    <div class="stat"><b>${s.corrections}</b><span>corrections learned</span></div>
    <div class="stat"><b>${pct(s.precision_before)} → <span class="up">${pct(s.precision_after)}</span></b><span>extraction precision</span></div>`;
  const b = $("#backend");
  b.hidden = s.backend !== "fake";
  b.textContent = "demo data (fake backend)";
}

async function loadEntries() {
  const params = new URLSearchParams();
  for (const [k, id] of [["q", "#f-q"], ["status", "#f-status"], ["kind", "#f-kind"]]) {
    const v = $(id).value.trim();
    if (v) params.set(k, v);
  }
  const entries = await api(`/api/entries?${params}`);
  const ul = $("#entries");
  if (!entries.length) {
    ul.innerHTML = `<li class="empty">No entries match.</li>`;
    return;
  }
  ul.innerHTML = entries.map((e) => `
    <li class="entry ${e.status === "rejected" || e.status === "superseded" ? "dim" : ""}" data-id="${esc(e.id)}">
      <div class="meta">
        <span class="badge">${esc(e.kind.replace("_", " "))}</span>
        <span class="badge ${esc(e.status)}">${esc(e.status)}</span>
        ${e.trust === "quarantined" ? `<span class="badge quarantined">quarantined</span>` : ""}
        <span>${day(e.decided_at)}</span>
        <span>· confidence ${Math.round((e.confidence ?? 0) * 100)}%</span>
        ${e.superseded_by ? `<span>· superseded by ${esc(e.superseded_by)}</span>` : ""}
      </div>
      <h4>${esc(e.title)}</h4>
      <p>${esc(e.statement)}</p>
      ${e.rationale ? `<p class="why">Why: ${esc(e.rationale)}</p>` : ""}
      ${e.alternatives_rejected?.length ? `<p class="why">Rejected: ${e.alternatives_rejected.map(esc).join(", ")}</p>` : ""}
      ${citation(e.source)}
      ${e.status === "proposed" ? `
        <div class="actions">
          <button class="primary" data-action="settle">Settle</button>
          <button class="reject" data-action="reject">Reject</button>
        </div>` : ""}
    </li>`).join("");
}

const refresh = () => Promise.all([loadStats(), loadEntries()]);

$("#entries").addEventListener("click", async (ev) => {
  const btn = ev.target.closest("button[data-action]");
  if (!btn) return;
  const id = btn.closest(".entry").dataset.id;
  btn.disabled = true;
  try {
    await post(`/api/entries/${encodeURIComponent(id)}/review`, { action: btn.dataset.action });
    await refresh();
  } catch (err) {
    alert(err.message);
    btn.disabled = false;
  }
});

const HEADLINE = {
  contradicts: "Contradicts a settled decision",
  supersedes: "Supersedes a settled decision",
  consistent: "Consistent with your decisions",
  unrelated: "No related decisions found",
};

$("#check-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const text = $("#check-text").value.trim();
  if (!text) return;
  const btn = ev.target.querySelector("button[type=submit]");
  btn.disabled = true;
  $("#verdict").innerHTML = `<p class="hint">Checking…</p>`;
  try {
    const v = await post("/api/check", { text });
    $("#verdict").innerHTML = `
      <div class="verdict ${esc(v.verdict)}">
        <h3>${HEADLINE[v.verdict] || esc(v.verdict)}</h3>
        ${v.conflicts.map((c) => `
          <div class="conflict">
            <p><b>${esc(c.entry.title)}</b> (decided ${day(c.entry.decided_at)})</p>
            <p class="why">${esc(c.explanation)}</p>
            ${citation(c.entry.source)}
          </div>`).join("")}
        <p class="model">model: ${esc(v.model)}</p>
      </div>`;
  } catch (err) {
    $("#verdict").innerHTML = `<p class="hint">Check failed: ${esc(err.message)}</p>`;
  } finally {
    btn.disabled = false;
  }
});

document.querySelectorAll("[data-sample]").forEach((b) => b.addEventListener("click", () => {
  $("#check-text").value = b.dataset.sample;
  $("#check-form").requestSubmit();
}));

let searchTimer;
$("#f-q").addEventListener("input", () => { clearTimeout(searchTimer); searchTimer = setTimeout(loadEntries, 200); });
$("#f-status").addEventListener("change", loadEntries);
$("#f-kind").addEventListener("change", loadEntries);

$("#ingest-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const fd = new FormData();
  fd.append("file", $("#ingest-file").files[0]);
  const kind = $("#ingest-kind").value;
  if (kind) fd.append("kind", kind);
  try {
    const r = await api("/api/ingest", { method: "POST", body: fd });
    $("#src-msg").textContent = `Ingested ${r.messages} messages from ${r.sources} source(s). Now extract.`;
  } catch (err) {
    $("#src-msg").textContent = `Ingest failed: ${err.message}`;
  }
});

$("#extract-btn").addEventListener("click", async (ev) => {
  const btn = ev.currentTarget;
  btn.disabled = true;
  $("#src-msg").textContent = "Extracting…";
  try {
    const found = await post("/api/extract", {});
    $("#src-msg").textContent = found.length
      ? `Found ${found.length} new candidate(s). Review them in the ledger.`
      : "Nothing new to extract.";
    await refresh();
  } catch (err) {
    $("#src-msg").textContent = `Extract failed: ${err.message}`;
  } finally {
    btn.disabled = false;
  }
});

refresh().catch((err) => { $("#entries").innerHTML = `<li class="empty">Could not load: ${esc(err.message)}</li>`; });
