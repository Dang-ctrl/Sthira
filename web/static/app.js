// Sthira web demo. Alpine.js state + Motion animation + Lucide icons + Chart.js + driver.js, no build step.
const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
const sleep = ms => new Promise(r => setTimeout(r, ms));

// Lucide icon as an SVG string, for use with x-html.
function ic(name, size = 16, cls = "") {
  if (!window.lucide || !lucide.icons[name]) return "";
  const el = lucide.createElement(lucide.icons[name]);
  el.setAttribute("width", size); el.setAttribute("height", size);
  el.setAttribute("class", "ic " + cls); el.setAttribute("aria-hidden", "true");
  return el.outerHTML;
}

async function j(url, opts) {
  const r = await fetch(url, opts);
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText);
  return r.json();
}
const postJSON = (url, body) => j(url, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)});
const squash = s => (s || "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
// Chart instances live outside Alpine: its reactive proxies break Chart.js internals.
const CHARTS = {};
const cssVar = name => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

function fade(el, from = 8) {
  if (!el || reduceMotion || !window.Motion) return;
  Motion.animate(el, {opacity: [0, 1], transform: [`translateY(${from}px)`, "translateY(0px)"]}, {duration: .32, ease: [.2, .8, .2, 1]});
}

function app() {
  return {
    meta: {}, entries: [], stats: {}, rules: [], agents: "", history: [], evalData: null,
    loading: true, filter: "settled", q: "",
    text: "", checking: false, verdict: null, prevVerdict: null, checkError: null,
    teach: {open: false, note: "", busy: false, done: false},
    rejecting: null, rejectNote: "",
    uploading: false, uploadMsg: "", uploadErr: false, dragging: false,
    agentsOpen: false, copied: "", toasts: [],
    shown: {settled: 0, corrections: 0}, barsIn: false,
    dark: false,
    // drawer
    drawer: null, ctx: null, ctxLoading: false,
    // palette
    palette: {open: false, q: "", i: 0},
    // simulation
    sim: {running: false, done: false, title: "", log: [], caught: 0, checked: 0, session: null},
    // install
    installTab: "cli",

    // The texts must stay exactly as recorded in demo/cached_checks.json (the offline fallback is keyed on them).
    examples: [
      {label: "MongoDB migration", hint: "conflict", text: "Migrate the user store from Postgres to MongoDB and denormalize memberships to avoid joins."},
      {label: "Password login", hint: "conflict", text: "Add email + password login with a forgot-password reset flow."},
      {label: "Mobile before web", hint: "conflict", text: "Set up the mobile app release pipeline now, before the web app is stable."},
      {label: "Dark mode", hint: "unrelated", text: "Add a dark mode toggle to the settings page."},
    ],
    tabs: [{key: "settled", label: "Settled"}, {key: "proposed", label: "To review"}, {key: "superseded", label: "Superseded"}, {key: "rejected", label: "Rejected"}],
    installs: {
      cli: {label: "CLI", note: "Local-first. Runs on Qwen3 through Ollama; nothing leaves your machine.", code:
`git clone https://github.com/HelloOjasMutreja/Sthira && cd Sthira
uv sync
uv run sthira ingest path/to/chatgpt-export.zip
uv run sthira extract        # the open-weight model proposes entries
uv run sthira review         # settle or reject; rejections teach it
uv run sthira check "Let's switch the user store to MongoDB"`},
      mcp: {label: "Claude Code · MCP", note: "The agent calls check before acting, and propose when you decide something new.", code:
`claude mcp add sthira -- uv run --directory /path/to/Sthira --extra mcp sthira mcp`},
      hook: {label: "Claude Code · hook", note: "Warns you and the agent when a prompt contradicts a settled decision. Silent when nothing is related.", code:
`{ "hooks": { "UserPromptSubmit": [ { "hooks": [ { "type": "command",
  "command": "uv run --directory /path/to/Sthira sthira hook" } ] } ] } }`},
      sync: {label: "AGENTS.md · Cursor", note: "Writes an always-fresh block of settled context where every coding agent reads it.", code:
`uv run sthira sync AGENTS.md            # or CLAUDE.md
uv run sthira sync --format cursor      # .cursor/rules/sthira.mdc`},
    },

    init() {
      const t = document.documentElement.dataset.theme;
      this.dark = t ? t === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
      j("/api/meta").then(m => this.meta = m).catch(() => {});
      j("/api/eval").then(e => this.evalData = e).catch(() => {});
      this.load();
      window.addEventListener("keydown", e => this.hotkeys(e));
      try { if (!localStorage.getItem("sthira-toured")) this.toast("New here? Take the 60-second tour.", false, {label: "Start", fn: () => this.tour()}); } catch (e) {}
    },

    hotkeys(e) {
      const k = e.key.toLowerCase();
      if ((e.ctrlKey || e.metaKey) && k === "k") { e.preventDefault(); this.palette.open ? this.closePalette() : this.openPalette(); return; }
      if (k === "escape") { if (this.palette.open) this.closePalette(); else if (this.drawer) this.closeDrawer(); return; }
      const typing = /input|textarea|select/i.test(document.activeElement?.tagName || "");
      if (!typing && k === "/") { e.preventDefault(); document.getElementById("text").focus(); }
    },

    // ---------------- data ----------------
    async load() {
      try { this.entries = await j("/api/entries"); }
      catch (e) { this.toast("Couldn’t load the ledger: " + e.message, true); }
      this.loading = false;
      this.animateRows();
      this.loadStats();
      j("/api/rules").then(r => this.rules = r).catch(() => {});
      j("/api/agents-md").then(a => this.agents = a.markdown).catch(() => {});
      j("/api/history?limit=25").then(h => this.history = h).catch(() => {});
      this.$nextTick(() => this.drawCharts());
      if (this.drawer) this.drawer = this.entries.find(e => e.id === this.drawer.id) || null;
    },

    async loadStats() {
      try { this.stats = await j("/api/stats"); } catch (e) { return; }
      const target = {settled: this.stats.entries?.settled ?? 0, corrections: this.stats.corrections ?? 0};
      for (const k of Object.keys(target)) this.countTo(k, target[k]);
      requestAnimationFrame(() => this.barsIn = true);
    },

    countTo(key, to) {
      const from = this.shown[key] || 0;
      if (reduceMotion || !window.Motion || from === to) { this.shown[key] = to; return; }
      Motion.animate(from, to, {duration: .9, ease: [.2, .8, .2, 1], onUpdate: v => this.shown[key] = Math.round(v)});
    },

    animateRows() {
      if (reduceMotion || !window.Motion) return;
      this.$nextTick(() => {
        const rows = this.$refs.rows?.querySelectorAll(".entry");
        if (rows?.length) Motion.animate(rows, {opacity: [0, 1], transform: ["translateY(6px)", "translateY(0px)"]}, {duration: .28, delay: Motion.stagger(.03)});
      });
    },

    setFilter(k) { this.filter = k; this.rejecting = null; this.animateRows(); },
    count(k) { return this.entries.filter(e => e.status === k).length; },
    visible() {
      const q = squash(this.q);
      return this.entries.filter(e => e.status === this.filter)
        .filter(e => !q || squash([e.statement, e.rationale, e.source.quote, e.source.title, e.kind].join(" ")).includes(q))
        .slice().reverse();
    },

    // Small models sometimes copy the quote or statement into the rationale; don't show it twice.
    // Near-identical only: a real reason that is merely part of a longer quote stays visible.
    showWhy(e) {
      if (!e || !e.rationale) return false;
      const a = squash(e.rationale);
      return ![e.statement, e.source.quote].some(o => {
        const b = squash(o);
        return a && b && (a.includes(b) || b.includes(a)) && Math.min(a.length, b.length) / Math.max(a.length, b.length) > .8;
      });
    },

    // ---------------- check ----------------
    async run({compare = false} = {}) {
      const text = this.text.trim();
      if (!text || this.checking) return null;
      this.prevVerdict = compare ? this.verdict : null;
      this.checking = true; this.verdict = null; this.checkError = null;
      if (!compare) this.teach = {open: false, note: "", busy: false, done: false};
      let v = null;
      try {
        v = await postJSON("/api/check", {text});
        v.conflicts = (v.conflicts || []).map(c => ({...c, mode: null, why: "", busy: false}));
        v.text = text;
        this.verdict = v;
        this.$nextTick(() => fade(document.querySelector("#console .verdict")));
      } catch (e) {
        this.checkError = {offline: /Model call failed/.test(e.message), msg: e.message, text};
      }
      this.checking = false;
      return v;
    },

    label(v) {
      if (!v) return "";
      if (v.verdict === "contradicts") return `Contradicts ${v.conflicts.length} decision${v.conflicts.length > 1 ? "s" : ""}`;
      return v.verdict === "unrelated" ? "No related decisions" : "Consistent";
    },

    footnote(v) {
      if (v.fallback === "keyword") return "Hosted model offline: keyword match on alternatives you rejected, not a model verdict.";
      if (v.fallback === "recorded") return "Recorded from a real local Qwen3 run (hosted model offline).";
      return "Flagged, then double-checked by a self-correction pass · " + v.model + (v.cached ? " · cached" : "");
    },

    async replace(c) {
      c.busy = true;
      try {
        await postJSON(`/api/entries/${encodeURIComponent(c.entry.id)}/replace`, {statement: this.verdict.text, rationale: c.why});
        c.mode = "replaced";
        this.toast("Decision replaced. The old one is kept as history.");
        this.load();
      } catch (e) { this.toast("Couldn’t replace it: " + e.message, true); }
      c.busy = false;
    },

    async sendTeach() {
      this.teach.busy = true;
      try {
        await postJSON("/api/correct", {text: this.verdict.text, note: this.teach.note});
        this.teach = {open: false, note: "", busy: false, done: true};
        this.toast("Noted. Re-check to see what it learned.");
        this.loadStats();
        j("/api/rules").then(r => this.rules = r).catch(() => {});
        j("/api/history?limit=25").then(h => this.history = h).catch(() => {});
      } catch (e) { this.teach.busy = false; this.toast("Couldn’t save the correction: " + e.message, true); }
    },

    // ---------------- review ----------------
    async review(e, action, note = null) {
      try {
        await postJSON(`/api/entries/${encodeURIComponent(e.id)}/review`, {action, note: note || null});
        this.rejecting = null;
        this.toast(action === "settle" ? "Settled. Agents will now respect it." : "Rejected. Sthira will learn from it.");
        this.load();
      } catch (err) { this.toast("Couldn’t save that: " + err.message, true); }
    },

    // ---------------- drawer ----------------
    async openDrawer(e) {
      this.drawer = e; this.ctx = null; this.ctxLoading = true;
      document.body.style.overflow = "hidden";
      this.$nextTick(() => { fade(document.querySelector(".drawer"), 0); document.querySelector(".drawer .iconbtn")?.focus(); });
      try { this.ctx = await j(`/api/entries/${encodeURIComponent(e.id)}/context`); } catch (err) { this.ctx = {messages: []}; }
      this.ctxLoading = false;
    },
    closeDrawer() { this.drawer = null; document.body.style.overflow = ""; },

    // The decision's history: what it replaced and what replaced it, oldest first.
    chain(e) {
      if (!e) return [];
      const byId = Object.fromEntries(this.entries.map(x => [x.id, x]));
      const before = [];
      let cur = e;
      for (let guard = 0; guard < 20; guard++) {
        const prev = this.entries.find(x => x.superseded_by === cur.id);
        if (!prev) break;
        before.unshift(prev); cur = prev;
      }
      const after = [];
      cur = e;
      for (let guard = 0; guard < 20 && cur.superseded_by && byId[cur.superseded_by]; guard++) {
        cur = byId[cur.superseded_by]; after.push(cur);
      }
      return [...before, e, ...after];
    },

    citation(e) { return `“${e.source.quote}” (${this.source(e)})`; },

    // ---------------- palette ----------------
    openPalette() {
      this.palette = {open: true, q: "", i: 0};
      this.$nextTick(() => document.querySelector(".palette input")?.focus());
    },
    closePalette() { this.palette.open = false; },
    commands() {
      const go = id => () => document.getElementById(id)?.scrollIntoView({behavior: reduceMotion ? "auto" : "smooth"});
      const base = [
        {g: "Action", icon: "Compass", label: "Take the 60-second tour", fn: () => this.tour()},
        {g: "Action", icon: "Bot", label: "Watch an agent get caught", fn: () => { go("simulate")(); this.simulate(); }},
        ...this.examples.map(ex => ({g: "Check", icon: "ShieldCheck", label: `Check: ${ex.label}`, fn: () => { go("console")(); this.text = ex.text; this.run(); }})),
        {g: "Go to", icon: "BookOpen", label: "Ledger", fn: go("ledger")},
        {g: "Go to", icon: "FlaskConical", label: "Evidence: does it work?", fn: go("evidence")},
        {g: "Go to", icon: "Terminal", label: "Install in Claude Code or Cursor", fn: go("install")},
        {g: "Export", icon: "Download", label: "Download ledger as JSON", fn: () => location.href = "/api/export?format=json"},
        {g: "Export", icon: "Download", label: "Download ledger as Markdown", fn: () => location.href = "/api/export?format=md"},
        {g: "Action", icon: this.dark ? "Sun" : "Moon", label: this.dark ? "Switch to light theme" : "Switch to dark theme", fn: () => this.toggleTheme()},
      ];
      const ents = this.entries.filter(e => e.status !== "rejected").map(e => ({g: e.kind.replace("_", " "), icon: "FileText", label: e.statement, fn: () => this.openDrawer(e)}));
      const q = squash(this.palette.q);
      const all = [...base, ...ents];
      return (q ? all.filter(c => squash(c.label + " " + c.g).includes(q)) : all).slice(0, 40);
    },
    paletteKey(e) {
      const n = this.commands().length;
      if (e.key === "ArrowDown") { e.preventDefault(); this.palette.i = (this.palette.i + 1) % Math.max(n, 1); this.scrollPalette(); }
      else if (e.key === "ArrowUp") { e.preventDefault(); this.palette.i = (this.palette.i - 1 + n) % Math.max(n, 1); this.scrollPalette(); }
      else if (e.key === "Enter") { e.preventDefault(); this.runCommand(this.commands()[this.palette.i]); }
    },
    scrollPalette() { this.$nextTick(() => document.querySelector('.palette li[aria-selected="true"]')?.scrollIntoView({block: "nearest"})); },
    runCommand(c) { if (!c) return; this.closePalette(); setTimeout(c.fn, 30); },

    // ---------------- simulation ----------------
    async simulate() {
      if (this.sim.running) return;
      if (!this.sim.session) {
        try { this.sim.session = await j("/api/demo-session"); }
        catch (e) { this.toast("Couldn’t load the demo session: " + e.message, true); return; }
      }
      this.sim = {...this.sim, running: true, done: false, title: this.sim.session.title, log: [], caught: 0, checked: 0};
      for (const m of this.sim.session.messages) {
        const item = {role: m.role, full: m.text, shown: "", typing: true, check: null};
        this.sim.log.push(item);
        const row = this.sim.log[this.sim.log.length - 1];
        await this.type(row, m.text, m.role === "user" ? 14 : 9);
        row.typing = false;
        if (m.role === "assistant" && m.text.length > 40) {
          row.check = {state: "pending"};
          this.scrollTerm();
          this.sim.checked++;
          try {
            const v = await postJSON("/api/check", {text: m.text});
            row.check = {state: v.verdict === "contradicts" ? "bad" : "ok", v};
            if (v.verdict === "contradicts") this.sim.caught++;
          } catch (e) {
            row.check = {state: "error", msg: /Model call failed/.test(e.message) ? "The hosted model is busy right now; try again in a minute." : e.message};
          }
          this.$nextTick(() => { fade(this.$refs.term?.querySelector(".interject:last-of-type")); this.scrollTerm(); });
          await sleep(500);
        }
      }
      this.sim.running = false; this.sim.done = true;
      j("/api/history?limit=25").then(h => this.history = h).catch(() => {});
    },
    async type(row, text, speed) {
      if (reduceMotion) { row.shown = text; return; }
      const step = Math.max(1, Math.round(text.length / 90));
      for (let i = 0; i < text.length; i += step) { row.shown = text.slice(0, i + step); this.scrollTerm(); await sleep(speed); }
      row.shown = text;
    },
    scrollTerm() { const t = this.$refs.term; if (t) t.scrollTop = t.scrollHeight; },

    // ---------------- tour ----------------
    tour() {
      if (!window.driver?.js?.driver) { this.toast("The tour couldn’t load. Try reloading the page.", true); return; }
      try { localStorage.setItem("sthira-toured", "1"); } catch (e) {}
      const self = this;
      const d = window.driver.js.driver({
        showProgress: true, popoverClass: "sthira-tour", overlayOpacity: .55, stagePadding: 6, stageRadius: 14,
        nextBtnText: "Next", prevBtnText: "Back", doneBtnText: "Done", progressText: "{{current}} of {{total}}",
        steps: [
          {element: "#ledger", popover: {title: "What you decided", side: "top", description: "Sthira read the team’s ChatGPT chats and a meeting, and kept each decision with its reason, the exact words used, and where it was said."}},
          {element: "#console", popover: {title: "An agent is about to act", side: "left",
            description: "Say an AI coding agent wants to migrate the user store to MongoDB. Press Next and Sthira checks it against what was settled.",
            onNextClick: async () => {
              if (self.checking) return;
              const btn = document.querySelector(".driver-popover-next-btn");
              if (btn) { btn.textContent = "Checking…"; btn.disabled = true; }
              self.filter = "settled"; self.text = self.examples[0].text;
              document.getElementById("console").scrollIntoView({block: "center"});
              await self.run();
              await sleep(250);
              d.moveNext();
            }}},
          {element: "#console", popover: {title: "It speaks up, with receipts", side: "left", description: "A cited warning: the March decision, the verbatim quote and why this goes against it. You can keep the decision, or change your mind and it’s superseded, never deleted."}},
          {element: "#learning", popover: {title: "It learns from you", side: "left", description: "Rejected extractions and corrected verdicts become rules for the next run. On qwen3:4b, precision on unseen chats rose from 60% to 71%."}},
          {element: "#simulate", popover: {title: "Or watch it live", side: "top", description: "Replay a real Claude Code session and see Sthira interrupt the moment the agent drifts from a decision."}},
          {element: "#install", popover: {title: "Works where you work", side: "top", description: "MCP for Claude Code, a prompt hook, AGENTS.md and Cursor rules. Runs locally on an open-weight model."}},
        ],
      });
      d.drive();
    },

    // ---------------- charts ----------------
    drawCharts() {
      if (!window.Chart || !this.entries.length) return;
      const live = this.entries.filter(e => e.status !== "rejected");
      const ink = cssVar("--ink-2"), muted = cssVar("--muted"), line = cssVar("--line");
      const palette = [cssVar("--accent"), cssVar("--ok"), cssVar("--warn"), cssVar("--ink-2"), cssVar("--line-2")];
      Chart.defaults.font.family = "Geist, system-ui, sans-serif";
      Chart.defaults.color = muted;

      const bySrc = {};
      live.forEach(e => { const k = this.srcLabel(e.source.type); bySrc[k] = (bySrc[k] || 0) + 1; });
      const byMonth = {};
      live.forEach(e => { if (e.decided_at) { const k = e.decided_at.slice(0, 7); byMonth[k] = (byMonth[k] || 0) + 1; } });
      const months = Object.keys(byMonth).sort();

      CHARTS.src?.destroy(); CHARTS.time?.destroy();
      const src = document.getElementById("chart-src"), time = document.getElementById("chart-time");
      if (src) CHARTS.src = new Chart(src, {
        type: "doughnut",
        data: {labels: Object.keys(bySrc), datasets: [{data: Object.values(bySrc), backgroundColor: palette, borderColor: cssVar("--surface"), borderWidth: 2}]},
        options: {maintainAspectRatio: false, cutout: "62%", animation: reduceMotion ? false : {duration: 700},
          plugins: {legend: {position: "right", labels: {boxWidth: 10, boxHeight: 10, color: ink, font: {size: 12}}}}},
      });
      if (time) CHARTS.time = new Chart(time, {
        type: "bar",
        data: {labels: months.map(m => new Date(m + "-01T00:00:00Z").toLocaleDateString("en-GB", {month: "short", year: "2-digit"})),
               datasets: [{data: months.map(m => byMonth[m]), backgroundColor: cssVar("--accent"), borderRadius: 5, maxBarThickness: 26}]},
        options: {maintainAspectRatio: false, animation: reduceMotion ? false : {duration: 700}, plugins: {legend: {display: false}},
          scales: {x: {grid: {display: false}, ticks: {color: muted}}, y: {beginAtZero: true, ticks: {precision: 0, color: muted}, grid: {color: line}}}},
      });
    },

    // ---------------- import / copy / theme / toasts ----------------
    async upload(file) {
      if (!file || this.uploading) return;
      this.uploading = true; this.uploadErr = false; this.uploadMsg = "";
      const fd = new FormData(); fd.append("file", file);
      try {
        const out = await j("/api/import", {method: "POST", body: fd});
        this.uploadMsg = `${out.messages} messages in · ${out.entries.length} new entries to review.`;
        this.filter = "proposed";
        this.load();
      } catch (e) {
        this.uploadErr = true;
        this.uploadMsg = /Model call failed/.test(e.message)
          ? "The hosted model is busy or offline, so extraction can’t run right now. Run Sthira locally with Ollama to import your history."
          : e.message;
      }
      this.uploading = false;
    },

    async copy(text, key) {
      try { await navigator.clipboard.writeText(text); this.copied = key; setTimeout(() => { if (this.copied === key) this.copied = ""; }, 1600); }
      catch (e) { this.toast("Couldn’t copy. Select the text instead.", true); }
    },

    toggleTheme() {
      this.dark = !this.dark;
      const t = this.dark ? "dark" : "light";
      document.documentElement.dataset.theme = t;
      try { localStorage.setItem("sthira-theme", t); } catch (e) {}
      this.$nextTick(() => this.drawCharts());
    },

    toast(msg, err = false, action = null) {
      const id = Math.random();
      this.toasts.push({id, msg, err, action});
      setTimeout(() => this.toasts = this.toasts.filter(t => t.id !== id), action ? 7000 : 3200);
    },
    dismiss(id) { this.toasts = this.toasts.filter(t => t.id !== id); },

    // ---------------- formatting ----------------
    pct: x => x == null ? "–" : Math.round(x * 100) + "%",
    fmtDate: s => s ? new Date(s).toLocaleDateString("en-GB", {day: "numeric", month: "short", year: "numeric"}) : "undated",
    ago(s) {
      if (!s) return "";
      const d = (Date.now() - new Date(s).getTime()) / 1000;
      if (d < 60) return "just now";
      if (d < 3600) return Math.round(d / 60) + " min ago";
      if (d < 86400) return Math.round(d / 3600) + " h ago";
      return this.fmtDate(s);
    },
    srcLabel: t => ({chatgpt: "ChatGPT", claude_ai: "Claude", claude_code: "Claude Code", transcript: "Meeting", gemini: "Gemini", manual: "Sthira"})[t] || t,
    source(e) { return [this.srcLabel(e.source.type), e.source.title, (e.decided_at || "").slice(0, 10)].filter(Boolean).join(" · "); },
    feedIcon: t => ({extracted: "FilePlus", settle: "Check", reject: "X", override: "GraduationCap"})[t] || "Dot",
    feedText(ev) {
      if (ev.type === "extracted") return `Extracted a ${ev.kind.replace("_", " ")}: ${ev.text}`;
      if (ev.type === "settle") return `Settled: ${ev.text}`;
      if (ev.type === "reject") return `Rejected: ${ev.text}` + (ev.note ? ` (why: ${ev.note})` : "");
      if (ev.type === "override") return `Corrected a verdict: ${ev.note}`;
      return ev.text;
    },
  };
}
