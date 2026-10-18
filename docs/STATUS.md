# Live status board

Update this file whenever you finish something, get blocked, or hand off (for example near a usage limit). Newest first.

## Board

**⏰ First-round evaluation runs 14:00–15:30 (be demo-ready by 14:00).** Criteria: one working feature · relevance to the theme · clear problem and solution. Submit: repo URL + Track 2 / O2 (portal TBA).

**Live demo:** https://sthira-mocha.vercel.app · **PRs:** #1 core → #2 demo/eval → #3 web (stacked; merge in order)

| Workstream | Owner | Status | Next step |
|---|---|---|---|
| Core + demo/eval (#1, #2) | Claude | done, CI green | merge at ~12:00 |
| Cursor rules #10 · model-down errors #11 · .vtt/.srt #12 · Gemini #13 · learned rules #14 · review fixes #15 | Claude | done, stacked on #2 | merge in order after #2 (integration dry-run: all merge cleanly, 17+ tests pass) |
| Web demo (#3) | Claude + Vidit (#9 merged) | **live**: learned-rules panel, labelled offline fallbacks, scoped import | merge last |
| Dogfood: Sthira on our own build session | Claude | running (qwen3:4b) | package as a demo moment |
| **Hosted model** | **Ojas** | blocked | Vercel card **or** Groq key in project env |
| **ShipWright app** | **Ojas** | not installed | install now if we want leaderboard credit before the merges |
| **Collaborators: Vidit, Danica** | **Ojas** | todo | fork PRs miss ShipWright's full review |
| Demo rehearsal / backup video / submission / X post | Danica | todo | `docs/DEMO_SCRIPT.md`, `docs/SUBMISSION.md` |

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
- 11:10: Added #10–#15 (Cursor rules, model-down errors, subtitles, Gemini, learned rules, Vidit's review fixes). Learned-rules panel live. Integration dry-run clean. Dogfood found real decisions from our own session.
- 10:55: Merged Vidit's #9 (labelled keyword fallback for typed checks) and redeployed. Handbook update: first-round eval 14:00–15:30, criteria published, live URL no longer required (we have one anyway). Primer PDF in docs/primer/.
- 10:05: Critic pass added (checks 6/6). qwen3:8b comparison done. Live site deployed with seeded ledger and labelled fallback. Waiting on two Ojas-only actions (hosted model, ShipWright).
- 09:27: `sthira demo` proves learning: precision 0.40 → 0.57 (run 1), and both agent contradictions in today's Claude Code session are caught. Web demo works locally. PR #1 is open (no ShipWright review yet, so the app may need installing by Ojas).
- 09:15: Core engine works end to end on qwen3:4b: ingest, extract (~50s for 2 convs), settle/reject, cited contradiction check (~15s), sync, MCP. 6 tests pass. `sthira.api` matches CONTRACTS.md, so Vidit can import it directly in `web/`.
- 08:21: Repo cloned and empty. Plan written (`docs/PLAN.md`). Local Ollama has qwen3:4b, qwen3:8b and nomic-embed-text.
