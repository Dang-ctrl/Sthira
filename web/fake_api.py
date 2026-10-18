"""In-memory stand-in for `sthira.api`, used until the core engine lands.

Same function names and signatures as docs/CONTRACTS.md, seeded with the
Acme Notes demo story. Nothing here calls a model: `check` is a keyword
matcher, and `extract` hands out canned candidates.
"""

from __future__ import annotations

import copy
import re
from datetime import datetime, timezone
from pathlib import Path

MODEL = "fake-keyword-matcher"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _entry(id, kind, title, statement, *, rationale=None, rejected=(), status="settled",
           trust="confirmed", superseded_by=None, decided_at=None, source, confidence=0.8):
    return {
        "id": id,
        "kind": kind,
        "title": title,
        "statement": statement,
        "rationale": rationale,
        "alternatives_rejected": list(rejected),
        "project": "acme-notes",
        "status": status,
        "trust": trust,
        "superseded_by": superseded_by,
        "decided_at": decided_at,
        "recorded_at": "2026-10-18T09:40:00Z",
        "source": source,
        "confidence": confidence,
    }


def _seed() -> dict[str, dict]:
    db_chat = {"id": "s_chat_db", "type": "chatgpt", "title": "DB choice"}
    auth_chat = {"id": "s_chat_auth", "type": "chatgpt", "title": "Login flow"}
    pricing_chat = {"id": "s_chat_pricing", "type": "chatgpt", "title": "Pricing ideas"}
    standup = {"id": "s_standup_0512", "type": "transcript", "title": "2026-05-12 standup"}
    entries = [
        _entry(
            "e_sqlite_proto", "decision", "Use SQLite for the prototype",
            "We will start the prototype on SQLite.",
            rationale="Zero setup while we validate the idea.",
            rejected=["Postgres"], status="superseded", superseded_by="e_postgres",
            decided_at="2026-02-10T15:02:00Z", confidence=0.77,
            source={**db_chat, "locator": "conversation c_db / message m_04",
                    "quote": "sqlite is fine for now, we'll revisit"},
        ),
        _entry(
            "e_postgres", "decision", "Use Postgres for the user store",
            "We will use Postgres, not MongoDB, for the user store.",
            rationale="We need relational joins across users and orgs.",
            rejected=["MongoDB"], decided_at="2026-03-04T10:12:00Z", confidence=0.92,
            source={**db_chat, "locator": "conversation c_db / message m_17",
                    "quote": "ok let's go with postgres, we need joins across users and orgs"},
        ),
        _entry(
            "e_magic_links", "decision", "Magic-link auth, no passwords",
            "Users sign in with emailed magic links; we will not store passwords.",
            rationale="Fewer support tickets and nothing to leak.",
            rejected=["passwords", "password login"], decided_at="2026-03-09T18:40:00Z",
            confidence=0.88,
            source={**auth_chat, "locator": "conversation c_auth / message m_09",
                    "quote": "let's just do magic links, no passwords at all"},
        ),
        _entry(
            "e_pricing", "open_question", "Monthly or annual pricing?",
            "Should Acme Notes charge monthly, annually, or both?",
            status="proposed", decided_at="2026-04-02T11:20:00Z", confidence=0.71,
            source={**pricing_chat, "locator": "conversation c_pricing / message m_06",
                    "quote": "not sure yet if we go monthly or annual, park it"},
        ),
        _entry(
            "e_mobile_after_web", "decision", "Ship mobile after web",
            "The web app ships first; mobile follows after web is stable.",
            rationale="Small team; one platform at a time.",
            rejected=["mobile first"], decided_at="2026-05-12T09:15:00Z", confidence=0.84,
            source={**standup, "locator": "2026-05-12-standup.md / line 14",
                    "quote": "web first, mobile after web is stable"},
        ),
        _entry(
            "e_onboarding_copy", "commitment", "Danica drafts onboarding copy",
            "Danica will draft the onboarding copy by Friday.",
            status="proposed", decided_at="2026-05-12T09:22:00Z", confidence=0.8,
            source={**standup, "locator": "2026-05-12-standup.md / line 21",
                    "quote": "Danica will draft the onboarding copy by Friday"},
        ),
        _entry(
            "e_lunch", "decision", "Grab lunch",
            "We will grab lunch.",
            status="proposed", trust="quarantined", decided_at="2026-03-04T12:30:00Z",
            confidence=0.41,
            source={**db_chat, "locator": "conversation c_db / message m_22",
                    "quote": "sounds good, let's grab lunch and pick this up later"},
        ),
    ]
    return {e["id"]: e for e in entries}


# Candidates `extract` hands out one call at a time, as if newly ingested.
_CANDIDATES = [
    _entry(
        "e_markdown_notes", "preference", "Notes are stored as Markdown",
        "Note bodies are stored as Markdown, not rich-text JSON.",
        rationale="Portable and easy to export.", rejected=["rich-text JSON"],
        status="proposed", decided_at="2026-06-01T14:05:00Z", confidence=0.74,
        source={"id": "s_chat_editor", "type": "chatgpt", "title": "Editor format",
                "locator": "conversation c_editor / message m_11",
                "quote": "markdown under the hood, keep it portable"},
    ),
    _entry(
        "e_ok_thanks", "decision", "Thanks",
        "Okay, thanks.",
        status="proposed", trust="quarantined", decided_at="2026-06-01T14:09:00Z",
        confidence=0.38,
        source={"id": "s_chat_editor", "type": "chatgpt", "title": "Editor format",
                "locator": "conversation c_editor / message m_12", "quote": "ok thanks!"},
    ),
]

_entries: dict[str, dict] = _seed()
_pending: list[dict] = copy.deepcopy(_CANDIDATES)
_corrections: list[dict] = []


def reset() -> None:
    """Restore the seeded demo state (used by tests and the demo reset)."""
    global _entries, _pending
    _entries = _seed()
    _pending = copy.deepcopy(_CANDIDATES)
    _corrections.clear()


def _get(entry_id: str) -> dict:
    if entry_id not in _entries:
        raise KeyError(entry_id)
    return _entries[entry_id]


def ingest(path: str, kind: str | None = None) -> dict:
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    messages = sum(1 for line in text.splitlines() if line.strip())
    return {"messages": messages, "sources": 1}


def extract(limit: int | None = None) -> list[dict]:
    n = len(_pending) if limit is None else max(0, limit)
    new = _pending[:n]
    del _pending[:n]
    for e in new:
        e["recorded_at"] = _now()
        _entries[e["id"]] = e
    return copy.deepcopy(new)


def list_entries(status: str | None = None, kind: str | None = None,
                 q: str | None = None) -> list[dict]:
    out = list(_entries.values())
    if status:
        out = [e for e in out if e["status"] == status]
    if kind:
        out = [e for e in out if e["kind"] == kind]
    if q:
        ql = q.lower()
        out = [e for e in out if ql in " ".join(
            [e["title"], e["statement"], e["rationale"] or "", e["source"]["quote"]]).lower()]
    out.sort(key=lambda e: e["decided_at"] or "", reverse=True)
    return copy.deepcopy(out)


def review(entry_id: str, action: str, note: str | None = None) -> dict:
    if action not in ("settle", "reject"):
        raise ValueError(f"unknown action: {action}")
    e = _get(entry_id)
    e["status"] = "settled" if action == "settle" else "rejected"
    e["trust"] = "confirmed"
    _corrections.append({"entry_id": entry_id, "action": action, "note": note})
    return copy.deepcopy(e)


def supersede(old_id: str, new_id: str) -> dict:
    old, new = _get(old_id), _get(new_id)
    old["status"] = "superseded"
    old["superseded_by"] = new_id
    new["status"] = "settled"
    return copy.deepcopy(old)


_STOP = {"the", "a", "an", "to", "for", "of", "and", "or", "we", "our", "us", "use", "will",
         "lets", "let's", "let", "is", "be", "with", "on", "in", "not", "no", "it", "this"}


def _words(s: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9']+", s.lower()) if w not in _STOP and len(w) > 2}


def check(text: str) -> dict:
    lowered = text.lower()
    words = _words(text)
    conflicts, related = [], []
    for e in _entries.values():
        if e["status"] != "settled":
            continue
        hit = next((alt for alt in e["alternatives_rejected"] if alt.lower() in lowered), None)
        if hit:
            conflicts.append({
                "entry": copy.deepcopy(e),
                "explanation": f"Proposes {hit}, which was rejected on "
                               f"{e['decided_at'][:10]}: {e['statement']}",
            })
        elif len(words & _words(e["title"] + " " + e["statement"])) >= 2:
            related.append(e)
    verdict = "contradicts" if conflicts else "consistent" if related else "unrelated"
    return {"input": text, "verdict": verdict, "conflicts": conflicts, "model": MODEL}


def feedback_stats() -> dict:
    n = len(_corrections)
    return {
        "corrections": n,
        "precision_before": 0.62,
        "precision_after": round(min(0.95, 0.62 + 0.06 * n), 2),
    }


def sync(path: str = "AGENTS.md") -> str:
    lines = ["<!-- sthira:start -->", "## Settled decisions (from Sthira)"]
    for e in list_entries(status="settled"):
        lines.append(f"- {e['statement']} (source: {e['source']['title']}, "
                     f"{(e['decided_at'] or '')[:10]})")
    lines.append("<!-- sthira:end -->")
    return "\n".join(lines)
