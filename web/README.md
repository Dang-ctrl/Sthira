# web/: Sthira API and demo UI

FastAPI app serving the HTTP API from [`docs/CONTRACTS.md`](../docs/CONTRACTS.md) plus a single-page UI (ledger, check, review, ingest/extract).

It uses the real `sthira.api` when it can be imported. Until the core engine lands it falls back to `web/fake_api.py`, an in-memory stand-in seeded with the Acme Notes demo story (no model calls; `check` is a keyword matcher). Set `STHIRA_FAKE=1` to force the fake. The UI shows a "demo data" pill while the fake is active.

## Run

From the repo root:

```bash
uv run --with-requirements web/requirements.txt uvicorn web.app:app --reload
```

or with a plain venv: `pip install -r web/requirements.txt && uvicorn web.app:app --reload`. Then open http://localhost:8000. Tests: `pytest -q web/tests`.

## Files
- `app.py`: routes; converts Pydantic/dataclass results from the core to JSON.
- `fake_api.py`: in-memory `sthira.api` with the same signatures.
- `static/`: `index.html`, `style.css`, `app.js` (vanilla JS, no build step).
