"""ChatGPT (`conversations.json` with a node `mapping`) and Claude.ai (`chat_messages`) exports."""

from __future__ import annotations

from datetime import datetime, timezone

from ..models import Message


def _iso(ts) -> str | None:
    if ts is None or ts == "":
        return None
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return str(ts)


def _chatgpt_conv(conv: dict) -> list[Message]:
    mapping = conv.get("mapping") or {}
    conv_id = conv.get("conversation_id") or conv.get("id") or conv.get("title", "conv")
    title = conv.get("title") or ""
    # Follow the active branch from current_node back to the root; fall back to all nodes by time.
    chain: list[dict] = []
    node_id = conv.get("current_node")
    seen = set()
    while node_id and node_id in mapping and node_id not in seen:
        seen.add(node_id)
        chain.append(mapping[node_id])
        node_id = mapping[node_id].get("parent")
    chain.reverse()
    if not chain:
        chain = sorted(mapping.values(), key=lambda n: ((n.get("message") or {}).get("create_time") or 0))
    out: list[Message] = []
    for node in chain:
        m = node.get("message")
        if not m:
            continue
        role = (m.get("author") or {}).get("role", "")
        if role not in {"user", "assistant"}:
            continue
        parts = (m.get("content") or {}).get("parts") or []
        text = "\n".join(p for p in parts if isinstance(p, str)).strip()
        if not text:
            continue
        out.append(Message(conv_id=str(conv_id), conv_title=title, msg_id=str(m.get("id") or node.get("id")),
                           role=role, ts=_iso(m.get("create_time") or conv.get("create_time")), text=text))
    return out


def _claude_ai_conv(conv: dict) -> list[Message]:
    out = []
    conv_id = conv.get("uuid") or conv.get("name", "conv")
    for i, m in enumerate(conv.get("chat_messages") or []):
        text = m.get("text") or "\n".join(c.get("text", "") for c in (m.get("content") or []) if isinstance(c, dict))
        if not text.strip():
            continue
        role = "user" if m.get("sender") == "human" else "assistant"
        out.append(Message(conv_id=str(conv_id), conv_title=conv.get("name") or "", msg_id=str(m.get("uuid") or i),
                           role=role, ts=_iso(m.get("created_at")), text=text.strip()))
    return out


def parse(obj) -> tuple[str, list[Message]]:
    convs = obj if isinstance(obj, list) else [obj]
    msgs: list[Message] = []
    src = "chatgpt"
    for c in convs:
        if not isinstance(c, dict):
            continue
        if "chat_messages" in c:
            src = "claude_ai"
            msgs.extend(_claude_ai_conv(c))
        elif "mapping" in c:
            msgs.extend(_chatgpt_conv(c))
    return src, msgs
