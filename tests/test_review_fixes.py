"""Regression tests for the review findings on PRs #1 and #3."""

import io
import json
import zipfile

import pytest

from sthira import api, check, store
from sthira.ingest import parse_bytes
from sthira.models import Entry, Message, SourceRef


def _e(statement, status="settled", alts=()):
    return Entry(id=store.new_id("e"), kind="decision", title=statement[:20], statement=statement, status=status,
                 trust="confirmed", alternatives_rejected=list(alts), recorded_at=store.now(),
                 source=SourceRef(id="s", type="chatgpt"))


def test_supersede_validates_before_writing(tmp_path):
    con = store.connect(tmp_path / "t.db")
    new = store.insert_entry(con, _e("Use CockroachDB", status="proposed"))
    with pytest.raises(KeyError):
        api.supersede("e_missing", new.id, con=con)
    assert store.get_entry(con, new.id).status == "proposed"  # nothing was written
    with pytest.raises(ValueError):
        api.supersede(new.id, new.id, con=con)


def test_multiword_rejected_alternatives_reach_the_judge(tmp_path):
    con = store.connect(tmp_path / "t.db")
    target = store.insert_entry(con, _e("Push uses APNs on iOS", alts=["Firebase Cloud Messaging (FCM)"]))
    login = store.insert_entry(con, _e("Login uses magic links only", alts=["email+password"]))
    for i in range(15):  # more than k settled entries, so the FTS/boost path is used
        store.insert_entry(con, _e(f"Unrelated decision number {i} about colours"))
    ids = {e.id for e in check.candidates(con, "switch notifications to FCM")}
    assert target.id in ids
    ids = {e.id for e in check.candidates(con, "add an email and password signup form")}
    assert login.id in ids


def test_pending_conversations_scoped_by_source(tmp_path):
    con = store.connect(tmp_path / "t.db")
    a = store.upsert_source(con, "transcript", "a/standup.md", "standup")
    b = store.upsert_source(con, "transcript", "b/standup.md", "standup")
    store.add_messages(con, a, [Message(conv_id="standup", msg_id="0", role="x", ts="2026-01-01T00:00:00Z", text="old")])
    store.add_messages(con, b, [Message(conv_id="standup", msg_id="0", role="x", ts="2026-05-01T00:00:00Z", text="new")])
    store.mark_extracted(con, [r["id"] for r in con.execute("SELECT id FROM messages WHERE source_id = ?", (a,))])
    pending = store.pending_conversations(con)
    assert [c["source_id"] for c in pending] == [b]  # source a's same-named conversation isn't re-sent
    assert [m["text"] for m in pending[0]["messages"]] == ["new"]
    assert store.pending_conversations(con, source_ids=[a]) == []


def test_ingest_returns_source_ids_for_scoped_extraction(tmp_path):
    con = store.connect(tmp_path / "t.db")
    r = api.ingest_upload("2026-05-12-standup.md", b"Ojas: We ship web first.\n", con=con)
    assert r["sources"] == 1 and len(r["source_ids"]) == 1
    assert [c["source_id"] for c in store.pending_conversations(con, r["source_ids"])] == r["source_ids"]


def test_reject_resets_trust(tmp_path):
    con = store.connect(tmp_path / "t.db")
    e = store.insert_entry(con, _e("x", status="proposed"))
    api.review(e.id, "settle", con=con)
    assert api.review(e.id, "reject", con=con).trust == "quarantined"


def test_zip_bomb_is_refused(monkeypatch):
    from sthira import ingest

    monkeypatch.setattr(ingest, "MAX_UNZIPPED", 1000)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("conversations.json", json.dumps([{"pad": "0" * 5000}]))
    with pytest.raises(ValueError):
        parse_bytes("export.zip", buf.getvalue())
