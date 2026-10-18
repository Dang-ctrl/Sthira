"""Write the settled ledger into AGENTS.md / CLAUDE.md so every coding agent starts with it."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from . import store

START, END = "<!-- sthira:start -->", "<!-- sthira:end -->"
LABELS = {
    "decision": "Decisions", "preference": "Preferences", "commitment": "Commitments",
    "lesson": "Lessons", "assumption": "Assumptions", "open_question": "Open questions (ask, don't assume)",
}


def render(con: sqlite3.Connection) -> str:
    entries = store.list_entries(con, status="settled")
    lines = [START, "## Settled context (managed by Sthira; do not edit by hand)",
             "Respect these. If your work would contradict one, stop and ask the user first.", ""]
    for kind, label in LABELS.items():
        group = [e for e in entries if e.kind == kind]
        if kind == "open_question":
            group = [e for e in store.list_entries(con, kind="open_question") if e.status in ("settled", "proposed")]
        if not group:
            continue
        lines.append(f"### {label}")
        for e in group:
            when = (e.decided_at or "")[:10]
            why = f" Because: {e.rationale}" if e.rationale else ""
            lines.append(f"- {e.statement}{why} _(source: {e.source.title}, {when})_")
        lines.append("")
    lines.append(END)
    return "\n".join(lines)


def sync(con: sqlite3.Connection, path: str = "AGENTS.md") -> str:
    block = render(con)
    p = Path(path)
    text = p.read_text(encoding="utf-8") if p.exists() else ""
    if START in text and END in text:
        text = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda _: block, text, flags=re.S)
    else:
        text = (text.rstrip() + "\n\n" if text.strip() else "") + block + "\n"
    p.write_text(text, encoding="utf-8")
    return block


CURSOR_RULE = ".cursor/rules/sthira.mdc"


def sync_cursor(con: sqlite3.Connection, path: str = CURSOR_RULE) -> str:
    """Write settled context as an always-applied Cursor rule. The whole file is managed by Sthira."""
    body = render(con).replace(START, "").replace(END, "").strip()
    text = ("---\ndescription: Settled decisions and context managed by Sthira (do not edit by hand)\n"
            "alwaysApply: true\n---\n\n" + body + "\n")
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return text
