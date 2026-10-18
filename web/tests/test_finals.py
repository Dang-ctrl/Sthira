"""Endpoints behind the finals UI: verdict cache, source context, history, exports, eval and the demo session."""

import os
import tempfile

os.environ.setdefault("STHIRA_DB", os.path.join(tempfile.mkdtemp(), "web-test.db"))
os.environ.setdefault("STHIRA_PROVIDER", "ollama")
os.environ.setdefault("OLLAMA_HOST", "http://127.0.0.1:9")

from fastapi.testclient import TestClient  # noqa: E402

from sthira.models import Verdict  # noqa: E402
from web import app as webapp  # noqa: E402

client = TestClient(webapp.app)


def test_repeated_check_is_cached_until_feedback_changes(monkeypatch):
    calls = []

    def fake_check(text, con=None):
        calls.append(text)
        return Verdict(input=text, verdict="unrelated", conflicts=[], model="test-model")

    monkeypatch.setattr(webapp.api, "check", fake_check)
    webapp._verdict_cache.clear()
    text = "Add a CSV export button to the notes list"
    first = client.post("/api/check", json={"text": text}).json()
    second = client.post("/api/check", json={"text": "  add a csv export button to the NOTES list "}).json()
    assert len(calls) == 1 and "cached" not in first and second["cached"] is True

    client.post("/api/correct", json={"text": text, "note": "exports are fine"})
    third = client.post("/api/check", json={"text": text}).json()
    assert len(calls) == 2 and "cached" not in third


def test_fallback_verdicts_are_not_cached():
    webapp._verdict_cache.clear()
    client.post("/api/check", json={"text": "let's just move users over to mongodb"})
    assert not webapp._verdict_cache


def test_entry_context_marks_the_quoted_message():
    entry = client.get("/api/entries", params={"status": "settled"}).json()[0]
    ctx = client.get(f"/api/entries/{entry['id']}/context").json()
    assert ctx["title"] == entry["source"]["title"]
    assert [m for m in ctx["messages"] if m["match"]]
    assert client.get("/api/entries/nope/context").status_code == 404


def test_history_is_newest_first():
    events = client.get("/api/history", params={"limit": 10}).json()
    assert 0 < len(events) <= 10
    stamps = [e["at"] for e in events]
    assert stamps == sorted(stamps, reverse=True)


def test_exports():
    j = client.get("/api/export", params={"format": "json"})
    assert j.headers["content-disposition"].endswith('sthira-ledger.json"') and j.json()["entries"]
    md = client.get("/api/export", params={"format": "md"})
    assert md.text.startswith("# Sthira ledger") and "## Settled" in md.text
    assert client.get("/api/export", params={"format": "pdf"}).status_code == 400


def test_eval_and_demo_session():
    ev = client.get("/api/eval").json()
    assert ev["checks"][-1]["correct"] == ev["checks"][-1]["total"]
    session = client.get("/api/demo-session").json()
    assert any(m["role"] == "assistant" and "MongoDB" in m["text"] for m in session["messages"])


def test_static_allowlist():
    assert client.get("/static/app.js").headers["content-type"].startswith("text/javascript")
    assert client.get("/static/app.css").headers["content-type"].startswith("text/css")
    assert client.get("/static/index.html").status_code == 404
    assert client.get("/static/..%2Fapp.py").status_code == 404
