"""Claude Code session transcripts (`~/.claude/projects/<project>/<session>.jsonl`)."""

from __future__ import annotations

import json
from pathlib import Path

from ..models import Message


def _text(content) -> str:
    if isinstance(content, str):
        return content
    parts = []
    for block in content or []:
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
    return "\n".join(parts)


def parse(text: str, name: str) -> tuple[str, list[Message]]:
    out: list[Message] = []
    title = ""
    for i, line in enumerate(text.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if rec.get("type") not in {"user", "assistant"} or rec.get("isMeta"):
            continue
        msg = rec.get("message") or {}
        body = _text(msg.get("content")).strip()
        # Skip slash-command plumbing and system reminders that aren't human or agent prose.
        if not body or body.startswith("<command-") or body.startswith("<local-command"):
            continue
        role = msg.get("role") or rec.get("type")
        if not title and role == "user":
            title = body.splitlines()[0][:80]
        out.append(Message(conv_id=str(rec.get("sessionId") or Path(name).stem), conv_title="", msg_id=str(rec.get("uuid") or i),
                           role=role, ts=rec.get("timestamp"), text=body))
    title = title or Path(name).stem
    for m in out:
        m.conv_title = f"Claude Code: {title}"
    return title, out
