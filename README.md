# Sthira

> स्थिर (*sthira*): steady, firm, unshakable.

**Your AI forgets what you decided. Sthira doesn't.**

Sthira reads your AI history (ChatGPT exports, Claude Code sessions, meeting transcripts), pulls out the decisions you made, along with their reasons and their sources, and keeps them in a local ledger. When an AI agent proposes something that contradicts a past decision, Sthira warns you and cites where you decided it. It learns from your corrections. Everything runs locally on an open-weight model (Qwen3 via Ollama).

Work in progress for Hacktoberfest Hack Day Bengaluru 2026 (Track 2, O2: Adaptive AI with Memory and Self-Correction). See [`docs/PLAN.md`](docs/PLAN.md).

## Quickstart

```bash
# needs uv and Ollama with a Qwen3 model:  ollama pull qwen3:4b
uv sync
uv run sthira ingest path/to/chatgpt-export.zip          # or conversations.json, ~/.claude/projects/<proj>/, meeting.md
uv run sthira extract                                    # local open-weight model reads it, proposes entries
uv run sthira review                                     # settle or reject; rejections teach Sthira
uv run sthira check "Let's switch the user store to MongoDB"
uv run sthira sync AGENTS.md                             # every coding agent now sees what's settled
uv run sthira stats                                      # precision before vs after your corrections
```

### Use it from Claude Code (MCP)

```bash
claude mcp add sthira -- uv run --directory /path/to/Sthira --extra mcp sthira mcp
```

Tools: `get_settled`, `open_questions`, `check`, `propose`.

## License
MIT
