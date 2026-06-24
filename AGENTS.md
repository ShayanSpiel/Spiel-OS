# AGENTS.md — SpielOS Governance

> Read `system/state-machine.md` for the state table. Read `team/post.md` for the pipeline procedure. Everything else is reference.

---

## What SpielOS is

A markdown-driven content pipeline. You bring the work. The pipeline turns it into posts for X, LinkedIn, and your blog. **You stay a builder.**

There is **one agent** (the slash command `team/post.md`) and **one prompt** (the body of that file). When you type `/post`, the LLM runs the full 10-state pipeline in your chat. No subagents, no nesting, no delegation. You see everything.

Five deterministic tools (`tools/researcher.py`, `tools/editor.py`, `tools/designer.py`, `tools/analyst.py`, `tools/publisher/*`) handle the parts the LLM can't do (SQLite reads, regex gates, PNG rendering, HTTP API calls).

The handoff file is one `.brief.md` per run. The state machine is a single markdown table at `system/state-machine.md`. **No central Python orchestrator.**

---

## The architecture

| File | Role |
|---|---|
| `team/post.md` | The slash command. Frontmatter: name + description. Body: full 10-step procedure. This is the only agent. |
| `system/state-machine.md` | The state table. The procedure references this. |
| `system/prompts/identity.md` | Hard rules for the LLM (no em-dashes, no leaked labels, etc.). |
| `system/prompts/compiler.md` | The compiler procedure (read at Step 3). |
| `system/prompts/leak-guard.md` | Architecture leak rules (read at draft time). |
| `system/prompts/wizards.md` | Format and publish wizard specs. |
| `system/rules.yaml` | Mechanical rules (regex, keyword banks). |
| `system/gates.md` | The 15 mechanical + 14 soft quality gates. |
| `strategy/*.md` | User's brand/ICP/positioning (filled by wizard). |
| `templates/*.md` | Platform templates. |
| `templates/registry/viral-templates.yaml` | Template registry. |
| `tools/*.py` | The 5 deterministic tools. |
| `content/.brief.md` | Active brief (gitignored). |
| `content/.brief/YYYY-MM-DD-NNN.md` | Archived briefs. |

That's it. No subagent files. No role files. No state file. The slash command is the only thing the IDE loads as an agent.

---

## The 10 states

```
IDLE → SESSION_CAPTURE → COMPILE → SELECT → DRAFTING → BANNER → GATE_CHECK → PUBLISHING → ANALYZING_POST → COMPLETE_POST → IDLE
```

The state table is the single source of truth at `system/state-machine.md`. The procedure for each state lives in `team/post.md`.

| # | State | What happens |
|---|---|---|
| 0 | IDLE | Awaiting `/post`. |
| 1 | SESSION_CAPTURE | Capture the source (session from opencode DB, or topic text). Classify. |
| 2 | COMPILE | Run the compiler. Extract core insight + 6 axis meanings. |
| 3 | SELECT | Rank templates by archetype/axis/funnel/ICP. |
| 4 | DRAFTING | Ask user for platforms. Write drafts with 15-field frontmatter. |
| 5 | BANNER | Render PNG banners (Playwright + Chrome). |
| 6 | GATE_CHECK | Run 15 mechanical gates + 14 soft self-check. |
| 7 | PUBLISHING | Ask user p/h/r per draft. Dispatch via Buffer / direct API / GH Pages. |
| 8 | ANALYZING_POST | Pull engagement. Re-rank templates. |
| 9 | COMPLETE_POST | Archive brief. Back to IDLE. |

---

## The handoff file: `.brief.md`

One `.brief.md` per `/post` run. Created on Step 0, updated each step, archived on Step 10.

```yaml
---
run_id: 2026-06-22-001
state: GATE_CHECK
scenario: session
source: current_conversation
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
template_rerank: { x: [...], linkedin: [...], blog: [...] }

## state_history
- 2026-06-22T18:08:00Z IDLE
- 2026-06-22T18:08:05Z SESSION_CAPTURE
- ...
```

Schema at `system/brief-schema.md`.

**Field ownership** — the LLM writes each section once per state.

**Section missing** — if a section is missing when the LLM gets to the next step, it re-runs the prior step. After one retry, it fails the run.

**File location** — `content/.brief.md` while running, archived to `content/.brief/YYYY-MM-DD-NNN.md` on COMPLETE_POST.

**Crash recovery** — Step 0 of the next `/post` reads `content/.brief.md` and detects the last state in `## state_history`. If it's not `IDLE`, it resets to IDLE.

---

## Human interaction

Two steps use the `question` tool:

| Step | What the user does | Shape |
|---|---|---|
| 5 (DRAFTING) | Pick platforms: x, linkedin, blog, all, hold | one choice |
| 8 (PUBLISHING) | Per-draft p/h/r | one per draft |

The LLM never auto-picks at a human checkpoint. It always uses the `question` tool and waits.

---

## What stays deterministic

These 5 tools the LLM calls via `bash`:

| Tool | What |
|---|---|
| `tools/researcher.py` | Session log synthesis from opencode DB (5s timeout) + classify |
| `tools/editor.py` | 15 mechanical gate checks (regex, length, structural) |
| `tools/designer.py` | Banner PNG render (Playwright + system Chrome) |
| `tools/analyst.py` | Buffer engagement pull + perf ledger + re-rank |
| `tools/publisher/{buffer,twitter,linkedin,blog.sh}` | API dispatch + archive |

Everything else is LLM-driven (the 10-step procedure in `team/post.md`).

---

## The install flow

```bash
curl -fsSL https://spielos.xyz/spielos | bash
```

1. Installer downloads the repo into the current directory (your project root becomes the vault, marked by `.spiel-vault`).
2. Starts the local dashboard at `http://localhost:7331` (auto-opens in browser).
3. Wizard walks 10 steps: Welcome → Brand → ICP → Positioning → Offer → Funnel + Archetypes → Voice + Corpus → Methodology → Rules → Connect.
4. Wizard writes 8 strategy files + brand + .env on Finish, then auto-shuts down.
5. Installer writes `<vault>/.spiel-vault` (vault pointer), `~/.config/spielos/config` (global config), shim at `~/.local/bin/spiel`, slash command at `~/.config/opencode/commands/post.md`.
6. Prints `DONE. From your IDE, type /post to ship a post.`

After install, the user never touches this repo. They edit `strategy/*.md` and `content/*` only.

### Install env vars

| Var | Default | What |
|---|---|---|
| `SPIELOS_INSTALL_DIR` | `$PWD` | Where to install the vault (default: current directory) |
| `SPIELOS_WIZARD_PORT` | `7331` | Port for the local dashboard |
| `SPIELOS_WIZARD_TIMEOUT` | `1800` (30 min) | Max wait for the wizard to finish |
| `SPIELOS_VERSION` | `main` | Git branch / tag / tarball ref |

### Vault resolution order

The vault is resolved (first match wins):

1. **`$VAULT_DIR` env var** — explicit per-session override
2. **`~/.config/spielos/config`** — global config (set by installer, persistent)
3. **`<cwd>/.spiel-vault`** — cwd walk-up for `.spiel-vault` file
4. **`<cwd>/team/md.md`** — cwd walk-up for vault marker (legacy)
5. **`<shim>/..`** — detected when shim lives at `<vault>/bin/spiel`

If they ever install to the wrong directory or move the vault, run:
```
spiel set-vault /path/to/vault
```

---

## Hard rules across the system

- **NEVER** auto-pick at a human checkpoint. Use the `question` tool. Wait for the user.
- **NEVER** use em-dashes in drafts. Use `→`, `:`, or `,`. The editor will fail the draft.
- **NEVER** leak internal labels (S1–S10, TOFU/MOFU/BOFU, L1–L4) in public posts.
- **NEVER** pitch the offer outside the 1-in-5 rule.
- **NEVER** write a draft without the full 15-field frontmatter.
- **NEVER** publish a draft with `gates: fail`.
- **NEVER** publish a draft without `banner:`.

---

## License

MIT.
