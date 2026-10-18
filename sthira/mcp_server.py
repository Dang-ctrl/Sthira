"""MCP server: lets any AI tool read your settled context and check its plans against it."""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from . import api

server = MCPServer(
    name="sthira",
    instructions=(
        "Sthira holds what the user has already decided. Before proposing a significant change (architecture, "
        "libraries, data stores, product direction), call `check` with your plan. If it contradicts a settled "
        "decision, stop and ask the user instead of proceeding. When the user makes a new decision, call `propose`."
    ),
)


def _fmt(e) -> str:
    when = (e.decided_at or "")[:10]
    why = f" Because: {e.rationale}" if e.rationale else ""
    return f"[{e.kind}] {e.statement}{why} (source: {e.source.title}, {when}; id {e.id})"


@server.tool(description="List the user's settled decisions, preferences and commitments, optionally filtered by topic.")
def get_settled(topic: str = "") -> str:
    entries = api.list_entries(status="settled", q=topic or None)
    return "\n".join(_fmt(e) for e in entries) or "No settled entries match."


@server.tool(description="List open questions the user has NOT decided yet. Ask the user rather than assuming.")
def open_questions() -> str:
    entries = [e for e in api.list_entries(kind="open_question") if e.status in ("settled", "proposed")]
    return "\n".join(_fmt(e) for e in entries) or "No open questions."


@server.tool(description="Check a plan, proposal or change against the user's settled decisions. Returns a verdict with cited sources.")
def check(plan: str) -> str:
    v = api.check(plan)
    if v.verdict != "contradicts":
        return f"{v.verdict}: no conflict with settled decisions."
    lines = ["CONTRADICTS settled decisions. Stop and ask the user before proceeding:"]
    for c in v.conflicts:
        lines.append(f"- {_fmt(c.entry)}\n  quote: \"{c.entry.source.quote}\"\n  why: {c.explanation}")
    return "\n".join(lines)


@server.tool(description="Record a new decision the user just made. It stays 'proposed' until the user confirms it in Sthira.")
def propose(statement: str, rationale: str = "", kind: str = "decision") -> str:
    e = api.propose(statement, kind=kind, rationale=rationale, source_title="via MCP")
    return f"Recorded as proposed ({e.id}). The user can confirm it with `sthira review`."


def main() -> None:
    server.run("stdio")


if __name__ == "__main__":
    main()
