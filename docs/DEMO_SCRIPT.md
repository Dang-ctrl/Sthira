# 2-minute demo script (judging)

**Setup before judges arrive:** the live URL is open in one tab. A terminal is open in the repo with `qwen3:4b` loaded (run `ollama run qwen3:4b "hi"` once to warm it up). Optionally, Claude Code is open with the Sthira MCP and hook configured.

## 0:00 The problem (15s)
"We all make decisions with AI now, across ChatGPT, Claude and coding agents. Weeks later an agent cheerfully undoes one, because nothing remembers what was settled, or why. Platform memories are siloed, and none of them track decisions."

## 0:15 What Sthira is (15s)
"Sthira (Sanskrit for *steady*) reads your AI history, extracts the decisions you made with their reasons and a verbatim quote, and keeps them in a local ledger. It runs entirely on an open-weight model, Qwen3, on your laptop."
*Show the ledger panel: a decision, its quote, its source chat and date.*

## 0:30 The moment (30s)
"Here's a Claude Code session from today. The agent wants to migrate our user store to MongoDB."
*Click the **Migrate the user store…** chip, or in the terminal run `uv run sthira scan demo/claude_code/session.jsonl`.*
"Sthira catches it: this contradicts what we decided on 4 March, and here's the exact sentence from that chat. It also caught the agent adding password login, which we ruled out."

## 1:00 It learns (O2: memory and self-correction) (35s)
"Small models make mistakes. In the first pass it logged '*we named the kitten Miso*' as a decision."
*Show the Rejected tab, or the `sthira demo` output.*
"When we reject something, with a reason, that reason becomes a rule for every future run. Extraction precision went from 40% to 57% (most recently 60% → …) after one round of corrections, and you can reproduce it with `sthira demo`."
*Point at the stats tile: corrections learned and precision before → after.*
"And if a contradiction warning is wrong, you click 'teach Sthira', and future checks adapt."

## 1:35 Every agent sees it (15s)
"`sthira sync` writes the settled decisions into AGENTS.md, and the MCP server lets Claude Code, Cursor or any agent call `check` before acting."
*Show the "Every agent sees it" panel.*

## 1:50 Close (10s)
"Open source, MIT, local-first, open-weight. Nothing is ever deleted, only superseded, and every entry cites its source. Sthira: your AI forgets what you decided. Sthira doesn't."

## Likely judge questions
- **Why not just use ChatGPT/Claude memory?** Those are siloed per vendor, can't be read by other tools, and none treat decisions, reasons or contradictions as first-class. Sthira is cross-tool and yours.
- **How do you stop hallucinated memories?** Every extracted quote must exist verbatim in the source, otherwise it's dropped. New entries are held as *quarantined* until a human settles them.
- **Memory poisoning?** Same answer: nothing becomes settled without human confirmation, and every entry keeps its provenance.
- **How is this different from Mem0 or other memory layers?** They store facts about you. Sthira stores *decisions with reasons and history*, and checks new work against them.
- **Why open-weight?** Your AI history is private. A 4B model on a laptop is enough to read it, so nothing leaves your machine.
