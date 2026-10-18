# Sthira: design and build plan (Hack Day, 18 Oct 2026)

> स्थिर (Sanskrit *sthira*): steady, firm, unshakable.
> **Sthira remembers what you decided while working with AI, and speaks up when something is about to undo it.**

## 1. Hackathon frame (from the official handbook)

- **Track:** Track 2, Best Open-Source AI Project.
- **Primary problem statement:** **O2, Adaptive AI with Memory and Self-Correction.** The required outcome is that the solution "retains relevant context, learns from feedback or identifies and corrects mistakes … adapts over time."
  - Secondary capability shown (allowed, but not claimed as primary): O3, Trustworthy and Verifiable AI. Every entry cites its source.
- **Open-weight AI must be meaningful.** Qwen3 (4B or 8B) runs locally via Ollama. For the hosted demo, the same model family runs through an OpenAI-compatible provider.
- **Must submit by 3:30 PM IST:**
  - the public GitHub repo
  - a **working live deployment URL judges can test**
  - the track and problem statement
- **Judging criteria are not published.** Be ready to demo how it works and how it uses open-weight AI.
- **Build window:** 13 to 18 Oct. All work happens inside it.
- **ShipWright leaderboard:**
  - Use feature branch → PR → ShipWright review → fix → merge.
  - **A human must open each PR.**
  - No artificial PRs, and keep each under 5,000 changed lines.

## 2. What Sthira is (MVP scope)

A local-first tool, run as a CLI plus an MCP server plus a web demo, that:

1. **Ingests** your AI history:
   - ChatGPT export (`conversations.json`)
   - Claude Code session logs (`~/.claude/projects/**/*.jsonl`)
   - plain-text or Markdown meeting transcripts
2. **Extracts** decisions and related entries with a local open-weight model. Each entry carries a status and a citation back to its source message.
3. **Keeps a ledger.** Nothing is deleted. A changed decision is marked `superseded` and linked to its replacement.
4. **Checks** new work, such as a plan, a prompt or a diff description, against settled decisions. A contradiction produces a **cited warning**: "This contradicts your 4 Mar decision (source: ChatGPT chat 'DB choice')."
5. **Learns from feedback (the core of O2).** When you reject a bad extraction or override a wrong verdict, the correction is stored and fed back as examples into future prompts. Precision visibly improves over the session, and we show a before/after counter.
6. **Serves** context to every AI tool:
   - an MCP server with `get_settled`, `check`, `propose`
   - a `sthira sync` command that writes an always-fresh block into `AGENTS.md` / `CLAUDE.md`

### Not in the MVP (stretch, or v1+)
Voice notes, Obsidian sync, git hooks, assumption watchers, team sharing, browser extension, profile building, Gemini import.

### Entry types and life cycle
`kind`: `decision | open_question | preference | commitment | lesson | assumption`
`status`: `proposed` (needs review) → `settled` | `rejected`; `settled` → `superseded` (by another entry)
`trust`: entries extracted from untrusted content stay `quarantined` until a human confirms them. This is the defence against memory poisoning.

## 3. Architecture

```
sources (ChatGPT export, Claude Code JSONL, transcripts)
   │  sthira/ingest/*.py  → normalized Message rows
   ▼
SQLite (one file, FTS5)  ── sthira/store.py
   │
   ├─ sthira/extract.py   chunk (~5k tokens) → LLM JSON-schema → candidate entries
   ├─ sthira/check.py     retrieve related settled entries (FTS + optional embeddings) → LLM judge → verdict + citation
   ├─ sthira/feedback.py  store corrections → few-shot examples for future prompts
   └─ sthira/llm.py       provider abstraction: Ollama (local) | OpenAI-compatible (hosted open-weight)
   ▼
surfaces:  sthira/cli.py (Typer) · sthira/mcp_server.py (MCP Python SDK) · sthira/sync.py (AGENTS.md/CLAUDE.md)
           web/ (FastAPI API + single-page UI) → deployed for judges
```

**Stack:** Python ≥ 3.11 (`uv`), Typer, SQLite FTS5, `httpx`, Pydantic, `mcp` SDK, FastAPI. Ollama with `qwen3:4b` (fast) or `qwen3:8b` (better). Output is constrained by a JSON schema via Ollama's `format`.

**Design rules learned from competitors' issue trackers** (see `docs/research/`):
- Never re-extract from recalled memory; extract only from raw source messages.
- Always keep the verbatim source quote and its location.
- The extractor must be allowed to return **nothing**. Most chat turns contain no decision.
- Never delete; supersede.
- No telemetry and no cloud calls unless the user configures them.
- Don't overclaim. Publish a small eval honestly.

## 4. Timeline (today, IST)

| Time | Phase | Done when |
|---|---|---|
| 08:20–09:15 | **P0 Setup:** repo skeleton, shared context, ShipWright installed, demo data drafted | `uv run sthira --help` works; PLAN/STATUS committed |
| 08:30–09:30 | *(venue check-in and inauguration: build in gaps)* | |
| 09:30–11:00 | **P1 Core engine:** store, ingest (3 parsers), extract, check | `sthira ingest` + `sthira extract` + `sthira check "<text>"` work end to end on demo data with a local model |
| 11:00–12:30 | **P2 Surfaces:** feedback loop, MCP server, `sync`; web API + UI skeleton | Claude Code can call `sthira` over MCP; UI lists the ledger and runs a check |
| 12:30–13:30 | Lunch (light work only) | |
| 13:30–14:45 | **P3 Demo-ready:** deploy, seeded demo, README, mini eval | Live URL works from a phone |
| 14:45–15:20 | **P4 Freeze:** bug fixes only, backup demo video, rehearse, **submit by 15:20** | Submitted, with a 10-minute buffer |
| 15:45– | Judging | |

**Rule:** at 11:00 and 13:30 we cut scope instead of slipping time.

## 5. Who does what

| Person | Tools | Workstream (owns these paths) |
|---|---|---|
| **Ojas** + Claude (orchestrator session) | Claude Pro | Core engine: `sthira/store.py`, `extract.py`, `check.py`, `feedback.py`, `llm.py`, `cli.py`. Integration, merges, final call on scope. |
| **Vidit** + his Claude session | Claude Pro | Web demo: `web/` (FastAPI app + UI) and deployment. Codes against the interface in `docs/CONTRACTS.md`, so the work can run in parallel. Later: MCP server (`sthira/mcp_server.py`) if time allows. |
| **Danica** | Free tools, manual work | Demo data (`demo/`): a realistic ChatGPT export, a Claude Code session and a meeting transcript, with **planted decisions and one deliberate later contradiction**. Gold labels for the mini eval (`eval/gold.json`). README polish, pitch, 2-minute demo script, backup video, submission form, Social Media Challenge. Human reviewer on ShipWright PRs. |

### Usage-limit protocol (two Pro accounts)
- Keep the critical path (core engine) with Ojas, and keep Vidit's work separable.
- Before handing over, or when a limit nears, update `docs/STATUS.md` with what's done, what's next and any gotchas. The other session reads `AGENTS.md` and `STATUS.md` and carries on.
- Heavy, broad tasks (large refactors, full test runs) go to whichever account has the most headroom. Small fixes can be made by hand.
- Never have two people editing the same file. Ownership follows the table above.

### Git and ShipWright workflow
1. Branch per feature: `feat/<area>-<thing>` (e.g. `feat/core-extract`).
2. Commit small and often. Open a **non-draft PR to `main` by hand** (a human must open it).
3. Read ShipWright's review. Fix valid points, push, and reply on the inapplicable ones.
4. Merge, then pull before starting the next branch.

## 6. Expectations for each phase

- **P0:** nothing fancy. A skeleton that runs, shared docs, and data that tells a story.
- **P1:** correctness over polish. The demo story must work on the demo data with `qwen3:4b`.
- **P2:** the "wow" moment, where an AI agent gets warned about a past decision live. The feedback loop is visible.
- **P3:** a judge can open the URL and in 60 seconds see: the ledger with citations, a check that catches a contradiction, and a correction that changes future behaviour.
- **P4:** no new features. Rehearse until the demo runs in 2 minutes.

## 7. Demo story (2 minutes)

1. "Months ago, in a ChatGPT chat, I decided to use **Postgres, not MongoDB**, because we need joins." The ledger shows it with its citation.
2. Today, a Claude Code session proposes "let's switch the user store to MongoDB." **Sthira warns** and cites the March chat. I choose *keep* or *supersede*.
3. Sthira wrongly extracts a chatty line as a "decision." I reject it, and it **learns**: the next extraction skips that pattern. The counter shows the change.
4. `sthira sync`: every agent's `AGENTS.md` now carries the settled decisions.

## 8. Open items
- Hosted open-weight provider for the live demo (needs one API key; see STATUS).
- Who or what "Iris" is in the team setup (to confirm with Ojas).
