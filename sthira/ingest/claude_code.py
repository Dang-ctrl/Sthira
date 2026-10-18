"""Claude Code session transcripts (`~/.claude/projects/<project>/<session>.jsonl`)."""

from __future__ import annotations

import json
import re
from pathlib import Path

from ..models import Message


_HARNESS = re.compile(r"<(system-reminder|local-command-caveat|local-command-stdout|command-name|command-message|command-args)>.*?</\1>", re.S)


def _clean(text: str) -> str:
    """Drop harness-injected blocks (reminders, slash-command plumbing) so only human/agent prose remains."""
    return _HARNESS.sub("", text).strip()


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
    project = ""
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
        project = project or Path(str(rec.get("cwd") or "")).name
        msg = rec.get("message") or {}
        body = _clean(_text(msg.get("content")))
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
        m.conv_title = f"Claude Code ({project}): {title}" if project else f"Claude Code: {title}"
    return title, out
