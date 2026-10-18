from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Kind = Literal["decision", "open_question", "preference", "commitment", "lesson", "assumption"]
Status = Literal["proposed", "settled", "rejected", "superseded"]
Trust = Literal["confirmed", "quarantined"]
SourceType = Literal["chatgpt", "claude_code", "transcript"]


class Message(BaseModel):
    """One normalized message from any source."""

    conv_id: str
    conv_title: str = ""
    msg_id: str
    role: str
    ts: str | None = None
    text: str


class SourceRef(BaseModel):
    id: str
    type: str
    title: str = ""
    locator: str = ""
    quote: str = ""


class Entry(BaseModel):
    id: str
    kind: Kind
    title: str
    statement: str
    rationale: str = ""
    alternatives_rejected: list[str] = Field(default_factory=list)
    project: str = ""
    status: Status = "proposed"
    trust: Trust = "quarantined"
    superseded_by: str | None = None
    decided_at: str | None = None
    recorded_at: str
    source: SourceRef
    confidence: float = 0.5


class Conflict(BaseModel):
    entry: Entry
    explanation: str


class Verdict(BaseModel):
    input: str
    verdict: Literal["contradicts", "consistent", "unrelated", "supersedes"]
    conflicts: list[Conflict] = Field(default_factory=list)
    model: str
