# Live status board

Update this file whenever you finish something, get blocked, or hand off (for example near a usage limit). Newest first.

## Board

**⏰ First-round evaluation runs 14:00–15:30 (be demo-ready by 14:00).** Criteria: one working feature · relevance to the theme · clear problem and solution. Submit: repo URL + Track 2 / O2 (portal TBA).

**Live demo:** https://sthira-mocha.vercel.app · **PRs:** #1 core → #2 demo/eval → #3 web (stacked; merge in order)

| Workstream | Owner | Status | Next step |
|---|---|---|---|
| Core engine + MCP + hook + scan + replace | Claude | done (PR #1, #2) | — |
| Self-correcting check (critic pass) + eval | Claude | done (PR #2): extraction 0.60→0.71 precision, checks 6/6 on qwen3:4b | — |
| Web demo + Vercel deploy | Claude | **live** (PR #3) | hosted model blocked: see blocker below |
| **BLOCKER: hosted model** | **Ojas** | todo | add a card to the Vercel team (unlocks AI Gateway free credits) **or** set `STHIRA_OPENAI_API_KEY` + `STHIRA_OPENAI_BASE_URL` + `STHIRA_MODEL` (e.g. Groq `qwen/qwen3-32b`) in Vercel project *sthira* env. Until then, example checks use labelled recorded verdicts |
| **ShipWright app on repo** | **Ojas** (admin) | todo | install https://github.com/apps/shipwright-agent, then comment `/shipwright rerun` on PRs #1–#3; merge by ~12:00 regardless |
| Demo script / pitch / backup video / submission | Danica | todo | `docs/DEMO_SCRIPT.md` is ready; rehearse, record a backup video of the live site + `sthira demo` |
| Collaborator access for Vidit + Danica | **Ojas** | todo | Settings → Collaborators (fork PRs only get basic ShipWright checks) |
| Polish / extra parsers / review | Vidit | #9 merged ✓; #8 overlaps #3 (suggest closing) | pick anything: e.g. Cursor or Gemini parser in `sthira/ingest/`, UI polish in `web/static/index.html` (branch off `feat/web-demo`) |

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
- 10:55: Merged Vidit's #9 (labelled keyword fallback for typed checks) and redeployed. Handbook update: first-round eval 14:00–15:30, criteria published, live URL no longer required (we have one anyway). Primer PDF in docs/primer/.
- 10:05: Critic pass added (checks 6/6). qwen3:8b comparison done. Live site deployed with seeded ledger and labelled fallback. Waiting on two Ojas-only actions (hosted model, ShipWright).
- 09:27: `sthira demo` proves learning: precision 0.40 → 0.57 (run 1), and both agent contradictions in today's Claude Code session are caught. Web demo works locally. PR #1 is open (no ShipWright review yet, so the app may need installing by Ojas).
- 09:15: Core engine works end to end on qwen3:4b: ingest, extract (~50s for 2 convs), settle/reject, cited contradiction check (~15s), sync, MCP. 6 tests pass. `sthira.api` matches CONTRACTS.md, so Vidit can import it directly in `web/`.
- 08:21: Repo cloned and empty. Plan written (`docs/PLAN.md`). Local Ollama has qwen3:4b, qwen3:8b and nomic-embed-text.
