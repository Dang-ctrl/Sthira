"""Sthira web demo: the HTTP API from docs/CONTRACTS.md plus a single-page UI.

Uses the real `sthira.api` when it is importable, otherwise the in-memory
fake in `web/fake_api.py`. Set STHIRA_FAKE=1 to force the fake.
"""

from __future__ import annotations

import dataclasses
import os
import tempfile
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

if os.environ.get("STHIRA_FAKE") == "1":
    from web import fake_api as api
else:
    try:
        from sthira import api  # type: ignore[no-redef]
    except ImportError:
        from web import fake_api as api

USING_FAKE = getattr(api, "__name__", "") == "web.fake_api"
STATIC = Path(__file__).parent / "static"

app = FastAPI(title="Sthira", version="0.1.0")


def dump(obj: Any) -> Any:
    """Turn whatever the core returns (Pydantic, dataclass, dict) into JSON-able data."""
    if isinstance(obj, list):
        return [dump(o) for o in obj]
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return dataclasses.asdict(obj)
    return obj


class ReviewBody(BaseModel):
    action: Literal["settle", "reject"]
    note: str | None = None


class CheckBody(BaseModel):
    text: str


class ExtractBody(BaseModel):
    limit: int | None = None


@app.get("/api/entries")
def get_entries(status: str | None = None, kind: str | None = None, q: str | None = None):
    return dump(api.list_entries(status=status, kind=kind, q=q))


@app.post("/api/entries/{entry_id}/review")
def review_entry(entry_id: str, body: ReviewBody):
    try:
        return dump(api.review(entry_id, body.action, body.note))
    except KeyError:
        raise HTTPException(404, f"no entry {entry_id}")


@app.post("/api/check")
def check(body: CheckBody):
    if not body.text.strip():
        raise HTTPException(422, "text is empty")
    return dump(api.check(body.text))


@app.post("/api/ingest")
async def ingest(file: UploadFile = File(...), kind: str | None = Form(None)):
    suffix = Path(file.filename or "upload").suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    try:
        return dump(api.ingest(tmp_path, kind))
    finally:
        os.unlink(tmp_path)


@app.post("/api/extract")
def extract(body: ExtractBody | None = None):
    return dump(api.extract(limit=body.limit if body else None))


@app.get("/api/stats")
def stats():
    entries = dump(api.list_entries())
    by_status: dict[str, int] = {}
    by_kind: dict[str, int] = {}
    for e in entries:
        by_status[e["status"]] = by_status.get(e["status"], 0) + 1
        by_kind[e["kind"]] = by_kind.get(e["kind"], 0) + 1
    return {
        **dump(api.feedback_stats()),
        "total": len(entries),
        "by_status": by_status,
        "by_kind": by_kind,
        "backend": "fake" if USING_FAKE else "sthira",
    }


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
