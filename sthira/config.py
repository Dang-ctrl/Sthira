import os
from pathlib import Path


def db_path() -> Path:
    p = os.environ.get("STHIRA_DB")
    path = Path(p).expanduser() if p else Path.home() / ".sthira" / "sthira.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def provider() -> str:
    return os.environ.get("STHIRA_PROVIDER", "ollama").lower()


def model() -> str:
    return os.environ.get("STHIRA_MODEL", "qwen3:4b")


def ollama_host() -> str:
    return os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")


def openai_base_url() -> str:
    url = os.environ.get("STHIRA_OPENAI_BASE_URL", "")
    if not url and (os.environ.get("AI_GATEWAY_API_KEY") or os.environ.get("VERCEL_OIDC_TOKEN")):
        url = "https://ai-gateway.vercel.sh/v1"  # Vercel AI Gateway, serving open-weight models (e.g. alibaba/qwen-3-32b)
    return url.rstrip("/")


def openai_api_key() -> str:
    return (os.environ.get("STHIRA_OPENAI_API_KEY") or os.environ.get("AI_GATEWAY_API_KEY")
            or os.environ.get("VERCEL_OIDC_TOKEN", ""))


def fallback_model() -> str:
    """Optional second open-weight model on the same endpoint, used when the first is rate limited."""
    return os.environ.get("STHIRA_FALLBACK_MODEL", "")
