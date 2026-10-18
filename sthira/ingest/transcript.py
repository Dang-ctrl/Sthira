"""Plain-text or Markdown meeting transcripts. `Speaker: text` lines become messages; other paragraphs become notes."""

from __future__ import annotations

import re
from pathlib import Path

from ..models import Message

_SPEAKER = re.compile(r"^\s*(?:\*\*)?([A-Z][\w .'-]{0,30}?)(?:\*\*)?\s*:\s+(.+)$")
_DATE = re.compile(r"(\d{4}-\d{2}-\d{2})")


def parse(text: str, name: str) -> tuple[str, list[Message]]:
    stem = Path(name).stem
    m = _DATE.search(name) or _DATE.search(text[:500])
    ts = f"{m.group(1)}T00:00:00Z" if m else None
    title = stem
    for line in text.splitlines():
        if line.startswith("#"):
            title = line.lstrip("# ").strip() or stem
            break
    out: list[Message] = []
    para: list[str] = []

    def flush():
        if para:
            out.append(Message(conv_id=stem, conv_title=title, msg_id=str(len(out)), role="note", ts=ts,
                               text=" ".join(para).strip()))
            para.clear()

    for line in text.splitlines():
        if line.startswith("#"):
            continue
        sm = _SPEAKER.match(line)
        if sm:
            flush()
            out.append(Message(conv_id=stem, conv_title=title, msg_id=str(len(out)), role=sm.group(1).strip(), ts=ts,
                               text=sm.group(2).strip()))
        elif line.strip():
            para.append(line.strip())
        else:
            flush()
    flush()
    return title, out
