# Interfaces (code against these so work can run in parallel)

If you need to change anything here, tell the team and update this file in the same PR.

## Entry (the ledger row)

```json
{
  "id": "e_01H...",
  "kind": "decision | open_question | preference | commitment | lesson | assumption",
  "title": "Use Postgres for the user store",
  "statement": "We will use Postgres, not MongoDB, for the user store.",
  "rationale": "We need relational joins across users and orgs.",
  "alternatives_rejected": ["MongoDB"],
  "project": "acme-app",
  "status": "proposed | settled | rejected | superseded",
  "trust": "confirmed | quarantined",
  "superseded_by": null,
  "decided_at": "2026-03-04T10:12:00Z",
  "recorded_at": "2026-10-18T09:40:00Z",
  "source": {
    "id": "s_...",
    "type": "chatgpt | claude_code | transcript",
    "title": "DB choice",
    "locator": "conversation <id> / message <id>",
    "quote": "ok let's go with postgres, we need joins"
  },
  "confidence": 0.82
}
```

## Check verdict

```json
{
  "input": "Let's switch the user store to MongoDB",
  "verdict": "contradicts | consistent | unrelated | supersedes",
  "conflicts": [ { "entry": "<Entry>", "explanation": "…" } ],
  "model": "qwen3:4b"
}
```

## Python API (`sthira.api`, stable for the web and MCP layers)

```python
from sthira import api
api.ingest(path: str, kind: str | None = None) -> dict          # {"messages": n, "sources": n}
api.extract(limit: int | None = None) -> list[Entry]            # new proposed entries
api.list_entries(status: str | None = None, kind: str | None = None, q: str | None = None) -> list[Entry]
api.review(entry_id: str, action: "settle" | "reject", note: str | None = None) -> Entry
api.supersede(old_id: str, new_id: str) -> Entry
api.check(text: str) -> Verdict
api.feedback_stats() -> dict                                    # {"corrections": n, "precision_before": x, "precision_after": y}
api.sync(path: str = "AGENTS.md") -> str                        # returns the written block
```

## HTTP API (`web/`, FastAPI, mirrors the Python API)

| Method | Path | Body / query | Returns |
|---|---|---|---|
| GET | `/api/entries` | `status, kind, q` | `Entry[]` |
| POST | `/api/entries/{id}/review` | `{action, note}` | `Entry` |
| POST | `/api/check` | `{text}` | `Verdict` |
| POST | `/api/ingest` | multipart file + `kind` | `{messages, sources}` |
| POST | `/api/extract` | `{limit}` | `Entry[]` |
| GET | `/api/stats` | none | feedback stats + counts |
| GET | `/api/entries/{id}/context` | `around` (0-5) | `{title, messages: [{role, ts, text, match}]}`, the source conversation around the quote |
| GET | `/api/history` | `limit` | newest-first events: extracted, settle, reject, override |
| GET | `/api/export` | `format=json\|md` | the whole ledger as a download |
| GET | `/api/eval` | none | headline numbers from `eval/README.md` |
| GET | `/api/demo-session` | none | `{title, messages}` from `demo/claude_code/session.jsonl` |

`POST /api/check` may add `"cached": true` (same text, unchanged ledger and feedback, within 10 minutes) or `"fallback": "keyword" | "recorded"` (hosted model unreachable). The Verdict fields are otherwise unchanged.

## Environment

| Var | Default | Meaning |
|---|---|---|
| `STHIRA_DB` | `~/.sthira/sthira.db` | SQLite file |
| `STHIRA_PROVIDER` | `ollama` | `ollama` or `openai` (any OpenAI-compatible endpoint serving an open-weight model) |
| `STHIRA_MODEL` | `qwen3:4b` | model name for the provider |
| `OLLAMA_HOST` | `http://localhost:11434` | |
| `STHIRA_OPENAI_BASE_URL` / `STHIRA_OPENAI_API_KEY` | none | hosted open-weight endpoint for the live demo |
