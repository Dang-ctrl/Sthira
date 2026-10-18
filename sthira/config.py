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
    return os.environ.get("STHIRA_OPENAI_BASE_URL", "").rstrip("/")


def openai_api_key() -> str:
    return os.environ.get("STHIRA_OPENAI_API_KEY", "")


def fallback_model() -> str:
    """Optional second open-weight model on the same endpoint, used when the first is rate limited."""
    return os.environ.get("STHIRA_FALLBACK_MODEL", "")
