"""Scripted end-to-end demo that proves the self-correction loop (problem statement O2).

Phase 1: ingest the March export, extract, and review against gold labels (simulated user).
Phase 2: ingest later data; extraction now uses the learned corrections, so precision changes.
Phase 3: scan today's Claude Code session and catch the agent undoing settled decisions.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from . import api, store

ROOT = Path(__file__).resolve().parent.parent


def load_gold(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def matches(entry, gold_item) -> bool:
    """A gold item matches when every keyword (each may list `a|b` alternatives) appears in the entry."""
    text = f"{entry.title} {entry.statement}".lower()
    return all(any(re.search(rf"\b{re.escape(alt)}", text) for alt in kw.split("|")) for kw in gold_item["keywords"])


def auto_review(con, gold: list[dict], matched: set[int]) -> dict:
    """Simulated human review: settle what matches a gold item, reject the rest (that's what teaches Sthira)."""
    settled = rejected = 0
    for e in store.list_entries(con, status="proposed"):
        hit = next((i for i, g in enumerate(gold) if i not in matched and matches(e, g)), None)
        if hit is not None:
            matched.add(hit)
            api.review(e.id, "settle", con=con)
            settled += 1
        else:
            api.review(e.id, "reject", "Only record things about the person's projects or work. Personal life (pets, trips, gifts, poems) and explanations of concepts are not decisions.", con=con)
            rejected += 1
    total = settled + rejected
    return {"proposed": total, "settled": settled, "rejected": rejected,
            "precision": round(settled / total, 2) if total else None}


def run(db: Path, data_dir: Path | None = None, say=print) -> dict:
    data_dir = data_dir or ROOT / "demo"
    gold = load_gold((data_dir.parent / "eval" / "gold.json") if (data_dir.parent / "eval" / "gold.json").exists()
                     else ROOT / "eval" / "gold.json")
    if db.exists():
        db.unlink()
    con = store.connect(db)
    matched: set[int] = set()
    out: dict = {}

    say("Phase 1: March export (no corrections yet)")
    api.ingest(str(data_dir / "chatgpt" / "export-march.json"), con=con)
    api.extract(con=con)
    out["phase1"] = auto_review(con, gold, matched)
    say(f"  {out['phase1']}")

    say("Phase 2: June export + standup transcript (Sthira now uses the corrections)")
    api.ingest(str(data_dir / "chatgpt" / "export-june.json"), con=con)
    api.ingest(str(data_dir / "meetings"), con=con)
    api.extract(con=con)
    out["phase2"] = auto_review(con, gold, matched)
    say(f"  {out['phase2']}")

    out["recall"] = round(len(matched) / len(gold), 2)
    out["stats"] = api.feedback_stats(con=con)
    say(f"  recall vs gold: {out['recall']}  stats: {out['stats']}")

    say("Phase 3: today's Claude Code session")
    out["scan"] = [
        {"message": r["text"][:120], "verdict": r["verdict"].verdict,
         "conflicts": [c.entry.statement for c in r["verdict"].conflicts]}
        for r in api.scan(str(data_dir / "claude_code" / "session.jsonl"), con=con)
    ]
    for r in out["scan"]:
        say(f"  {r['verdict']}: {r['message']}  ->  {r['conflicts']}")
    return out
