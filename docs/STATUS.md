# Live status board

Update this file whenever you finish something, get blocked, or hand off (for example near a usage limit). Newest first.

## Board

| Workstream | Owner | Status | Next step |
|---|---|---|---|
| P0 skeleton + shared docs | Ojas + Claude | in progress | `uv run sthira --help` |
| Core engine (store/ingest/extract/check) | Ojas + Claude | not started | after P0 |
| Web demo (`web/`) + deploy | Vidit | scaffold done on `feat/web-scaffold` (API + UI on fake backend, 7 tests) | swap to real `sthira.api` when it lands; deploy |
| Demo data (`demo/`) + gold labels | Danica | not started | see "Demo data brief" below |
| ShipWright app installed on repo | Ojas (admin) | todo | https://github.com/apps/shipwright-agent |
| Hosted open-weight API key for live demo | Ojas/Vidit | todo | pick provider, put key in deploy env (never commit it) |

## Demo data brief (Danica)

Create these in `demo/` (fictional project "Acme Notes", a note-taking app):

1. `demo/chatgpt/conversations.json`: 3 to 4 short conversations in ChatGPT export format (Claude can give you the schema). Plant these:
   - **Decision (4 Mar 2026):** use Postgres, not MongoDB, because we need joins across users and orgs.
   - **Decision:** auth with magic links, no passwords.
   - **Open question:** pricing, monthly vs annual (never resolved).
   - Plenty of normal chatter that is **not** a decision.
2. `demo/meetings/2026-05-12-standup.md`: a short transcript with one decision (ship mobile after web) and one commitment ("Danica will draft the onboarding copy by Friday").
3. `demo/claude_code/session.jsonl`: a short coding session (Claude can generate it in the right format) where the agent **proposes switching the user store to MongoDB**. This is the contradiction for the demo.
4. `eval/gold.json`: the list of real decisions, questions and commitments you planted, so we can measure precision and recall.

## Log
- web: FastAPI app implements every CONTRACTS.md HTTP route against `web/fake_api.py` (Acme Notes seed); falls back to real `sthira.api` automatically when importable. Gap: no HTTP route for `api.supersede` yet (demo step 2 needs one).
- 08:21: Repo cloned and empty. Plan written (`docs/PLAN.md`). Local Ollama has qwen3:4b, qwen3:8b and nomic-embed-text.
