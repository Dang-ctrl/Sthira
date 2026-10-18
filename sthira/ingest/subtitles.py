"""Subtitle transcripts (.vtt from Zoom/Teams/Meet/Whisper, .srt). Cues become messages; consecutive cues
from the same speaker are merged so a sentence split across cues stays one message."""

from __future__ import annotations

import re
from pathlib import Path

from ..models import Message

_TIME = re.compile(r"(\d{1,2}:)?\d{1,2}:\d{2}[.,]\d{3}\s*-->\s*(\d{1,2}:)?\d{1,2}:\d{2}[.,]\d{3}")
_VOICE = re.compile(r"^<v\s+([^>]+)>(.*?)(?:</v>)?$")          # WebVTT voice tag: <v Ojas>text</v>
_SPEAKER = re.compile(r"^([A-Z][\w .'-]{0,30}?):\s+(.+)$")       # "Ojas: text"
_TAGS = re.compile(r"</?[^>]+>")
_DATE = re.compile(r"(\d{4}-\d{2}-\d{2})")


def parse(text: str, name: str) -> tuple[str, list[Message]]:
    stem = Path(name).stem
    m = _DATE.search(name)
    ts = f"{m.group(1)}T00:00:00Z" if m else None
    out: list[Message] = []
    for block in re.split(r"\n\s*\n", text.replace("\r\n", "\n")):
        lines = [l.strip() for l in block.strip().split("\n") if l.strip()]
        lines = [l for l in lines if not l.isdigit() and not _TIME.search(l) and l != "WEBVTT"
                 and not l.startswith(("NOTE", "STYLE", "Kind:", "Language:"))]
        if not lines:
            continue
        joined = " ".join(lines)
        speaker, body = "speaker", joined
        if vm := _VOICE.match(joined):
            speaker, body = vm.group(1).strip(), vm.group(2)
        elif sm := _SPEAKER.match(joined):
            speaker, body = sm.group(1).strip(), sm.group(2)
        body = _TAGS.sub("", body).strip()
        if not body:
            continue
        if out and out[-1].role == speaker:
            out[-1].text += " " + body
        else:
            out.append(Message(conv_id=stem, conv_title=stem, msg_id=str(len(out)), role=speaker, ts=ts, text=body))
    return stem, out
