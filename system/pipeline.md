# Pipeline

The content pipeline is a 10-state machine, executed by **one LLM agent** (the `team/post.md` slash command) with no subagents and no nesting. The LLM runs all 10 steps inline in your chat.

```
IDLE → SESSION_CAPTURE → COMPILE → SELECT → DRAFTING → BANNER → GATE_CHECK → PUBLISHING → ANALYZING_POST → COMPLETE_POST → IDLE
```

## The 10 states

| # | State | What happens | Tools used |
|---|---|---|---|
| 0 | IDLE | Awaiting `/post` | — |
| 1 | SESSION_CAPTURE | Capture source (session from opencode DB or topic text). Classify. | `tools/researcher.py` (bash) |
| 2 | COMPILE | Run 8-step (session) or 6-question (topic) compiler. Extract 6 axis meanings + 1 core insight. | read `system/prompts/compiler.md` |
| 3 | SELECT | Rank templates from registry. Top 3 per platform. | read `templates/registry/viral-templates.yaml` |
| 4 | DRAFTING | Ask user for platforms. Write drafts with 15-field frontmatter. Apply 14 soft-gate self-check. | `question` tool, `write` tool |
| 5 | BANNER | Render PNG banners. | `tools/designer.py` (bash) |
| 6 | GATE_CHECK | Run 15 mechanical gates. Apply 14 soft review. | `tools/editor.py` (bash) |
| 7 | PUBLISHING | Per-draft p/h/r wizard. Dispatch via Buffer / direct API / GH Pages. Archive. | `question` tool, `tools/publisher/*` (bash) |
| 8 | ANALYZING_POST | Pull engagement. Update perf ledger. Re-rank templates. | `tools/analyst.py` (bash) |
| 9 | COMPLETE_POST | Archive brief. Back to IDLE. | bash mv |

## Architecture

**One agent. One prompt. One conversation.**

When you type `/post`:
1. The IDE runs the `team/post.md` slash command in your chat.
2. The slash command's body is the full 10-step procedure.
3. The LLM executes each step inline using `bash`, `read`, `write`, and `question` tools.
4. No `task()` calls, no subagent dispatch, no nested contexts.

You see every step in your chat. There is exactly one conversation.

## The handoff file: `.brief.md`

One `.brief.md` per `/post` run. The LLM writes to it via the `write` tool at each step. Archived to `content/.brief/YYYY-MM-DD-NNN.md` on Step 10.

```yaml
---
run_id: 2026-06-22-001
state: GATE_CHECK
scenario: session
source: { kind: session, file: content/sessions/2026-06-22-session-...md }
formats: [x, linkedin, blog]
draft_count: 2
---

## researcher
classification: { archetype, funnel, icp_layer, vertical }
evidence: { session, topic_text, key_facts }

## strategist
core_insight: ...
meanings: { systemic, behavioral, philosophical, contrarian, leverage, human }
selected_meaning: { axis, rationale }
template_selection: { x: [...], linkedin: [...], blog: [...] }

## copywriter
drafts: [{ file, template, hook, archetype, axis, funnel, voice_register, self_check }]

## editor
gates: { mechanical: ..., soft: ..., verdict: pass|warn|fail }

## designer
banners: [{ draft, banner, icon, template, size_bytes }]

## publisher
publish_decisions: [{ draft, decision }]
posted: [{ draft, post_ids, urls, archive }]
held: []
rejected: []
failed: []

## analyst
engagement: [{ draft, views, likes, replies, reposts, pulled_at }]
perf_delta: { ... }
template_rerank: { ... }

## state_history
- 2026-06-22T18:08:00Z IDLE
- ...
```

## File I/O per state

| State | Reads | Writes |
|---|---|---|
| IDLE | (nothing) | `content/.brief.md` (skeleton or reset) |
| SESSION_CAPTURE | `content/sessions/*.md` OR `topic text` | `## researcher` in brief |
| COMPILE | `## researcher`, `system/prompts/compiler.md`, `strategy/icp.md` | `## strategist.core_insight` + `## strategist.meanings` |
| SELECT | `## strategist`, `templates/registry/viral-templates.yaml` | `## strategist.template_selection` |
| DRAFTING | `## strategist`, `## researcher`, `strategy/voice.md`, `strategy/corpus.md`, `templates/<platform>.md` | `## copywriter` + `content/queue/*.md` + `formats` |
| BANNER | drafts in `content/queue/` | `## designer` + `assets/banners/*.png` + `banner:` frontmatter |
| GATE_CHECK | drafts in `content/queue/` | `## editor` + `gates:` frontmatter |
| PUBLISHING | drafts in `content/queue/`, `.env` | `## publisher` + `content/posted/*.md` + `content/rejected/*.md` |
| ANALYZING_POST | `## publisher.posted` | `## analyst` + `templates/registry/performance.json` |
| COMPLETE_POST | `content/.brief.md` | rename to `content/.brief/YYYY-MM-DD-NNN.md` |

## The deterministic tools

- `tools/researcher.py` — synthesizes a session log from the opencode DB (5s SQLite timeout) + classifies.
- `tools/designer.py` — renders PNG banners (Playwright + system Chrome).
- `tools/editor.py` — runs the 15 mechanical gates against each draft.
- `tools/publisher/buffer.py` — multi-platform fan-out (X + LinkedIn + Threads).
- `tools/publisher/twitter.py` — direct X API fallback.
- `tools/publisher/linkedin.py` — direct LinkedIn UGC API fallback.
- `tools/publisher/blog.sh` — GH Pages deploy.
- `tools/analyst.py` — pulls Buffer engagement, updates perf.json, re-ranks viral-templates.yaml.

All other work is the LLM, reading the brief and writing to the brief.
