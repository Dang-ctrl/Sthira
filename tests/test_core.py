"""Model-free tests: parsers, store, quote verification, sync."""

import json
from pathlib import Path

from sthira import store, sync
from sthira.extract import _quote_found
from sthira.ingest import parse_bytes, parse_path
from sthira.models import Entry, SourceRef

FIX = Path(__file__).parent / "fixtures"


def test_chatgpt_export_follows_active_branch():
    [(src, _, _, msgs)] = parse_path(FIX / "conversations.json")
    assert src == "chatgpt"
    texts = [m.text for m in msgs]
    assert any("go with Postgres" in t for t in texts)
    assert all(m.role in ("user", "assistant") for m in msgs)


def test_claude_code_jsonl_keeps_text_blocks_only():
    lines = [
        {"type": "user", "sessionId": "s1", "uuid": "u1", "timestamp": "2026-10-18T09:00:00Z",
         "message": {"role": "user", "content": "Switch the user store to MongoDB"}},
        {"type": "assistant", "sessionId": "s1", "uuid": "u2",
         "message": {"role": "assistant", "content": [{"type": "text", "text": "Plan: migrate to MongoDB"},
                                                       {"type": "tool_use", "name": "Edit", "input": {}}]}},
        {"type": "summary", "summary": "x"},
    ]
    data = "\n".join(json.dumps(l) for l in lines).encode()
    [(src, _, title, msgs)] = parse_bytes("s1.jsonl", data)
    assert src == "claude_code" and len(msgs) == 2
    assert msgs[1].text == "Plan: migrate to MongoDB"
    assert title.startswith("Switch the user store")


def test_transcript_speakers():
    text = "# Standup 2026-05-12\nOjas: We ship mobile after web.\nDanica: I'll draft onboarding copy by Friday.\n"
    [(src, _, title, msgs)] = parse_bytes("2026-05-12-standup.md", text.encode())
    assert src == "transcript" and title.startswith("Standup")
    assert [m.role for m in msgs] == ["Ojas", "Danica"]
    assert msgs[0].ts == "2026-05-12T00:00:00Z"


def test_quote_verification_rejects_hallucinations():
    src = "We need joins across users. Ok let's go with Postgres, not MongoDB."
    assert _quote_found("let's go with Postgres, not MongoDB", src)
    assert not _quote_found("we will use DynamoDB for everything", src)


def _entry(statement, status="settled"):
    return Entry(id=store.new_id("e"), kind="decision", title=statement[:20], statement=statement, status=status,
                 trust="confirmed", decided_at="2026-03-04T00:00:00Z", recorded_at=store.now(),
                 source=SourceRef(id="s", type="chatgpt", title="DB choice", quote=statement))


def test_store_supersede_never_deletes(tmp_path):
    con = store.connect(tmp_path / "t.db")
    old = store.insert_entry(con, _entry("Use Postgres for the user store"))
    new = store.insert_entry(con, _entry("Use CockroachDB for the user store"))
    store.set_status(con, old.id, "superseded", superseded_by=new.id)
    all_ids = {e.id for e in store.list_entries(con)}
    assert {old.id, new.id} <= all_ids
    assert store.get_entry(con, old.id).superseded_by == new.id
    assert [e.id for e in store.list_entries(con, q="postgres")] == [old.id]


def test_sync_replaces_managed_block(tmp_path):
    con = store.connect(tmp_path / "t.db")
    store.insert_entry(con, _entry("Use Postgres for the user store"))
    target = tmp_path / "AGENTS.md"
    target.write_text("# Project\nhand-written notes\n", encoding="utf-8")
    sync.sync(con, str(target))
    sync.sync(con, str(target))
    text = target.read_text(encoding="utf-8")
    assert text.count(sync.START) == 1 and "hand-written notes" in text and "Use Postgres" in text


def test_rejections_become_rules_for_next_extraction(tmp_path):
    from sthira import api, feedback

    con = store.connect(tmp_path / "t.db")
    e = store.insert_entry(con, _entry("The user named the kitten Miso", status="proposed"))
    assert feedback.extraction_guidance(con) == ""
    api.review(e.id, "reject", "Personal life is not a project decision.", con=con)
    g = feedback.extraction_guidance(con)
    assert "Personal life is not a project decision." in g and "kitten Miso" in g
    s = feedback.stats(con)
    assert s["corrections"] == 1 and s["entries"]["rejected"] == 1


def test_replace_supersedes_and_keeps_history(tmp_path):
    from sthira import api

    con = store.connect(tmp_path / "t.db")
    old = store.insert_entry(con, _entry("Use Postgres for the user store"))
    r = api.replace(old.id, "Use CockroachDB for the user store", "multi-region writes", con=con)
    assert r["old"].status == "superseded" and r["old"].superseded_by == r["new"].id
    assert r["new"].status == "settled" and r["new"].rationale == "multi-region writes"
    assert [e.id for e in store.list_entries(con, status="settled")] == [r["new"].id]


def test_sync_cursor_rule(tmp_path):
    con = store.connect(tmp_path / "t.db")
    store.insert_entry(con, _entry("Use Postgres for the user store"))
    target = tmp_path / ".cursor" / "rules" / "sthira.mdc"
    sync.sync_cursor(con, str(target))
    text = target.read_text(encoding="utf-8")
    assert text.startswith("---\n") and "alwaysApply: true" in text
    assert "Use Postgres" in text and sync.START not in text
