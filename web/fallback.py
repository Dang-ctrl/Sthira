"""Model-free check used only when the hosted model is unreachable.

It flags text that names an alternative a settled decision explicitly rejected
(e.g. "MongoDB" against "use Postgres, not MongoDB"). It can't judge anything
subtler, so it never claims "consistent" or "unrelated": no match means no verdict.
Results are labelled so nobody mistakes them for a model verdict.
"""

from __future__ import annotations

import re

from sthira.models import Conflict, Entry, Verdict

LABEL = "keyword match (hosted model offline; not a model verdict)"
_STOP = {"the", "a", "an", "and", "or", "of", "to", "for", "with", "use", "using"}


def _tokens(text: str) -> set[str]:
    out = set()
    for w in re.findall(r"[a-z0-9]+", text.lower()):
        if w in _STOP:
            continue
        out.add(w[:-1] if len(w) > 3 and w.endswith("s") else w)
    return out


def _variants(alt: str) -> list[set[str]]:
    # "Firebase Cloud Messaging (FCM)" matches on the full name or on "FCM" alone.
    parts = [alt.split("(")[0], *re.findall(r"\(([^)]*)\)", alt)]
    return [t for t in (_tokens(p) for p in parts) if t]


def normalize(text: str) -> str:
    return " ".join(text.lower().split())


def keyword_check(text: str, settled: list[Entry]) -> Verdict | None:
    words = _tokens(text)
    conflicts = []
    for e in settled:
        hit = next((alt for alt in e.alternatives_rejected
                    if any(v <= words for v in _variants(alt))), None)
        if hit:
            conflicts.append(Conflict(
                entry=e,
                explanation=f"This mentions “{hit}”, which was explicitly rejected when you decided: {e.statement}",
            ))
    if not conflicts:
        return None
    return Verdict(input=text, verdict="contradicts", conflicts=conflicts, model=LABEL)
