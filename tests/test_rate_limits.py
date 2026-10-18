import httpx
import pytest

from sthira import llm


class _Resp:
    def __init__(self, status, body=None, headers=None):
        self.status_code, self._body, self.headers, self.text = status, body or {}, headers or {}, str(body)

    def json(self):
        return self._body


def _ok(content='{"ok": true}'):
    return _Resp(200, {"choices": [{"message": {"content": content}}]})


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("STHIRA_PROVIDER", "openai")
    monkeypatch.setenv("STHIRA_OPENAI_BASE_URL", "http://provider.test/v1")
    monkeypatch.setenv("STHIRA_MODEL", "main-model")
    monkeypatch.delenv("STHIRA_FALLBACK_MODEL", raising=False)
    monkeypatch.setattr(llm.time, "sleep", lambda s: None)


def test_max_tokens_is_sent(monkeypatch):
    seen = {}
    monkeypatch.setattr(httpx, "post", lambda url, json=None, **k: seen.update(json) or _ok())
    llm.chat_json("s", "u", {}, max_tokens=321)
    assert seen["max_tokens"] == 321


def test_429_is_retried_then_succeeds(monkeypatch):
    calls = iter([_Resp(429, {"e": 1}, {"retry-after": "1"}), _ok()])
    monkeypatch.setattr(httpx, "post", lambda *a, **k: next(calls))
    assert llm.chat_json("s", "u", {}) == {"ok": True}


def test_exhausted_quota_falls_back_to_second_model(monkeypatch):
    monkeypatch.setenv("STHIRA_FALLBACK_MODEL", "backup-model")
    used = []

    def post(url, json=None, **k):
        used.append(json["model"])
        return _Resp(429, {}, {"retry-after": "30"}) if json["model"] == "main-model" else _ok()

    monkeypatch.setattr(httpx, "post", post)
    assert llm.chat_json("s", "u", {}) == {"ok": True}
    assert used == ["main-model", "backup-model"]


def test_rate_limit_without_fallback_raises_clear_error(monkeypatch):
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _Resp(429, {}, {"retry-after": "30"}))
    with pytest.raises(llm.LLMError, match="Rate limited"):
        llm.chat_json("s", "u", {})


def test_extract_waits_and_retries_a_rate_limited_chunk(tmp_path, monkeypatch):
    from sthira import api, extract, store

    monkeypatch.setattr(extract.time, "sleep", lambda s: None)
    calls = {"n": 0}

    def fake_chat(system, user, schema, **k):
        calls["n"] += 1
        if calls["n"] == 1:
            raise llm.LLMRateLimited("slow down", retry_after=3)
        return {"entries": [{"kind": "decision", "title": "Use SQLite", "statement": "Use SQLite for search.",
                             "rationale": "", "alternatives_rejected": [], "quote": "we use SQLite for search",
                             "msg": 0, "confidence": 0.9}]}

    monkeypatch.setattr(llm, "chat_json", fake_chat)
    con = store.connect(tmp_path / "t.db")
    api.ingest_upload("2026-10-18-plan.md", b"Ojas: we use SQLite for search.\n", con=con)
    errors = []
    created = api.extract(con=con, errors=errors)
    assert len(created) == 1 and errors == [] and calls["n"] == 2


def test_extract_reports_chunks_it_could_not_read(tmp_path, monkeypatch):
    from sthira import api, extract, store

    monkeypatch.setattr(extract.time, "sleep", lambda s: None)
    monkeypatch.setattr(llm, "chat_json", lambda *a, **k: (_ for _ in ()).throw(llm.LLMRateLimited("quota", 120)))
    con = store.connect(tmp_path / "t.db")
    api.ingest_upload("2026-10-18-plan.md", b"Ojas: we use SQLite for search.\n", con=con)
    errors = []
    assert api.extract(con=con, errors=errors) == []
    assert len(errors) == 1 and "quota" in errors[0]
    assert store.pending_conversations(con)  # still pending, so the next run picks it up


def test_extract_splits_a_chunk_whose_output_is_invalid(tmp_path, monkeypatch):
    from sthira import api, store

    seen = []

    def fake_chat(system, user, schema, **k):
        seen.append(user.count("\n["))  # number of messages in this call
        if seen[-1] > 1:
            raise llm.LLMError("Failed to validate JSON")  # a dense chunk got cut off
        return {"entries": []}

    monkeypatch.setattr(llm, "chat_json", fake_chat)
    con = store.connect(tmp_path / "t.db")
    api.ingest_upload("2026-10-18-plan.md", b"Ojas: we use SQLite.\nDanica: agreed.\nVidit: ok.\nOjas: done.\n", con=con)
    errors = []
    api.extract(con=con, errors=errors)
    assert errors == [] and seen[0] == 4 and seen[-1] == 1  # 4 -> 2+2 -> 1+1+1+1, nothing was lost
    assert not store.pending_conversations(con)
