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


def candidates(con: sqlite3.Connection, text: str, k: int = 12) -> list[Entry]:
    settled = store.list_entries(con, status="settled")
    if len(settled) <= k:
        return settled
    hits = [e for e in store.list_entries(con, status="settled", q=text)]
    seen = {e.id for e in hits}
    # keep decisions with matching rejected alternatives even if FTS missed them
    kws = set(store.keywords(text, 30))
    for e in settled:
        if e.id not in seen and any(a.lower() in kws for a in e.alternatives_rejected):
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
    system = SYSTEM + ("\n\n" + guidance if guidance else "")
    data = llm.chat_json(system, f"SETTLED:\n{listing}\n\nNEW WORK:\n{text}", SCHEMA)
    conflicts = []
    for c in data.get("conflicts", []):
        n = c.get("n")
        if isinstance(n, int) and 0 <= n < len(cands):
            explanation = re.sub(r"\s*\[\d+\]", "", c.get("explanation", "")).replace("settled decision states", "decision states")
            conflicts.append(Conflict(entry=cands[n], explanation=explanation))
    verdict = data.get("verdict", "unrelated")
    if verdict == "contradicts" and not conflicts:
        verdict = "consistent"
    if conflicts and verdict != "contradicts":
        verdict = "contradicts"
    return Verdict(input=text, verdict=verdict, conflicts=conflicts, model=config.model())
