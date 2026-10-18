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
