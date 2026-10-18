import os

os.environ["STHIRA_FAKE"] = "1"

import pytest
from fastapi.testclient import TestClient

from web import fake_api
from web.app import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset():
    fake_api.reset()


def test_mongodb_contradicts_postgres_decision():
    v = client.post("/api/check", json={"text": "Let's switch the user store to MongoDB"}).json()
    assert v["verdict"] == "contradicts"
    assert v["conflicts"][0]["entry"]["id"] == "e_postgres"
    assert v["conflicts"][0]["entry"]["source"]["quote"]


def test_review_reject_counts_as_correction():
    before = client.get("/api/stats").json()
    e = client.post("/api/entries/e_lunch/review", json={"action": "reject"}).json()
    assert e["status"] == "rejected"
    after = client.get("/api/stats").json()
    assert after["corrections"] == before["corrections"] + 1
    assert after["precision_after"] > before["precision_after"]


def test_review_unknown_entry_404():
    assert client.post("/api/entries/nope/review", json={"action": "settle"}).status_code == 404


def test_review_bad_action_422():
    assert client.post("/api/entries/e_lunch/review", json={"action": "delete"}).status_code == 422


def test_filters():
    settled = client.get("/api/entries", params={"status": "settled"}).json()
    assert settled and all(e["status"] == "settled" for e in settled)
    assert [e["id"] for e in client.get("/api/entries", params={"q": "magic"}).json()] == ["e_magic_links"]


def test_ingest_then_extract():
    r = client.post("/api/ingest", files={"file": ("chat.txt", b"hi\nlet's use markdown\n")},
                    data={"kind": "transcript"})
    assert r.json() == {"messages": 2, "sources": 1}
    assert len(client.post("/api/extract", json={"limit": 1}).json()) == 1
    assert len(client.post("/api/extract", json={}).json()) == 1
    assert client.post("/api/extract", json={}).json() == []


def test_index_served():
    assert "Sthira" in client.get("/").text
