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


def test_unreachable_model_fails_loudly(tmp_path, monkeypatch):
    import pytest

    from sthira import api, llm

    monkeypatch.setenv("STHIRA_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_HOST", "http://127.0.0.1:9")  # nothing listens here
    con = store.connect(tmp_path / "t.db")
    api.ingest(str(FIX / "conversations.json"), con=con)
    with pytest.raises(llm.LLMUnavailable):
        api.extract(con=con)
    # messages stay pending, so a later run (with the server up) still extracts them
    assert store.pending_conversations(con)
