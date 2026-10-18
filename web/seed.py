"""Export a ledger to JSON and load it into a fresh database (used to seed the hosted demo)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from sthira import store

TABLES = ["sources", "messages", "entries", "feedback", "runs"]


def export(con: sqlite3.Connection, path: Path) -> None:
    data = {t: [dict(r) for r in con.execute(f"SELECT * FROM {t}")] for t in TABLES}
    path.write_text(json.dumps(data, indent=1), encoding="utf-8")


def load(con: sqlite3.Connection, path: Path) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    for t in TABLES:
        for row in data.get(t, []):
            cols = ",".join(row)
            con.execute(f"INSERT OR IGNORE INTO {t}({cols}) VALUES ({','.join('?' * len(row))})", list(row.values()))
    for row in data.get("entries", []):
        con.execute("INSERT INTO entries_fts(id,title,statement,rationale) VALUES (?,?,?,?)",
                    (row["id"], row["title"], row["statement"], row["rationale"]))
    con.commit()
