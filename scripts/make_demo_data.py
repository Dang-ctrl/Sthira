"""Generate the 'Acme Notes' demo dataset in real export formats.

Writes:
  demo/chatgpt/export-march.json   ChatGPT conversations.json format (batch 1)
  demo/chatgpt/export-june.json    ChatGPT conversations.json format (batch 2, later export)
  demo/meetings/2026-05-12-standup.md
  demo/claude_code/session.jsonl   today's coding session where the agent drifts
  eval/gold.json                   what a human would actually want recorded
Run: uv run python scripts/make_demo_data.py
"""

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def ts(s: str) -> float:
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp()


def conv(cid: str, title: str, when: str, turns: list[tuple[str, str]]) -> dict:
    t0 = ts(when)
    mapping = {f"{cid}-root": {"id": f"{cid}-root", "message": None, "parent": None, "children": []}}
    parent = f"{cid}-root"
    for i, (role, text) in enumerate(turns):
        nid = f"{cid}-{i}"
        mapping[nid] = {"id": nid, "parent": parent, "children": [], "message": {
            "id": nid, "author": {"role": role}, "create_time": t0 + i * 90,
            "content": {"content_type": "text", "parts": [text]}}}
        mapping[parent]["children"].append(nid)
        parent = nid
    return {"id": cid, "conversation_id": cid, "title": title, "create_time": t0, "current_node": parent, "mapping": mapping}


MARCH = [
    conv("acme-db", "Acme Notes: database choice", "2026-03-04T10:00:00", [
        ("user", "I'm starting Acme Notes, a collaborative note-taking app. Postgres or MongoDB for the user store?"),
        ("assistant", "Both can work. MongoDB gives schema flexibility; Postgres gives relational integrity, joins and mature tooling. What do your access patterns look like?"),
        ("user", "Users belong to orgs, orgs share notebooks, notebooks have permissions per user. Lots of joins."),
        ("assistant", "That's strongly relational. Postgres fits well; with MongoDB you'd end up re-implementing joins in application code."),
        ("user", "Ok, decided: we go with Postgres, not MongoDB. We need joins across users, orgs and notebooks."),
        ("assistant", "Great. I'll sketch the schema with users, orgs, memberships and notebooks tables."),
    ]),
    conv("acme-cat", "Cat names", "2026-03-06T21:00:00", [
        ("user", "random question, what's a cute name for a grey kitten?"),
        ("assistant", "How about Miso, Pebble or Ash?"),
        ("user", "haha Miso is perfect, thanks!"),
    ]),
    conv("acme-auth", "Acme Notes: login flow", "2026-03-09T11:30:00", [
        ("user", "For Acme Notes login, should I do email+password, OAuth, or magic links?"),
        ("assistant", "Magic links remove password resets and credential stuffing risk. OAuth is convenient but adds provider dependencies. Passwords are familiar but costly to support."),
        ("user", "Password resets were half our support tickets at my last job. Let's do magic links only, no passwords."),
        ("assistant", "Makes sense. I'll plan an email magic-link flow with 15 minute expiry."),
    ]),
    conv("acme-crdt", "Explain CRDTs", "2026-03-15T09:00:00", [
        ("user", "Can you explain CRDTs simply?"),
        ("assistant", "CRDTs are data structures that let multiple replicas edit independently and merge without conflicts, like a shared counter that only adds."),
        ("user", "nice, and how is that different from operational transforms?"),
        ("assistant", "OT transforms concurrent operations against each other through a central server; CRDTs merge by design without coordination."),
    ]),
    conv("acme-pricing", "Acme Notes: pricing", "2026-03-20T16:00:00", [
        ("user", "Thinking about pricing for Acme Notes. Monthly at $8 or annual at $80?"),
        ("assistant", "Annual improves cash flow and retention; monthly lowers the barrier. Many offer both."),
        ("user", "I honestly can't decide yet. Let's leave pricing open until we have beta users and revisit."),
        ("assistant", "Sounds reasonable. You can gather willingness-to-pay data during beta."),
    ]),
]

JUNE = [
    conv("acme-frontend", "Acme Notes: frontend stack", "2026-04-02T10:00:00", [
        ("user", "Frontend for Acme Notes: React with Next.js or SvelteKit?"),
        ("assistant", "Next.js has the bigger ecosystem; SvelteKit is lighter and simpler. Which does your team know?"),
        ("user", "The whole team knows Svelte already. We'll use SvelteKit, not Next.js. And always TypeScript in strict mode."),
        ("assistant", "Got it. SvelteKit with strict TypeScript."),
    ]),
    conv("acme-trip", "Weekend in Coorg", "2026-04-11T08:00:00", [
        ("user", "Planning a weekend trip to Coorg, any tips?"),
        ("assistant", "Visit Abbey Falls early, try a coffee estate stay, and carry a light jacket."),
        ("user", "thanks, sounds lovely!"),
    ]),
    conv("acme-push", "Acme Notes: push notifications", "2026-05-20T14:00:00", [
        ("user", "We tried Firebase Cloud Messaging for push in the beta and it was really flaky on iOS. Alternatives?"),
        ("assistant", "You could use APNs directly for iOS, or a service like OneSignal."),
        ("user", "Lesson learned: don't rely on FCM for iOS. Let's use APNs directly for iOS push."),
        ("assistant", "Ok, APNs for iOS, and you can keep FCM for Android."),
    ]),
    conv("acme-poem", "Poem for mom", "2026-05-25T19:00:00", [
        ("user", "write a short poem for my mom's birthday"),
        ("assistant", "Roses bloom where you have walked, your kindness is the light we talk..."),
        ("user", "aww she'll love it, thank you"),
    ]),
]

STANDUP = """# Acme Notes standup 2026-05-12

Ojas: Quick sync. Web beta is stable, mobile is half done.
Vidit: If we split focus we'll ship both late.
Ojas: Agreed. Decision: we ship the web app first and the mobile app after web is stable.
Danica: I'll draft the onboarding copy by Friday.
Vidit: Also, weekly standups move to Mondays at 10.
Ojas: Sounds good. Anything else? No? Thanks all.
"""

SESSION_TODAY = [
    ("user", "The notes search is slow. Can you look at the user store and fix performance?"),
    ("assistant", "I looked at the queries. Joins between users, orgs and notebooks are the bottleneck. Plan: migrate the user store from Postgres to MongoDB and denormalize memberships into the user document so we avoid joins."),
    ("user", "hmm ok, also add a 'forgot password' page while you're at it"),
    ("assistant", "Sure. I'll add email+password login with a forgot-password reset flow alongside the existing login."),
]

GOLD = [
    {"kind": "decision", "keywords": ["postgres"], "statement": "Use Postgres, not MongoDB, for the user store (joins across users, orgs, notebooks)."},
    {"kind": "decision", "keywords": ["magic"], "statement": "Login uses magic links only; no passwords."},
    {"kind": "open_question", "keywords": ["pricing"], "statement": "Pricing (monthly vs annual) is undecided until beta."},
    {"kind": "decision", "keywords": ["sveltekit"], "statement": "Use SvelteKit, not Next.js."},
    {"kind": "preference", "keywords": ["typescript"], "statement": "Always TypeScript in strict mode."},
    {"kind": "lesson", "keywords": ["fcm|firebase"], "statement": "FCM was flaky for iOS push; don't rely on it for iOS."},
    {"kind": "decision", "keywords": ["apns"], "statement": "Use APNs directly for iOS push."},
    {"kind": "decision", "keywords": ["mobile"], "statement": "Ship web first, mobile after web is stable."},
    {"kind": "commitment", "keywords": ["onboarding"], "statement": "Danica drafts onboarding copy by Friday."},
    {"kind": "decision", "keywords": ["monday|standup"], "statement": "Weekly standups move to Mondays at 10."},
]


def main():
    (ROOT / "demo/chatgpt").mkdir(parents=True, exist_ok=True)
    (ROOT / "demo/meetings").mkdir(parents=True, exist_ok=True)
    (ROOT / "demo/claude_code").mkdir(parents=True, exist_ok=True)
    (ROOT / "eval").mkdir(parents=True, exist_ok=True)
    (ROOT / "demo/chatgpt/export-march.json").write_text(json.dumps(MARCH, indent=1), encoding="utf-8")
    (ROOT / "demo/chatgpt/export-june.json").write_text(json.dumps(JUNE, indent=1), encoding="utf-8")
    (ROOT / "demo/meetings/2026-05-12-standup.md").write_text(STANDUP, encoding="utf-8")
    lines = []
    for i, (role, text) in enumerate(SESSION_TODAY):
        content = text if role == "user" else [{"type": "text", "text": text}]
        lines.append(json.dumps({"type": role, "sessionId": "acme-perf-2026-10-18", "uuid": f"cc-{i}",
                                 "timestamp": f"2026-10-18T09:{10 + i:02d}:00Z",
                                 "message": {"role": role, "content": content}}))
    (ROOT / "demo/claude_code/session.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (ROOT / "eval/gold.json").write_text(json.dumps(GOLD, indent=1), encoding="utf-8")
    print("demo data written")


if __name__ == "__main__":
    main()
