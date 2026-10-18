# Contributing to Sthira

Thanks for helping. Sthira should stay **local-first, honest about what it knows, and easy to extend**.

## Setup
```bash
git clone https://github.com/HelloOjasMutreja/Sthira && cd Sthira
uv sync --extra mcp --extra web
uv run pytest -q
ollama pull qwen3:4b          # only needed for extraction and checks
uv run sthira demo            # end-to-end scenario
```

## Good first contributions

### 1. A new source parser (great first PR)
Every source is one small file in [`sthira/ingest/`](sthira/ingest/) that turns an export into `Message` objects (`conv_id`, `conv_title`, `msg_id`, `role`, `ts`, `text`). Wire it into `parse_bytes()` in `sthira/ingest/__init__.py` and add a test with a tiny fixture.

Wanted sources:
- Gemini (Google Takeout), Perplexity, Grok, DeepSeek, Le Chat exports
- Cursor chats (SQLite `state.vscdb`), Codex CLI, Gemini CLI, Aider, OpenCode, Cline sessions
- Slack / Discord channel exports (decisions made in group chats)
- Obsidian / Markdown notes
- Meeting tools: Granola, Otter, Meetily, Whisper `.vtt`/`.srt`

### 2. More eval scenarios
Add a scenario to `demo/` with gold labels in `eval/`. Real anonymised exports are the most valuable contribution of all.

### 3. Output targets
`sthira sync` writes `AGENTS.md` / `CLAUDE.md`. Cursor rules (`.cursor/rules/*.mdc`), Copilot instructions and MADR decision records would all be welcome.

## Principles (please keep them)
- **Never delete** ledger entries. Supersede them.
- **Keep provenance:** every entry stores a verbatim quote plus its locator. Extract only from raw source messages, never from recalled memory.
- **The extractor may return nothing.** Precision matters more than volume.
- **No telemetry, and no network calls** except to the model provider the user configured.
- **Don't overclaim.** If you change prompts or models, rerun `sthira demo` and `scripts/eval_checks.py` and report the numbers in your PR.

## Pull requests
Keep them focused, add a test, and run `uv run pytest -q`. CI runs the tests on Python 3.11 and 3.13.
