"""Source parsers. Each returns (source_type, title, [Message]) per file."""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

from ..models import Message
from . import chat_exports, claude_code, gemini, subtitles, transcript

MAX_UNZIPPED = 500_000_000  # guards against zip bombs; real chat exports are far smaller
ParseResult = list[tuple[str, str, str, list[Message]]]  # (source_type, path_key, title, messages)


def parse_path(path: str | Path, kind: str | None = None) -> ParseResult:
    p = Path(path).expanduser()
    if p.is_dir():
        out: ParseResult = []
        for f in sorted(p.rglob("*")):
            if f.is_file() and f.suffix.lower() in {".json", ".jsonl", ".md", ".txt", ".zip", ".vtt", ".srt"}:
                out.extend(parse_path(f, kind))
        return out
    return parse_bytes(p.name, p.read_bytes(), kind, str(p))


def parse_bytes(name: str, data: bytes, kind: str | None = None, key: str | None = None) -> ParseResult:
    key = key or name
    suffix = Path(name).suffix.lower()
    if suffix == ".zip":
        out: ParseResult = []
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            if sum(i.file_size for i in z.infolist()) > MAX_UNZIPPED:
                raise ValueError(f"Zip expands beyond {MAX_UNZIPPED // 1_000_000} MB; unzip it and ingest the files directly.")
            for n in z.namelist():
                if n.endswith("conversations.json") or (n.endswith("MyActivity.json") and "Gemini" in n):
                    out.extend(parse_bytes(n, z.read(n), kind, f"{key}!{n}"))
        return out
    text = data.decode("utf-8", errors="replace")
    if kind == "claude_code" or (kind is None and suffix == ".jsonl"):
        title, msgs = claude_code.parse(text, name)
        return [("claude_code", key, title, msgs)] if msgs else []
    if suffix in {".vtt", ".srt"}:
        title, msgs = subtitles.parse(text, name)
        return [("transcript", key, title, msgs)] if msgs else []
    if kind == "transcript" or (kind is None and suffix in {".md", ".txt"}):
        title, msgs = transcript.parse(text, name)
        return [("transcript", key, title, msgs)] if msgs else []
    if suffix == ".json" or kind in {"chatgpt", "claude_ai", "gemini"}:
        try:
            obj = json.loads(text)
        except json.JSONDecodeError:
            return []
        if kind == "gemini" or gemini.is_gemini(obj):
            msgs = gemini.parse(obj)
            return [("gemini", key, "Gemini activity", msgs)] if msgs else []
        src, msgs = chat_exports.parse(obj)
        return [(src, key, Path(name).stem, msgs)] if msgs else []
    return []
