# Sthira: shared context for every human and AI agent on this repo

Read this first, then `docs/STATUS.md` (what's happening now), `docs/PLAN.md` (design and timeline) and `docs/CONTRACTS.md` (interfaces).

## What we're building
Sthira (स्थिर, "steady, firm") remembers what you decided while working with AI, and warns when new work contradicts it. It ingests ChatGPT exports, Claude Code sessions and meeting transcripts, extracts decisions with a **local open-weight model** (Qwen3 via Ollama), keeps a ledger where nothing is deleted (old entries are superseded) and every entry cites its source, checks new proposals for contradictions, **learns from your corrections**, and serves the ledger to AI tools over MCP and generated `AGENTS.md` blocks.

Hackathon: Hacktoberfest Hack Day Bengaluru, 18 Oct 2026. Track 2 (Best Open-Source AI Project), problem statement **O2, Adaptive AI with Memory and Self-Correction**. **Submissions close at 15:30 IST**: public repo plus a live deployment URL.

## Team and ownership
- **Ojas** (+ Claude): core engine in `sthira/` (except `mcp_server.py` unless handed over). Orchestrates and merges.
- **Vidit** (+ Claude): `web/` (FastAPI API + UI) and deployment; `sthira/mcp_server.py` if handed over.
- **Danica**: `demo/`, `eval/`, README polish, pitch, demo video, submission.
- Never edit a file someone else owns without asking. Interfaces live in `docs/CONTRACTS.md`.

## Rules
- Python ≥ 3.11, managed with `uv`. Run with `uv run sthira …`. Tests: `uv run pytest -q`.
- Local-first: no telemetry, and no network calls except to the configured model provider.
- Extract only from raw source messages, and keep the verbatim quote plus locator. The extractor may return nothing.
- Never delete ledger entries; supersede them.
- Never commit secrets (`.env` is gitignored).
- Git: branch `feat/<area>-<thing>`, then a **human** opens the PR to `main`, ShipWright reviews, we fix and then merge. Keep PRs under 5,000 changed lines, and keep them real (no artificial PRs).
- Before you stop or hand off, update `docs/STATUS.md`.
