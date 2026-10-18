"""Open-weight model access. Ollama locally, or any OpenAI-compatible endpoint serving an open-weight model."""

from __future__ import annotations

import json
import re
import time

import httpx

from . import config


class LLMError(RuntimeError):
    pass


class LLMUnavailable(LLMError):
    """The model server can't be reached at all. Unlike a bad response, retrying the next chunk won't help."""


def _parse_json(text: str) -> dict:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.S)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, flags=re.S)
        if m:
            return json.loads(m.group(0))
        raise LLMError(f"Model did not return JSON: {text[:200]}")


def chat_json(system: str, user: str, schema: dict, timeout: float = 240.0, max_tokens: int = 1200) -> dict:
    """Ask the model for JSON matching `schema`. Uses constrained decoding where the provider supports it."""
    if config.provider() == "ollama":
        payload = {
            "model": config.model(),
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "format": schema,
            "stream": False,
            "think": False,
            "options": {"temperature": 0, "num_ctx": 16384},
        }
        try:
            r = httpx.post(f"{config.ollama_host()}/api/chat", json=payload, timeout=timeout)
        except (httpx.ConnectError, httpx.ConnectTimeout) as e:
            raise LLMUnavailable(f"Can't reach Ollama at {config.ollama_host()}. Is it running? Start it with `ollama serve`.") from e
        except httpx.TimeoutException as e:
            raise LLMError(f"Ollama timed out after {timeout:.0f}s") from e
        if r.status_code >= 400:
            raise LLMError(f"Ollama error {r.status_code}: {r.text[:300]}")
        return _parse_json(r.json()["message"]["content"])

    return _chat_openai(system, user, schema, timeout, max_tokens)


def _chat_openai(system: str, user: str, schema: dict, timeout: float, max_tokens: int) -> dict:
    """OpenAI-compatible endpoint serving an open-weight model. Rate limits (429) are retried briefly, then the
    optional fallback model (its own quota) is tried, so a busy free tier degrades instead of failing."""
    base = config.openai_base_url()
    if not base:
        raise LLMError("STHIRA_OPENAI_BASE_URL is not set")
    sys_with_schema = f"{system}\n\nRespond with JSON only, matching this JSON schema:\n{json.dumps(schema)}"
    headers = {"Authorization": f"Bearer {config.openai_api_key()}"}
    models = [config.model()] + ([config.fallback_model()] if config.fallback_model() else [])
    last: LLMError | None = None
    for model in models:
        payload = {
            "model": model,
            "messages": [{"role": "system", "content": sys_with_schema}, {"role": "user", "content": user}],
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "max_tokens": max_tokens,  # an explicit cap also stops providers reserving a huge default against quota
        }
        for attempt in range(3):
            try:
                r = httpx.post(f"{base}/chat/completions", json=payload, headers=headers, timeout=timeout)
            except (httpx.ConnectError, httpx.ConnectTimeout) as e:
                raise LLMUnavailable(f"Can't reach the model provider at {base}.") from e
            except httpx.TimeoutException as e:
                raise LLMError(f"Model provider timed out after {timeout:.0f}s") from e
            if r.status_code == 429:
                wait = _retry_after(r)
                last = LLMError(f"Rate limited by the model provider ({model}). {r.text[:200]}")
                if attempt < 2 and wait <= 6:
                    time.sleep(wait)
                    continue
                break  # quota exhausted for this model: try the fallback model
            if r.status_code >= 400:
                raise LLMError(f"Provider error {r.status_code}: {r.text[:300]}")
            return _parse_json(r.json()["choices"][0]["message"]["content"])
    raise last or LLMError("Model call failed")


def _retry_after(r: httpx.Response) -> float:
    try:
        return max(0.5, min(float(r.headers.get("retry-after", "2")), 60.0))
    except ValueError:
        return 2.0
