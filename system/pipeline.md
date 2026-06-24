# Pipeline

The content pipeline is a 10-state machine, executed by **MD** orchestrating 3 subagents (designer, editor, publisher) for tool-heavy work and running 5 inline steps (researcher, strategist, copywriter, analyst) in its own conversation.

```
IDLE → SESSION_CAPTURE → COMPILE → SELECT → DRAFTING → BANNER → GATE_CHECK → PUBLISHING → ANALYZING_POST → COMPLETE_POST → IDLE
```

## The 10 states

| # | State | Owner | Output | Where the work runs |
|---|---|---|---|---|
| 0 | IDLE | MD | empty brief | inline in MD |
| 1 | SESSION_CAPTURE | MD (inline via `researcher.md`) | `## researcher` | inline in MD + `tools/researcher.py` |
| 2 | COMPILE | MD (inline via `strategist.md`) | `## strategist.core_insight` + 6 axes | inline in MD |
| 3 | SELECT | MD (inline via `strategist.md`) | `## strategist.template_selection` | inline in MD |
| 4 | DRAFTING | MD (inline via `copywriter.md`) | `## copywriter` + draft files + `formats` | inline in MD + `question` tool |
| 5 | BANNER | **@designer subagent** | `## designer` + PNG files | `task(designer)` + `tools/designer.py` |
| 6 | GATE_CHECK | **@editor subagent** | `## editor.verdict` | `task(editor)` + `tools/editor.py` |
| 7 | PUBLISHING | **@publisher subagent** | `## publisher` + posted/rejected files | `task(publisher)` + `tools/publisher/*` |
| 8 | ANALYZING_POST | MD (inline via `analyst.md`) | `## analyst` | inline in MD + `tools/analyst.py` |
| 9 | COMPLETE_POST | MD | `.brief.md` archived | inline in MD |

---

## Hand-off graph

```
MD (inline — runs in MD's visible conversation, 1 nesting level)
│
├── Step 2: read system/prompts/researcher.md → run tools/researcher.py → write ## researcher
├── Step 3: read system/prompts/strategist.md + compiler.md → run compiler → write ## strategist
├── Step 4: read templates/registry/viral-templates.yaml → rank → write template_selection
├── Step 5: read system/prompts/copywriter.md + format-wizard.md → question tool → write drafts + ## copywriter
│
├── Step 6: task(designer) → banner render → write ## designer
├── Step 7: task(editor) → gate checks → write ## editor
├── Step 8: task(publisher) → p/h/r wizard + dispatch → write ## publisher
│
├── Step 9: read system/prompts/analyst.md → run tools/analyst.py → write ## analyst
└── Step 10: archive brief → IDLE
```

Only designer, editor, and publisher run as separate subagents (via `task()`). Everything else runs inline in MD's conversation — fixing both session capture (MD can read the opencode DB) and UX (user sees progress without clicking into nested panels).

---

## File I/O per state

| State | Reads | Writes |
|---|---|---|
| IDLE | (nothing) | `content/.brief.md` (skeleton) |
| SESSION_CAPTURE | `content/sessions/*.md` OR `topic text` | `## researcher` |
| COMPILE | `## researcher`, `system/prompts/compiler.md`, `strategy/icp.md` | `## strategist.core_insight` + `## strategist.meanings` |
| SELECT | `## strategist`, `templates/registry/viral-templates.yaml` | `## strategist.template_selection` |
| DRAFTING | `## strategist`, `## researcher`, `strategy/voice.md`, `strategy/corpus.md`, `templates/<platform>.md` | `## copywriter` + `content/queue/*.md` + `formats` |
| BANNER | `## copywriter` | `## designer` + `assets/banners/*.png` + `banner:` frontmatter |
| GATE_CHECK | drafts in `content/queue/` | `## editor` + `gates:` frontmatter |
| PUBLISHING | drafts in `content/queue/`, `.env` | `## publisher` + `content/posted/*.md` + `content/rejected/*.md` |
| ANALYZING_POST | `## publisher.posted` | `## analyst` + `templates/registry/performance.json` |
| COMPLETE_POST | `content/.brief.md` | rename to `content/.brief/YYYY-MM-DD-NNN.md` |

---

## Where the deterministic parts run

- `tools/researcher.py` — synthesizes a session log from the opencode DB (5s SQLite timeout to prevent hangs) + classifies.
- `tools/designer.py` — renders PNG banners (Playwright + system Chrome).
- `tools/editor.py` — runs the 15 mechanical gates against each draft.
- `tools/publisher/buffer.py` — multi-platform fan-out (X + LinkedIn + Threads).
- `tools/publisher/twitter.py` — direct X API fallback.
- `tools/publisher/linkedin.py` — direct LinkedIn UGC API fallback.
- `tools/publisher/blog.sh` — GH Pages deploy.
- `tools/analyst.py` — pulls Buffer engagement, updates perf.json, re-ranks viral-templates.yaml.

All other work is the LLM, reading the brief and writing to the brief.
