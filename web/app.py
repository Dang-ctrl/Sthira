"""Sthira web demo: FastAPI over `sthira.api`, plus a single-page UI."""

from __future__ import annotations

import copy
import json
import os
import re
import threading
import time
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

# On serverless hosts only /tmp is writable; each cold start gets a freshly seeded demo ledger.
if "STHIRA_DB" not in os.environ:
    os.environ["STHIRA_DB"] = "/tmp/sthira.db" if os.environ.get("VERCEL") else str(ROOT / ".sthira" / "web.db")
# Values pasted into a dashboard often end with a newline, which makes the Authorization header invalid.
for _name in ("STHIRA_PROVIDER", "STHIRA_MODEL", "STHIRA_FALLBACK_MODEL", "STHIRA_OPENAI_BASE_URL", "STHIRA_OPENAI_API_KEY"):
    if os.environ.get(_name):
        os.environ[_name] = os.environ[_name].strip()
if os.environ.get("VERCEL") and "STHIRA_PROVIDER" not in os.environ:
    os.environ["STHIRA_PROVIDER"] = "openai"
    os.environ.setdefault("STHIRA_MODEL", "alibaba/qwen-3-32b")

from sthira import api, config, llm, store  # noqa: E402

from . import fallback, seed  # noqa: E402

app = FastAPI(title="Sthira", version="0.1.0")

# Provider errors can echo request headers (e.g. httpx's "Illegal header value b'Bearer …'"), and these
# messages are returned to the browser. Never let a key out.
_SECRET = re.compile(r"(Bearer\s+)[^\s'\"]+|\b(?:gsk|sk|sk-proj|vck)[_-][A-Za-z0-9_-]{8,}", re.I)


def _safe(e: Exception) -> str:
    return _SECRET.sub(lambda m: (m.group(1) or "") + "[redacted]", str(e))
_lock = threading.Lock()


@app.middleware("http")
async def vercel_oidc(request, call_next):
    # Vercel passes a short-lived OIDC token per request; AI Gateway accepts it as the API key.
    token = request.headers.get("x-vercel-oidc-token")
    if token:
        os.environ["VERCEL_OIDC_TOKEN"] = token
    return await call_next(request)


def con():
    c = store.connect()
    if c.execute("SELECT COUNT(*) FROM entries").fetchone()[0] == 0 and (ROOT / "demo" / "seed.json").exists():
        with _lock:
            if c.execute("SELECT COUNT(*) FROM entries").fetchone()[0] == 0:
                seed.load(c, ROOT / "demo" / "seed.json")
    return c


class ReviewBody(BaseModel):
    action: str
    note: str | None = None


class CheckBody(BaseModel):
    text: str


class CorrectBody(BaseModel):
    text: str
    note: str


class ExtractBody(BaseModel):
    limit: int | None = 3


@app.get("/", response_class=HTMLResponse)
def index():
    return (HERE / "static" / "index.html").read_text(encoding="utf-8")


@app.get("/api/meta")
def meta():
    return {"model": config.model(), "provider": config.provider(), "version": "0.1.0"}


@app.get("/api/entries")
def entries(status: str | None = None, kind: str | None = None, q: str | None = None):
    return [e.model_dump() for e in api.list_entries(status, kind, q, con=con())]


@app.post("/api/entries/{entry_id}/review")
def review(entry_id: str, body: ReviewBody):
    try:
        return api.review(entry_id, body.action, body.note, con=con()).model_dump()
    except (KeyError, ValueError) as e:
        raise HTTPException(400, str(e))


class ReplaceBody(BaseModel):
    statement: str
    rationale: str = ""


@app.post("/api/entries/{old_id}/replace")
def replace(old_id: str, body: ReplaceBody):
    try:
        r = api.replace(old_id, body.statement[:1000], body.rationale[:1000], con=con())
    except KeyError:
        raise HTTPException(404, "entry not found")
    return {"old": r["old"].model_dump(), "new": r["new"].model_dump()}


@app.post("/api/entries/{old_id}/supersede/{new_id}")
def supersede(old_id: str, new_id: str):
    try:
        return api.supersede(old_id, new_id, con=con()).model_dump()
    except KeyError as e:
        raise HTTPException(404, f"entry not found: {e}")
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/api/check")
def check(body: CheckBody):
    if not body.text.strip():
        raise HTTPException(400, "text is empty")
    text = body.text[:4000]
    c = con()
    key = (fallback.normalize(text), _ledger_fingerprint(c))
    hit = _verdict_cache.get(key)
    if hit and time.monotonic() - hit[0] < VERDICT_TTL:
        return {**copy.deepcopy(hit[1]), "cached": True}
    try:
        v = api.check(text, con=c).model_dump()
    except Exception as e:
        # If the hosted model is unreachable: the built-in examples fall back to verdicts recorded from a
        # real local Qwen3 run, and other text to a keyword match on explicitly rejected alternatives.
        # Both are labelled as such. If neither applies, surface the error honestly.
        cached = _cached_checks().get(fallback.normalize(text))
        if cached:
            cached["model"] = f"{cached['model']} (recorded from a local run; hosted model unavailable)"
            return {**cached, "fallback": "recorded"}
        v = fallback.keyword_check(text, api.list_entries("settled", con=con()))
        if v:
            return {**v.model_dump(), "fallback": "keyword"}
        raise HTTPException(502, f"Model call failed: {_safe(e)}")
    if len(_verdict_cache) >= 256:
        _verdict_cache.pop(next(iter(_verdict_cache)))
    _verdict_cache[key] = (time.monotonic(), v)
    return v


# Repeated checks of the same text (e.g. judges clicking the same example) reuse the model's verdict instead of
# spending the hosted model's small per-minute quota. The key includes a fingerprint of the settled ledger and of
# the feedback, so a correction or a new decision makes the next check ask the model again.
VERDICT_TTL = 600
_verdict_cache: dict[tuple, tuple[float, dict]] = {}


def _ledger_fingerprint(c) -> tuple:
    settled = c.execute("SELECT COUNT(*), MAX(recorded_at) FROM entries WHERE status = 'settled'").fetchone()
    feedback = c.execute("SELECT COUNT(*) FROM feedback").fetchone()
    return (settled[0], settled[1], feedback[0])


def _cached_checks() -> dict:
    import json

    p = ROOT / "demo" / "cached_checks.json"
    data = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    return {fallback.normalize(k): v for k, v in data.items()}


@app.post("/api/correct")
def correct(body: CorrectBody):
    api.correct_check(body.text, body.note, con=con())
    return {"ok": True}


@app.post("/api/ingest")
async def ingest(file: UploadFile = File(...), kind: str | None = Form(None)):
    data = await file.read()
    if len(data) > 4_000_000:
        raise HTTPException(413, "File too large for the hosted demo (4 MB). Run Sthira locally for full exports.")
    return api.ingest_upload(file.filename or "upload.json", data, kind or None, con=con())


@app.post("/api/import")
async def import_and_extract(file: UploadFile = File(...), kind: str | None = Form(None)):
    """Ingest + extract in one request (serverless instances don't share /tmp between requests)."""
    data = await file.read()
    if len(data) > 4_000_000:
        raise HTTPException(413, "File too large for the hosted demo (4 MB). Run Sthira locally for full exports.")
    c = con()
    r = api.ingest_upload(file.filename or "upload.json", data, kind or None, con=c)
    try:
        llm.chat_json("Reply with JSON.", 'Return {"ok": true}', {"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]})
    except Exception as e:
        raise HTTPException(502, f"Model call failed: {_safe(e)}")
    entries = api.extract(3, con=c, source_ids=r["source_ids"])  # only this upload, never someone else's
    return {"messages": r["messages"], "sources": r["sources"], "entries": [e.model_dump() for e in entries]}


@app.get("/api/health")
def health():
    try:
        out = llm.chat_json("Reply with JSON.", 'Return {"ok": true}', {"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]})
        return {"model": config.model(), "ok": bool(out.get("ok"))}
    except Exception as e:
        raise HTTPException(502, f"Model call failed: {_safe(e)}")


@app.post("/api/extract")
def extract(body: ExtractBody):
    try:
        return [e.model_dump() for e in api.extract(min(body.limit or 3, 5), con=con())]
    except Exception as e:
        raise HTTPException(502, f"Model call failed: {_safe(e)}")


@app.get("/api/rules")
def rules():
    return api.learned_rules(con=con())


@app.get("/api/stats")
def stats():
    return api.feedback_stats(con=con())


@app.get("/api/agents-md")
def agents_md():
    from sthira import sync

    return {"markdown": sync.render(con())}


STATIC_FILES = {"app.css": "text/css; charset=utf-8", "app.js": "text/javascript; charset=utf-8"}


@app.get("/static/{name}", include_in_schema=False)
def static_file(name: str):
    # An explicit allowlist, read the same way as index.html, so it ships with the function on Vercel.
    if name not in STATIC_FILES:
        raise HTTPException(404, "not found")
    return Response((HERE / "static" / name).read_text(encoding="utf-8"), media_type=STATIC_FILES[name],
                    headers={"Cache-Control": "public, max-age=300"})


@app.get("/api/entries/{entry_id}/context")
def entry_context(entry_id: str, around: int = 2):
    """The source conversation around an entry's quote, so you can read it in context."""
    c = con()
    e = store.get_entry(c, entry_id)
    if e is None:
        raise HTTPException(404, "entry not found")
    conv_id, _, msg_id = e.source.locator.partition(" / ")
    rows = c.execute("SELECT msg_id, role, ts, text FROM messages WHERE source_id = ? AND conv_id = ? "
                     "ORDER BY COALESCE(ts, ''), rowid", (e.source.id, conv_id)).fetchall()
    idx = next((i for i, r in enumerate(rows) if r["msg_id"] == msg_id), None)
    if idx is None:
        return {"title": e.source.title, "messages": []}
    around = max(0, min(around, 5))
    window = rows[max(0, idx - around): idx + around + 1]
    return {"title": e.source.title, "messages": [
        {"role": r["role"], "ts": r["ts"], "text": r["text"][:1500], "match": r["msg_id"] == msg_id} for r in window]}


@app.get("/api/history")
def history(limit: int = 30):
    """What happened in the ledger, newest first: extractions, settles, rejections and corrections."""
    c = con()
    limit = max(1, min(limit, 100))
    events = [{"at": r["recorded_at"], "type": "extracted", "entry_id": r["id"], "kind": r["kind"],
               "text": r["statement"], "status": r["status"]}
              for r in c.execute("SELECT id, kind, statement, status, recorded_at FROM entries "
                                 "ORDER BY recorded_at DESC LIMIT ?", (limit,))]
    events += [{"at": r["created_at"], "type": r["action"], "target": r["target"], "entry_id": r["entry_id"],
                "text": r["snippet"] or "", "note": r["note"]}
               for r in c.execute("SELECT entry_id, target, action, note, snippet, created_at FROM feedback "
                                  "ORDER BY created_at DESC LIMIT ?", (limit,))]
    events.sort(key=lambda ev: ev["at"] or "", reverse=True)
    return events[:limit]


@app.get("/api/export")
def export(format: str = "json"):
    """Download the whole ledger, superseded and rejected entries included."""
    entries = [e.model_dump() for e in api.list_entries(con=con())]
    if format == "json":
        return Response(json.dumps({"format": "sthira-ledger/1", "entries": entries}, indent=2),
                        media_type="application/json",
                        headers={"Content-Disposition": 'attachment; filename="sthira-ledger.json"'})
    if format != "md":
        raise HTTPException(400, "format must be json or md")
    lines = ["# Sthira ledger", ""]
    for status in ("settled", "proposed", "superseded", "rejected"):
        group = [e for e in entries if e["status"] == status]
        if not group:
            continue
        lines += [f"## {status.capitalize()}", ""]
        for e in group:
            lines.append(f"### {e['title']}")
            lines.append(f"- **{e['kind'].replace('_', ' ')}:** {e['statement']}")
            if e["rationale"]:
                lines.append(f"- **Why:** {e['rationale']}")
            if e["alternatives_rejected"]:
                lines.append(f"- **Rejected:** {', '.join(e['alternatives_rejected'])}")
            if e["superseded_by"]:
                lines.append(f"- **Superseded by:** {e['superseded_by']}")
            src = e["source"]
            lines.append(f"- **Source:** {src['title']} ({src['type']}, {(e['decided_at'] or '')[:10]}, {src['locator']})")
            lines.append(f"  > {src['quote']}")
            lines.append("")
    return Response("\n".join(lines), media_type="text/markdown; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="sthira-ledger.md"'})


@app.get("/api/eval")
def eval_summary():
    """Headline numbers from eval/README.md, for the evidence panel."""
    return json.loads((HERE / "eval_summary.json").read_text(encoding="utf-8"))


@app.get("/api/demo-session")
def demo_session():
    """The demo Claude Code session (demo/claude_code/session.jsonl), for the live agent simulation."""
    from sthira.ingest import claude_code

    path = ROOT / "demo" / "claude_code" / "session.jsonl"
    if not path.exists():
        return {"title": "", "messages": []}
    title, msgs = claude_code.parse(path.read_text(encoding="utf-8"), path.name)
    return {"title": title, "messages": [{"role": m.role, "text": m.text} for m in msgs]}
