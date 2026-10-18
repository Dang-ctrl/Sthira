"""Gemini Apps activity from Google Takeout (`My Activity/Gemini Apps/MyActivity.json`).

Each activity item is one prompt ("Prompted <text>") with the response as HTML in `safeHtmlItem`.
Takeout has no conversation ids, so prompts on the same day are grouped into one conversation.
Written against the documented My Activity shape; tolerant of missing fields.
"""

from __future__ import annotations

import html
import re

from ..models import Message

_TAGS = re.compile(r"<[^>]+>")


def is_gemini(obj) -> bool:
    return (isinstance(obj, list) and obj and isinstance(obj[0], dict)
            and "Gemini" in str(obj[0].get("header", "")) and "title" in obj[0])


def _text(h: str) -> str:
    text = re.sub(r"\s+", " ", html.unescape(_TAGS.sub(" ", h or ""))).strip()
    return re.sub(r"\s+([.,;:!?])", r"", text)


def parse(items: list) -> list[Message]:
    out: list[Message] = []
    for i, it in enumerate(sorted((x for x in items if isinstance(x, dict)), key=lambda x: x.get("time", ""))):
        ts = it.get("time")
        day = (ts or "undated")[:10]
        conv = f"gemini-{day}"
        prompt = str(it.get("title", ""))
        prompt = prompt[len("Prompted "):] if prompt.startswith("Prompted ") else prompt
        if prompt.strip():
            out.append(Message(conv_id=conv, conv_title=f"Gemini {day}", msg_id=f"{i}-p", role="user", ts=ts, text=prompt.strip()))
        reply = " ".join(_text(s.get("html", "")) for s in it.get("safeHtmlItem") or [] if isinstance(s, dict))
        if reply:
            out.append(Message(conv_id=conv, conv_title=f"Gemini {day}", msg_id=f"{i}-r", role="assistant", ts=ts, text=reply))
    return out
