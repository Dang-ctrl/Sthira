"""Check new work against settled entries and return a cited verdict."""

from __future__ import annotations

import re
import sqlite3

from . import config, feedback, llm, store
from .models import Conflict, Entry, Verdict

SYSTEM = """You protect a person's settled decisions. You are given NEW WORK (a plan, prompt, proposal or change)
and a numbered list of SETTLED entries the person already decided.
Decide:
- contradicts: the new work goes against at least one settled entry (e.g. uses an option that was rejected,
  reverses a choice, breaks a stated constraint or preference)
- consistent: the new work follows the settled entries that are relevant
- unrelated: no settled entry is relevant
List every contradicted entry by its number with a one-sentence explanation that names both sides.
Be precise: a different topic is NOT a contradiction.
In explanations, never mention entry numbers; refer to the decision by its content."""

SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["contradicts", "consistent", "unrelated"]},
        "conflicts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"n": {"type": "integer"}, "explanation": {"type": "string"}},
                "required": ["n", "explanation"],
            },
        },
    },
    "required": ["verdict", "conflicts"],
}


CRITIC = """Answer one concrete question about a settled decision and some new work.
Question: does the NEW WORK stop using, migrate away from, remove, or go against what the SETTLED ENTRY chose,
or use an option the settled entry rejected?
- Migrating from the chosen thing to something else: YES.
- Adding the rejected option (even "alongside" the chosen one): YES.
- Doing things in the opposite order the entry requires: YES.
- Keeping the chosen thing and only adding something around it (a cache, an index, a replica, a test): NO.
Do not judge whether the new work is a good idea. Follow any rules the user taught you."""

CRITIC_SCHEMA = {
    "type": "object",
    "properties": {"what_settled_chose": {"type": "string"}, "what_new_work_does": {"type": "string"},
                   "goes_against_settled": {"type": "boolean"}},
    "required": ["what_settled_chose", "what_new_work_does", "goes_against_settled"],
}


def _confirm(entry: Entry, text: str, explanation: str, guidance: str) -> bool:
    """Self-correction pass: re-examine one claimed conflict; drop it if it doesn't hold up."""
    user = (f"SETTLED ENTRY: {entry.statement}" + (f" Reason: {entry.rationale}" if entry.rationale else "")
            + f"\n\nNEW WORK: {text}\n\n"
            + (f"{guidance}\n\n" if guidance else "") + "Does the new work go against the settled entry?")
    try:
        return bool(llm.chat_json(CRITIC, user, CRITIC_SCHEMA).get("goes_against_settled", True))
    except llm.LLMUnavailable:
        raise
    except llm.LLMError:
        return True  # if the critic fails, keep the warning rather than silently drop it


def _tokens(text: str) -> set[str]:
    return {w[:-1] if len(w) > 3 and w.endswith("s") else w for w in re.findall(r"[a-z0-9]+", text.lower())}


def _variants(alt: str) -> list[set[str]]:
    """'Firebase Cloud Messaging (FCM)' matches on the full name or on 'FCM' alone."""
    parts = [alt.split("(")[0], *re.findall(r"\(([^)]*)\)", alt)]
    return [t for t in (_tokens(p) for p in parts) if t]


def candidates(con: sqlite3.Connection, text: str, k: int = 12) -> list[Entry]:
    settled = store.list_entries(con, status="settled")
    if len(settled) <= k:
        return settled
    hits = [e for e in store.list_entries(con, status="settled", q=text)]
    seen = {e.id for e in hits}
    # keep decisions whose rejected alternatives appear in the text even if FTS missed them;
    # match on token subsets so "email+password", "Next.js" or "Firebase Cloud Messaging (FCM)" work too
    words = _tokens(text)
    for e in settled:
        if e.id not in seen and any(any(v <= words for v in _variants(a)) for a in e.alternatives_rejected):
            hits.append(e)
            seen.add(e.id)
    return hits[:k] or settled[:k]


def check(con: sqlite3.Connection, text: str) -> Verdict:
    cands = candidates(con, text)
    if not cands:
        return Verdict(input=text, verdict="unrelated", conflicts=[], model=config.model())
    listing = "\n".join(
        f"[{i}] ({e.kind}, decided {e.decided_at or 'unknown'}) {e.statement}"
        + (f" Reason: {e.rationale}" if e.rationale else "")
        + (f" Rejected: {', '.join(e.alternatives_rejected)}" if e.alternatives_rejected else "")
        for i, e in enumerate(cands)
    )
    guidance = feedback.check_guidance(con)
    # Learned rules sit right before the new work: small models weigh nearby instructions far more.
    user = f"SETTLED:\n{listing}\n\n" + (f"{guidance}\n\n" if guidance else "") + f"NEW WORK:\n{text}"
    data = llm.chat_json(SYSTEM, user, SCHEMA)
    conflicts = []
    for c in data.get("conflicts", []):
        n = c.get("n")
        if isinstance(n, int) and 0 <= n < len(cands):
            explanation = re.sub(r"\s*\[\d+\]", "", c.get("explanation", "")).replace("settled decision states", "decision states")
            if any(x.entry.id == cands[n].id for x in conflicts):
                continue
            if _confirm(cands[n], text, explanation, guidance):
                conflicts.append(Conflict(entry=cands[n], explanation=explanation))
    verdict = data.get("verdict", "unrelated")
    if verdict == "contradicts" and not conflicts:
        verdict = "consistent"
    if conflicts and verdict != "contradicts":
        verdict = "contradicts"
    return Verdict(input=text, verdict=verdict, conflicts=conflicts, model=config.model())
