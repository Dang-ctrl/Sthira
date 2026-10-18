"""Upload size limits on the hosted demo."""

import io
import json
import os
import tempfile
import zipfile

os.environ.setdefault("STHIRA_DB", os.path.join(tempfile.mkdtemp(), "web-test.db"))
os.environ.setdefault("STHIRA_PROVIDER", "ollama")
os.environ.setdefault("OLLAMA_HOST", "http://127.0.0.1:9")

from fastapi.testclient import TestClient  # noqa: E402

from web.app import app  # noqa: E402

client = TestClient(app)


def _zip(name: str, data: bytes) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(name, data)
    return buf.getvalue()


def test_zip_that_inflates_past_limit_is_rejected():
    bomb = _zip("export/conversations.json", b" " * 25_000_000)
    assert len(bomb) < 4_000_000
    r = client.post("/api/ingest", files={"file": ("export.zip", bomb)})
    assert r.status_code == 413 and "unzipped" in r.json()["detail"]


def test_small_zip_is_ingested():
    conv = [{"uuid": "c1", "name": "Zip test", "chat_messages": [
        {"uuid": "m1", "sender": "human", "text": "We decided to ship the zip importer.", "created_at": "2026-10-18T05:00:00Z"}]}]
    r = client.post("/api/ingest", files={"file": ("export.zip", _zip("conversations.json", json.dumps(conv).encode()))})
    assert r.status_code == 200 and r.json()["messages"] == 1


def test_bad_zip_is_400():
    r = client.post("/api/ingest", files={"file": ("export.zip", b"not a zip")})
    assert r.status_code == 400
