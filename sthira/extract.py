"""Pull decisions (and other settled-context entries) out of raw messages with a local open-weight model."""

from __future__ import annotations

import difflib
import re
import sqlite3

from . import config, feedback, llm, store
from .models import Entry, SourceRef

CHUNK_CHARS = 12000  # ~3k tokens; long transcripts lose decisions without chunking

SYSTEM = """You extract durable, settled context from a person's conversations with AI assistants and colleagues.
Record ONLY items the person would want every future AI assistant to respect:
- decision: a choice that was made ("we'll use X", "go with Y", "let's not do Z"), ideally with its reason
- open_question: an important question raised but explicitly left unresolved
- preference: a stable personal or project preference ("always use British spelling")
- commitment: a promise with an owner ("Danica will draft the copy by Friday")
- lesson: something tried that failed or worked, worth remembering
- assumption: a stated premise a decision depends on
Rules:
- If the person explicitly leaves something undecided ("let's revisit", "can't decide yet"), it is an open_question, not a decision.
- Write statements about the project, not about "the user" or "the assistant" (e.g. "Login uses magic links only").
- Most messages contain NOTHING worth recording. Returning an empty list is normal and correct.
- Do not record suggestions the assistant made unless the user accepted them.
- Do not record greetings, thanks, brainstorming that was not chosen, or questions that were answered.
- `quote` MUST be copied verbatim from one message (a short span, under 200 characters).
- `msg` is the [number] of the message containing the quote.
- Write `statement` as one clear, self-contained sentence; `title` as a short label (max 8 words)."""

SCHEMA = {
    "type": "object",
    "properties": {
        "entries": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "kind": {"type": "string", "enum": ["decision", "open_question", "preference", "commitment", "lesson", "assumption"]},
                    "title": {"type": "string"},
                    "statement": {"type": "string"},
                    "rationale": {"type": "string"},
                    "alternatives_rejected": {"type": "array", "items": {"type": "string"}},
                    "quote": {"type": "string"},
                    "msg": {"type": "integer"},
                    "confidence": {"type": "number"},
                },
                "required": ["kind", "title", "statement", "rationale", "alternatives_rejected", "quote", "msg", "confidence"],
            },
        }
    },
    "required": ["entries"],
}


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.lower()).strip()


def _quote_found(quote: str, text: str) -> bool:
    q, t = _norm(quote).strip(" .\"'"), _norm(text)
    if not q:
        return False
    if q in t:
        return True
    # tolerate small paraphrase drift from small models
    sm = difflib.SequenceMatcher(None, q, t)
    m = sm.find_longest_match(0, len(q), 0, len(t))
    return m.size >= max(20, int(len(q) * 0.7))


def _chunks(messages: list[dict]) -> list[list[dict]]:
    out, cur, size = [], [], 0
    for m in messages:
        n = len(m["text"])
        if cur and size + n > CHUNK_CHARS:
            out.append(cur)
            cur, size = [], 0
        cur.append(m)
        size += n
    if cur:
        out.append(cur)
    return out


def _is_duplicate(con: sqlite3.Connection, statement: str) -> bool:
    for e in store.list_entries(con, q=statement):
        if e.status == "rejected":
            continue
        if difflib.SequenceMatcher(None, _norm(e.statement), _norm(statement)).ratio() > 0.82:
            return True
    return False


def extract(con: sqlite3.Connection, limit: int | None = None, on_progress=None,
            source_ids: list[str] | None = None) -> list[Entry]:
    convs = store.pending_conversations(con, source_ids)
    if limit:
        convs = convs[:limit]
    run_id = store.start_run(con, "extract")
    guidance = feedback.extraction_guidance(con)
    created: list[Entry] = []
    for ci, conv in enumerate(convs):
        for chunk in _chunks(conv["messages"]):
            if on_progress:
                on_progress(ci + 1, len(convs), conv["conv_title"])
            listing = "\n\n".join(
                f"[{i}] {m['role']} ({m['ts'] or 'undated'}): {m['text'][:4000]}" for i, m in enumerate(chunk)
            )
            user = f"Conversation: {conv['conv_title']}\n\n{listing}"
            system = SYSTEM + ("\n\n" + guidance if guidance else "")
            try:
                data = llm.chat_json(system, user, SCHEMA)
            except llm.LLMUnavailable:
                raise  # nothing will work until the server is back; don't report "nothing new"
            except llm.LLMError:
                continue
            for item in data.get("entries", []):
                idx = item.get("msg", -1)
                msg = chunk[idx] if isinstance(idx, int) and 0 <= idx < len(chunk) else None
                # Self-check: the quote must really exist in the source, otherwise it's a hallucination.
                if msg is None or not _quote_found(item.get("quote", ""), msg["text"]):
                    msg = next((m for m in chunk if _quote_found(item.get("quote", ""), m["text"])), None)
                if msg is None or not item.get("statement"):
                    continue
                if _is_duplicate(con, item["statement"]):
                    continue
                entry = Entry(
                    id=store.new_id("e"),
                    kind=item.get("kind", "decision"),
                    title=item.get("title", "")[:120] or item["statement"][:60],
                    statement=item["statement"],
                    rationale=item.get("rationale", ""),
                    alternatives_rejected=[a for a in item.get("alternatives_rejected", []) if a][:5],
                    status="proposed",
                    trust="quarantined",
                    decided_at=msg["ts"],
                    recorded_at=store.now(),
                    source=SourceRef(
                        id=msg["source_id"], type=conv["source_type"], title=conv["conv_title"],
                        locator=f"{conv['conv_id']} / {msg['msg_id']}", quote=item.get("quote", "")[:300],
                    ),
                    confidence=float(item.get("confidence") or 0.5),
                )
                created.append(store.insert_entry(con, entry, run_id))
            store.mark_extracted(con, [m["id"] for m in chunk])
    return created


def model_name() -> str:
    return config.model()
