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


def test_sync_cursor_rule(tmp_path):
    con = store.connect(tmp_path / "t.db")
    store.insert_entry(con, _entry("Use Postgres for the user store"))
    target = tmp_path / ".cursor" / "rules" / "sthira.mdc"
    sync.sync_cursor(con, str(target))
    text = target.read_text(encoding="utf-8")
    assert text.startswith("---\n") and "alwaysApply: true" in text
    assert "Use Postgres" in text and sync.START not in text
