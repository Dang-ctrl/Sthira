"""Sthira web demo: FastAPI over `sthira.api`, plus a single-page UI."""

from __future__ import annotations

import os
import threading
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

# On serverless hosts only /tmp is writable; each cold start gets a freshly seeded demo ledger.
if "STHIRA_DB" not in os.environ:
    os.environ["STHIRA_DB"] = "/tmp/sthira.db" if os.environ.get("VERCEL") else str(ROOT / ".sthira" / "web.db")
if os.environ.get("VERCEL") and "STHIRA_PROVIDER" not in os.environ:
    os.environ["STHIRA_PROVIDER"] = "openai"
    os.environ.setdefault("STHIRA_MODEL", "alibaba/qwen-3-32b")

from sthira import api, config, llm, store  # noqa: E402

from . import seed  # noqa: E402

app = FastAPI(title="Sthira", version="0.1.0")
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


@app.post("/api/entries/{old_id}/supersede/{new_id}")
def supersede(old_id: str, new_id: str):
    return api.supersede(old_id, new_id, con=con()).model_dump()


@app.post("/api/check")
def check(body: CheckBody):
    if not body.text.strip():
        raise HTTPException(400, "text is empty")
    try:
        return api.check(body.text[:4000], con=con()).model_dump()
    except Exception as e:
        # If the hosted model is unreachable, the built-in examples fall back to verdicts recorded from a
        # real local Qwen3 run (labelled as such). Anything else surfaces the error honestly.
        cached = _cached_checks().get(body.text.strip())
        if cached:
            cached["model"] = f"{cached['model']} (recorded from a local run; hosted model unavailable)"
            return cached
        raise HTTPException(502, f"Model call failed: {e}")


def _cached_checks() -> dict:
    import json

    p = ROOT / "demo" / "cached_checks.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


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
        raise HTTPException(502, f"Model call failed: {e}")
    entries = api.extract(3, con=c)
    return {"messages": r["messages"], "sources": r["sources"], "entries": [e.model_dump() for e in entries]}


@app.get("/api/health")
def health():
    try:
        out = llm.chat_json("Reply with JSON.", 'Return {"ok": true}', {"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]})
        return {"model": config.model(), "ok": bool(out.get("ok"))}
    except Exception as e:
        raise HTTPException(502, f"Model call failed: {e}")


@app.post("/api/extract")
def extract(body: ExtractBody):
    try:
        return [e.model_dump() for e in api.extract(min(body.limit or 3, 5), con=con())]
    except Exception as e:
        raise HTTPException(502, f"Model call failed: {e}")


@app.get("/api/stats")
def stats():
    return api.feedback_stats(con=con())


@app.get("/api/agents-md")
def agents_md():
    from sthira import sync

    return {"markdown": sync.render(con())}
