"""Split out of test_core.py so feature branches don't collide."""

import json
from pathlib import Path

from sthira import store, sync
from sthira.ingest import parse_bytes
from sthira.models import Entry, SourceRef

FIX = Path(__file__).parent / "fixtures"


def _entry(statement, status="settled"):
    return Entry(id=store.new_id("e"), kind="decision", title=statement[:20], statement=statement, status=status,
                 trust="confirmed", decided_at="2026-03-04T00:00:00Z", recorded_at=store.now(),
                 source=SourceRef(id="s", type="chatgpt", title="DB choice", quote=statement))


def test_gemini_takeout_activity():
    items = [
        {"header": "Gemini Apps", "title": "Prompted Should Acme Notes use Postgres or MongoDB?",
         "time": "2026-03-04T10:00:00.000Z", "safeHtmlItem": [{"html": "<p>Postgres gives you <b>joins</b>.</p>"}]},
        {"header": "Gemini Apps", "title": "Prompted ok we go with Postgres", "time": "2026-03-04T10:05:00.000Z"},
        {"header": "Gemini Apps", "title": "Prompted cat names?", "time": "2026-03-06T21:00:00.000Z"},
    ]
    [(src, _, _, msgs)] = parse_bytes("MyActivity.json", json.dumps(items).encode())
    assert src == "gemini"
    assert [m.role for m in msgs] == ["user", "assistant", "user", "user"]
    assert msgs[1].text == "Postgres gives you joins."
    assert {m.conv_id for m in msgs} == {"gemini-2026-03-04", "gemini-2026-03-06"}
