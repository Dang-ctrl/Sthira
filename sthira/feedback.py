"""Self-correction: user corrections become guidance for future extraction and checks."""

from __future__ import annotations

import sqlite3


def extraction_guidance(con: sqlite3.Connection, limit: int = 6) -> str:
    """Few-shot guidance built from what the user previously rejected and accepted."""
    rows = con.execute(
        """SELECT f.action, f.note, e.kind, e.title, e.statement FROM feedback f
           JOIN entries e ON e.id = f.entry_id
           WHERE f.target = 'extraction' ORDER BY f.created_at DESC LIMIT 40"""
    ).fetchall()
    rejected = [r for r in rows if r["action"] == "reject"][:limit]
    accepted = [r for r in rows if r["action"] == "settle"][:limit]
    if not rejected and not accepted:
        return ""
    lines = ["Learn from the user's past corrections:"]
    if rejected:
        lines.append("The user REJECTED these as not worth recording. Do NOT extract similar items:")
        for r in rejected:
            why = f" (user note: {r['note']})" if r["note"] else ""
            lines.append(f"- [{r['kind']}] {r['statement']}{why}")
    if accepted:
        lines.append("The user CONFIRMED these as correct. Extract items like these:")
        for r in accepted:
            lines.append(f"- [{r['kind']}] {r['statement']}")
    return "\n".join(lines)


def check_guidance(con: sqlite3.Connection, limit: int = 6) -> str:
    rows = con.execute(
        "SELECT note, snippet FROM feedback WHERE target = 'check' ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    if not rows:
        return ""
    lines = ["The user corrected earlier verdicts. Apply these lessons:"]
    for r in rows:
        lines.append(f"- For input like \"{(r['snippet'] or '')[:160]}\": {r['note']}")
    return "\n".join(lines)


def stats(con: sqlite3.Connection) -> dict:
    """Extraction precision on runs before vs after the user started giving feedback."""
    rows = con.execute(
        """SELECT r.feedback_count > 0 AS learned, e.status FROM entries e JOIN runs r ON r.id = e.run_id
           WHERE r.kind = 'extract' AND e.status IN ('settled','rejected','superseded')"""
    ).fetchall()

    def precision(flag: int):
        rel = [r for r in rows if r["learned"] == flag]
        if not rel:
            return None
        good = sum(1 for r in rel if r["status"] in ("settled", "superseded"))
        return round(good / len(rel), 2)

    counts = {r["status"]: r["n"] for r in con.execute("SELECT status, COUNT(*) n FROM entries GROUP BY status")}
    corrections = con.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]
    return {
        "corrections": corrections,
        "precision_before": precision(0),
        "precision_after": precision(1),
        "entries": counts,
    }
