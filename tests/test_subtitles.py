"""Split out of test_core.py so feature branches don't collide."""

import json
from pathlib import Path

from sthira import store, sync
from sthira.ingest import parse_bytes
from sthira.models import Entry, SourceRef

FIX = Path(__file__).parent / "fixtures"


def _entry(statement, status="settled"):
    return Entry(id=store.new_id("e"), kind="decision", title=statement[:20], statement=statement, status=status,
                 trust="confirmed", decided_at="2026-03-04T00:00:00Z", recorded_at=store.now(),
                 source=SourceRef(id="s", type="chatgpt", title="DB choice", quote=statement))


def test_vtt_voice_tags_and_merging():
    vtt = """WEBVTT

1
00:00:01.000 --> 00:00:04.000
<v Ojas>We ship the web app first,</v>

2
00:00:04.000 --> 00:00:06.500
<v Ojas>mobile after web is stable.</v>

3
00:00:07.000 --> 00:00:09.000
<v Danica>I'll draft the onboarding copy by Friday.</v>
"""
    [(src, _, _, msgs)] = parse_bytes("2026-05-12-standup.vtt", vtt.encode())
    assert src == "transcript" and [m.role for m in msgs] == ["Ojas", "Danica"]
    assert msgs[0].text == "We ship the web app first, mobile after web is stable."
    assert msgs[0].ts == "2026-05-12T00:00:00Z"


def test_srt_speaker_prefix():
    srt = "1\n00:00:01,000 --> 00:00:03,000\nVidit: Standups move to Mondays at 10.\n\n2\n00:00:03,500 --> 00:00:05,000\nno speaker label here\n"
    [(_, _, _, msgs)] = parse_bytes("sync.srt", srt.encode())
    assert msgs[0].role == "Vidit" and msgs[0].text == "Standups move to Mondays at 10."
    assert msgs[1].role == "speaker"
