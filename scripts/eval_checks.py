"""Run the contradiction-check cases in eval/check_cases.json against a ledger (default: the `sthira demo` DB).

uv run python scripts/eval_checks.py [path/to/ledger.db]
"""

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault("STHIRA_DB", sys.argv[1] if len(sys.argv) > 1 else str(Path.home() / ".sthira" / "demo.db"))

from sthira import api, config  # noqa: E402

cases = json.loads((ROOT / "eval" / "check_cases.json").read_text(encoding="utf-8"))
ok_n = 0
for c in cases:
    t0 = time.time()
    v = api.check(c["text"])
    ok = (v.verdict == "contradicts") == (c["expect"] == "contradicts")
    ok_n += ok
    print(f"{'OK ' if ok else 'BAD'} {v.verdict:12} {time.time() - t0:5.1f}s  {c['text'][:70]}")
print(f"{ok_n}/{len(cases)} correct with {config.model()}")
