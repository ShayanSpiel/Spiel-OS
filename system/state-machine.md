# State Machine

The single source of truth for the content loop. **MD reads this on every step.**

The state machine is a markdown table. There is no Python orchestrator. MD (the LLM agent in `team/md.md`) reads the table, picks the next state, and runs the work for that state. **5 states run inline in MD's conversation** (SESSION_CAPTURE, COMPILE, SELECT, DRAFTING, ANALYZING_POST) by reading reference docs in `system/prompts/`. **3 states delegate via `task()` to subagents** (BANNER → designer, GATE_CHECK → editor, PUBLISHING → publisher). The previous state output is the next state input. The pipeline is step-chained within MD.

---

## The 10 states

| # | State | From | Owner | Output check | Next states |
|---|---|---|---|---|---|
| 0 | IDLE | (any) | MD | new run? | SESSION_CAPTURE |
| 1 | SESSION_CAPTURE | IDLE | MD (inline, via `researcher.md`) | `## researcher` populated | COMPILE / IDLE |
| 2 | COMPILE | SESSION_CAPTURE | MD (inline, via `strategist.md`) | `## strategist.core_insight` | SELECT / IDLE |
| 3 | SELECT | COMPILE | MD (inline, via `strategist.md`) | `template_selection` ≥ 1 | DRAFTING / IDLE |
| 4 | DRAFTING | SELECT | MD (inline, via `copywriter.md`) | `## copywriter.drafts` ≥ 1 | BANNER / IDLE |
| 5 | BANNER | DRAFTING | **@designer subagent** | each draft has `banner:` | GATE_CHECK |
| 6 | GATE_CHECK | BANNER | **@editor subagent** | `verdict: pass` | PUBLISHING / DRAFTING |
| 7 | PUBLISHING | GATE_CHECK | **@publisher subagent** | `## publisher` populated | ANALYZING_POST / IDLE |
| 8 | ANALYZING_POST | PUBLISHING | MD (inline, via `analyst.md`) | `## analyst.engagement` | COMPLETE_POST |
| 9 | COMPLETE_POST | ANALYZING_POST | MD | `.brief.md` archived | IDLE |

Human checkpoints are no longer separate states. Each role owns its own user interaction:

- **MD at DRAFTING** (inline copywriter step) — asks user which formats to write (x, linkedin, blog). Uses the `question` tool directly.
- **@publisher subagent at PUBLISHING** — asks user per-draft publish/hold/reject.

MD never delegates human interaction. It handles the format wizard itself in DRAFTING, and the publisher subagent handles the p/h/r wizard in PUBLISHING.

---

## Hand-off discipline

- For inline states: MD runs the work, writes the role section to the brief, appends the next state to `## state_history`, moves on.
- For subagent states: the subagent runs the work, writes the role section, appends the next state, returns. MD reads the brief and continues.
- 15-minute idle between states = state expires → MD reverts to IDLE.
- One state at a time. No parallel states. No skipping.

## Crash recovery

`## state_history` is append-only. If MD reads a brief and the last entry is `BANNER`, the pipeline is mid-banner — MD asks "continue from BANNER, or restart from IDLE?" before doing anything.

If `## state_history` is empty, MD assumes `IDLE` and starts a new run.

## Human interaction (embedded in roles)

Two roles interact with the user via the `question` tool:

| Role | State | What it asks | Input shape |
|---|---|---|---|
| MD (inline copywriter) | DRAFTING | Which platforms? | `x`, `linkedin`, `blog`, `x linkedin`, `all`, `hold` |
| Publisher subagent | PUBLISHING | Per-draft p/h/r? | `p`, `h`, `r <reason>` |
| Publisher subagent | PUBLISHING | Confirm all decisions | `y` / `N` |

If the user says `hold` at format pick, MD exits to IDLE with no drafts.
If the user holds/rejects all at publish review, Publisher returns with `posted: []` — MD skips ANALYZING_POST.

## Bounce rule

- **GATE_CHECK → DRAFTING** if any draft failed mechanical gates. Editor calls `tools/editor.py` once more after Copywriter's fix. Max 3 bounce rounds; after 3, MD moves to PUBLISHING anyway with a `verdict: warn` flag.

## Hold / Reject

- **Hold** = draft stays in `content/queue/`, decision is null. Publisher logs it. Next `/post` run enters PUBLISHING for those held drafts.
- **Reject** = draft moves to `content/rejected/` with a `rejection_reason:` frontmatter field. Engine learns nothing from this (no LLM-judged adaptation in MVP).

## Idempotency

Re-running the same state is safe:
- **Re-running BANNER** = re-render only the drafts missing `banner:`.
- **Re-running GATE_CHECK** = re-run only drafts with `gates: fail` or no `gates:`.
- **Re-running PUBLISHING** = re-publish only drafts with decision `publish` that aren't already in `content/posted/`.

MD checks the brief's `## state_history` and the draft's frontmatter to decide what to skip.
