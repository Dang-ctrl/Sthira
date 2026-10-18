"""Open-weight model access. Ollama locally, or any OpenAI-compatible endpoint serving an open-weight model."""

from __future__ import annotations

import json
import re

import httpx

from . import config


class LLMError(RuntimeError):
    pass


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


def chat_json(system: str, user: str, schema: dict, timeout: float = 240.0) -> dict:
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
        r = httpx.post(f"{config.ollama_host()}/api/chat", json=payload, timeout=timeout)
        if r.status_code >= 400:
            raise LLMError(f"Ollama error {r.status_code}: {r.text[:300]}")
        return _parse_json(r.json()["message"]["content"])

    base = config.openai_base_url()
    if not base:
        raise LLMError("STHIRA_OPENAI_BASE_URL is not set")
    sys_with_schema = f"{system}\n\nRespond with JSON only, matching this JSON schema:\n{json.dumps(schema)}"
    payload = {
        "model": config.model(),
        "messages": [{"role": "system", "content": sys_with_schema}, {"role": "user", "content": user}],
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }
    headers = {"Authorization": f"Bearer {config.openai_api_key()}"}
    r = httpx.post(f"{base}/chat/completions", json=payload, headers=headers, timeout=timeout)
    if r.status_code >= 400:
        raise LLMError(f"Provider error {r.status_code}: {r.text[:300]}")
    return _parse_json(r.json()["choices"][0]["message"]["content"])
