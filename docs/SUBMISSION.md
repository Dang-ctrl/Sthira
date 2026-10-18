# Submission (copy-paste ready)

| Field | Value |
|---|---|
| Project name | **Sthira** |
| Team | Ojas Mutreja, Vidit, Danica |
| Track | **Track 2: Best Open-Source AI Project** |
| Primary problem statement | **O2: Adaptive AI with Memory and Self-Correction** |
| Public GitHub repository | https://github.com/HelloOjasMutreja/Sthira |
| Live deployment URL (bonus; no longer required) | https://sthira-mocha.vercel.app |
| License | MIT |
| Open-weight AI used | Qwen3 (4B / 8B) locally via Ollama; Qwen3-32B for the hosted demo |

## Short description (about 3 to 5 lines)
Sthira remembers what you decided while working with AI. It reads your ChatGPT and Claude exports, Claude Code sessions and meeting transcripts with a local open-weight model (Qwen3), extracts decisions with their reasons and a verbatim source quote, and keeps them in a ledger where nothing is deleted, only superseded. When an AI agent proposes something that contradicts a past decision, Sthira warns you and cites where you decided it, over the CLI, MCP, a Claude Code hook or the web app. It adapts: your corrections become rules for future extractions and checks, and a self-correction pass double-checks every warning.

## How it meets O2 (memory and self-correction)
- **Retains context:** a persistent, cited ledger across all your AI tools, served to agents via MCP and `AGENTS.md`.
- **Learns from feedback:** rejected extractions and corrected verdicts become rules in future prompts. Measured precision on unseen conversations rose from 0.60 to 0.71 on qwen3:4b (`sthira demo`, `eval/README.md`).
- **Identifies and corrects its own mistakes:**
  - Hallucinated quotes are dropped by verifying them against the source.
  - A critic pass re-examines every claimed contradiction. It took checks from 4/6 to 6/6 (`scripts/eval_checks.py`).
- **Adapts over time:** decisions can be superseded, with history kept, so the ledger tracks how your thinking changed.

## Social Media Challenge (X only)
Post about the build with a photo, follow and tag KrowdKraft and the listed partners, and use **#BuildWithKrowdKraft**. Draft:

> We built Sthira at #HacktoberfestHackDay Bengaluru: your AI forgets what you decided, Sthira doesn't. It reads your AI chats and coding-agent sessions with an open-weight model on your laptop, keeps a cited ledger of your decisions, and warns when an agent goes against one. Open source: github.com/HelloOjasMutreja/Sthira #BuildWithKrowdKraft
