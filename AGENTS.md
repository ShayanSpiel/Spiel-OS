# AGENTS.md — SpielOS Governance

The canonical governance doc. **The state machine, the team, the role contracts.**

> **If you only read one file, read `system/state-machine.md`.**
> **If you only read two, also read `system/brief-schema.md`.**
> **If you only read three, also read this file.**
> **Everything else is reference.**

---

## What SpielOS is

A markdown-driven marketing team. You bring the work. MD — the orchestrator — turns it into posts for X, LinkedIn, and your blog. **You stay a builder.**

The pipeline has **3 subagents** (real agents for tool-heavy work: designer, editor, publisher) and **5 reference docs** (LLM-driven work MD does inline: researcher, strategist, copywriter, analyst). The 3 subagents live in `team/`. The 5 reference docs live in `system/prompts/`. The 5 deterministic tools are small Python CLIs in `tools/`. The state machine is a single markdown table at `system/state-machine.md`. The handoff file is one `.brief.md` per run. **No central Python orchestrator.**

**Why this design:** the 3 subagents (designer, editor, publisher) genuinely need their own context — they run heavy tooling (Playwright, Buffer API, GH Pages) and have complex state management (the bounce loop in editor). The 5 LLM-driven roles do pure reasoning and work better when the LLM has the full context. Putting them all behind `task()` made the UX nested 7 levels deep. This model is 1 level deep (post → MD), with 3 tool delegations to subagents where isolation matters.

---

## The team: 3 subagents + 5 reference docs

### 3 subagents (in `team/`)

| Agent | File | States owned | What it does |
|---|---|---|---|
| **designer** | [`team/designer.md`](team/designer.md) | BANNER | Picks template + tokens, calls `tools/designer.py` (Playwright + system Chrome) |
| **editor** | [`team/editor.md`](team/editor.md) | GATE_CHECK | Calls `tools/editor.py` (15 mechanical) + 14 soft review, bounce loop |
| **publisher** | [`team/publisher.md`](team/publisher.md) | PUBLISHING | Per-draft p/h/r wizard, dispatch via Buffer / direct API / GH Pages |

The IDE invokes the MD subagent when you type `/post`. MD delegates to these 3 via `task()` — and only these 3 (the permission block literally allows only these 3).

### 5 reference docs (in `system/prompts/`, run inline by MD)

| Role | Reference doc | States | What it does |
|---|---|---|---|
| **researcher** | [`system/prompts/researcher.md`](system/prompts/researcher.md) | SESSION_CAPTURE | DB synthesis (primary) + classification + key facts |
| **strategist** | [`system/prompts/strategist.md`](system/prompts/strategist.md) | COMPILE, SELECT | 8-step (session) or 6-question (topic) compiler + template ranking |
| **copywriter** | [`system/prompts/copywriter.md`](system/prompts/copywriter.md) | DRAFTING | Format wizard (question tool) + writes drafts + 14 soft-gate self-check |
| **analyst** | [`system/prompts/analyst.md`](system/prompts/analyst.md) | ANALYZING_POST | Engagement pull + perf ledger + re-rank |
| **format-wizard** | [`system/prompts/format-wizard.md`](system/prompts/format-wizard.md) | (called from DRAFTING) | Asks user which platforms to write for |

These are reference docs that MD reads via the `read` tool at each step. The LLM that runs MD is the actor; the docs are the procedure. This means:
- The user sees strategist/copywriter/analyst work in MD's visible conversation
- No nested subagent conversations
- The session capture is fixed (researcher.py reads the opencode DB, MD has the result in context)

---

## The 10 states

```
IDLE → SESSION_CAPTURE → COMPILE → SELECT → DRAFTING → BANNER → GATE_CHECK → PUBLISHING → ANALYZING_POST → COMPLETE_POST → IDLE
```

The state table is the **single source of truth** at `system/state-machine.md`. No Python enforces it. MD reads the table; nobody else needs to.

### State → role → action map

| # | State | Owner | Action | Next states |
|---|---|---|---|---|
| 0 | IDLE | MD | reset brief, await intent | SESSION_CAPTURE |
| 1 | SESSION_CAPTURE | **MD inline** (reads `system/prompts/researcher.md`) | DB synthesis + classification + key facts | COMPILE / IDLE |
| 2 | COMPILE | **MD inline** (reads `system/prompts/strategist.md` + `system/prompts/compiler.md`) | 8-step (session) or 6-question (topic) compiler | SELECT / IDLE |
| 3 | SELECT | **MD inline** (reads `system/prompts/strategist.md`) | rank templates by archetype/axis/funnel/ICP | DRAFTING / IDLE |
| 4 | DRAFTING | **MD inline** (reads `system/prompts/copywriter.md` + `format-wizard.md`) | format wizard (question tool) + write drafts + soft-gate self-check | BANNER / IDLE |
| 5 | BANNER | **@designer subagent** (via `task()`) | pick template + tokens, call `tools/designer.py` | GATE_CHECK |
| 6 | GATE_CHECK | **@editor subagent** (via `task()`) | call `tools/editor.py` (15 mechanical) + 14 soft review | PUBLISHING / DRAFTING |
| 7 | PUBLISHING | **@publisher subagent** (via `task()`) | publish wizard + dispatch via Buffer (or direct API) + archive | ANALYZING_POST / IDLE |
| 8 | ANALYZING_POST | **MD inline** (reads `system/prompts/analyst.md`) | pull engagement + re-rank templates | COMPLETE_POST |
| 9 | COMPLETE_POST | MD | archive `.brief.md` | IDLE |

---

## The handoff file: `.brief.md`

One `.brief.md` per `/post` run. Every role (subagent or inline) writes its `## <role>` section, appends the next state to `## state_history`, returns. Schema at `system/brief-schema.md`.

```markdown
---
run_id: 2026-06-22-001
state: GATE_CHECK
source: { kind: session, file: content/sessions/2026-06-22-session-...md }
formats: [x, linkedin, blog]
---
```

**Field ownership** — each role writes its section once per state. Re-running is idempotent (read existing, diff, overwrite owned fields).

**Section missing** — if MD runs an inline step and the prior step's section is missing, MD re-runs the prior step (retry once). If still missing, MD exits to IDLE with an error.

**File location** — `content/.brief.md` while running, archived to `content/.brief/YYYY-MM-DD-NNN.md` on COMPLETE_POST. `.brief/` is gitignored.

**Crash recovery** — read the last line of `## state_history`, ask the user "continue from <state> or restart?"

---

## Human interaction (embedded in roles)

Two roles interact with the user directly via the `question` tool:

| Role | State | What the user does | Source |
|---|---|---|---|
| **Copywriter (inline in MD)** | DRAFTING | Pick platforms: x, linkedin, blog | `system/prompts/format-wizard.md` |
| **Publisher (subagent)** | PUBLISHING | Per-draft p/h/r/s | `~/.config/opencode/skill/publish_wizard/SKILL.md` |

Roles NEVER auto-pick at a human checkpoint. Always use the `question` tool and wait for the user's answer. MD is never involved in human interaction.

---

## Bounce rule

- **GATE_CHECK → DRAFTING** if any draft failed mechanical gates. Editor calls `tools/editor.py` once more after Copywriter's fix. Max 3 bounce rounds; after 3, MD moves to PUBLISHING anyway with `verdict: warn`.

---

## Hold / Reject

- **Hold** — draft stays in `content/queue/`, decision is null. Publisher handles it. Next `/post` run enters PUBLISHING for those held drafts.
- **Reject** — draft moves to `content/rejected/` with `rejection_reason:` frontmatter.

---

## How a subagent is structured

Every `team/<role>.md` (the 3 subagents) has this shape:

```markdown
---
name: <role>
description: <one-line>
mode: subagent
role_in_pipeline: [<state>, ...]
reads: [<list of files / sections>]
writes: [<list of files / sections>]
tools: [<list of CLI tools>]
---

# <Role>

## Mission
[What this role owns]

## Handoff IN
[What I read from the previous role]

## Handoff OUT
[What I write to the brief + any files]

## <role-specific guidance>
[State machine / compiler / drafting / etc.]

## Voice
[Tone, register, status line format]

## Hard rules
[What I never do]

## Failure modes
[What I do when X]
```

When you add a new subagent, copy this structure. The handoff contract (`reads:` / `writes:`) is what makes the chain work.

## How a reference doc is structured

Every `system/prompts/<role>.md` (the 5 inline roles) has this shape:

```markdown
---
name: <role>
description: <one-line — what the doc is, what state MD reads it at>
---

# <Role> (reference for MD)

## Mission
[What MD does at this step]

## Status output
[The `MD — <status>` lines MD prints while running this step]

## Handoff IN / Handoff OUT
[What MD reads, what MD writes to the brief]

## <role-specific procedure>
[Full step-by-step procedure MD follows inline]

## Hard rules
[What MD never does at this step]

## Failure modes
[What MD does when X]
```

The reference doc is procedural guidance for the LLM running MD. It is not a subagent — `sync_adapters.py` will not install it as one.

---

## What stays deterministic

These 5 tools the LLM can't replace:

| Tool | Role | What |
|---|---|---|
| `tools/editor.py` | Editor (subagent) | 15 mechanical gate checks (regex, length, structural) |
| `tools/designer.py` | Designer (subagent) | Banner PNG render (Playwright + system Chrome) |
| `tools/publisher/{buffer,twitter,linkedin,blog.sh}` | Publisher (subagent) | API dispatch + archive |
| `tools/analyst.py` | Analyst (inline in MD) | Buffer engagement pull + perf ledger + re-rank |
| `tools/researcher.py` | Researcher (inline in MD) | Session log synthesis from opencode DB + classify |

Everything else is LLM-driven (the 3 subagent `.md` files in `team/` + the 5 reference docs in `system/prompts/`).

---

## How to extend the team

Adding a new subagent (tool-heavy role) is **one file + one sync**:

1. Drop `team/<name>.md` with the subagent structure above.
2. Add `task.<name>: allow` to the `permission:` block in `team/md.md`.
3. Run `python3 tools/sync_adapters.py --install`.
4. The new subagent is now available in opencode, Claude Code, Cursor, MCP.

Adding a new inline step is **one reference doc + one MD step**:

1. Drop `system/prompts/<role>.md` with the reference doc structure above.
2. Add a new procedure block in `team/md.md` that reads the doc and follows the procedure.
3. No sync needed — reference docs are not installed as agents.

Adding a new state is **one row in the table** at `system/state-machine.md` + one role file (or a delegation to an existing role).

---

## Where everything lives

| What | Where |
|---|---|
| Subagent prompts (3 — designer, editor, publisher) | `team/*.md` |
| Inline role reference docs (5 — researcher, strategist, copywriter, analyst, format-wizard) | `system/prompts/*.md` |
| State machine (canonical) | `system/state-machine.md` |
| Brief schema (canonical) | `system/brief-schema.md` |
| Pipeline map | `system/pipeline.md` |
| Brand (human) | `system/brand.md` |
| Brand (machine) | `system/brand.json` |
| LLM identity | `system/prompts/identity.md` |
| Compiler prompt | `system/prompts/compiler.md` |
| Leak guard | `system/prompts/leak-guard.md` |
| Format wizard skill | `system/prompts/format-wizard.md` |
| Publish wizard skill | `~/.config/opencode/skill/publish_wizard/SKILL.md` |
| Quality gates | `system/gates.md` |
| Mechanical config | `system/rules.yaml` |
| Knowledge base (user) | `strategy/*.md` (filled by wizard) |
| Post output shapes | `templates/*.md` |
| Templates + perf ledger | `templates/registry/*` |
| Deterministic tools | `tools/editor.py`, `tools/designer.py`, `tools/publisher/*`, `tools/analyst.py`, `tools/researcher.py` |
| Sync adapters | `tools/sync_adapters.py` |
| IDE adapter files | `adapters/` (auto-gen) |
| Live install | `~/.config/opencode/{agents,skill,commands}/`, `~/.cursor/skills/`, `~/.claude/{agents,skills}/` |
| Vault shim | `bin/spiel` (installed to `~/.local/bin/spiel`) |
| Global config | `~/.config/spielos/config` — stores `VAULT_DIR=`, makes vault resolvable from ANY cwd |
| Vault pointer | `<vault>/.spiel-vault` (marks the vault root; auto-created on install/update) |
| Install + wizard | `install/install.sh`, `install/wizard/` |
| Brief file (active) | `content/.brief.md` |
| Brief archive | `content/.brief/YYYY-MM-DD-NNN.md` |
| Sessions / queue / posted / rejected | `content/{sessions,queue,posted,rejected}/` |
| Banners | `assets/banners/*.png` |
| Icons | `assets/icons/*.svg` |

---

## Hard rules across the system

- **NEVER** auto-pick at a human checkpoint. Use the `question` tool. Wait for the user.
- **NEVER** use em-dashes. Use →, colons, or commas. The Editor will fail the draft.
- **NEVER** leak internal labels (S1–S10, TOFU/MOFU/BOFU, L1–L4, "core_insight" as a label, "the engine" as a label, "the pipeline" as a label) in public posts.
- **NEVER** pitch the offer outside the 1-in-5 rule.
- **NEVER** write a draft without the full 15-field frontmatter.
- **NEVER** advance the state without the previous role's section populated.
- **NEVER** publish a draft with `gates: fail`.
- **NEVER** publish a draft without `banner:`.

---

## The install flow

```bash
curl -fsSL https://spielos.xyz/spielos | bash
```

1. Installer downloads the repo into the **current directory** (your project root becomes the vault, marked by `.spiel-vault`)
2. Starts the local dashboard at `http://localhost:7331` (auto-opens in browser)
3. Installer polls for `.install-state.json` (the wizard writes this on Finish)
4. Wizard walks 10 steps: Welcome → Brand → ICP → Positioning → Offer → Funnel + Archetypes → Voice + Corpus → Methodology → Rules → Connect
5. Wizard writes 8 strategy files (textarea-based editors) + brand + .env on Finish, then auto-shuts down
6. Installer continues: writes `<vault>/.spiel-vault` (vault pointer), `~/.config/spielos/config` (global config — makes vault resolvable from ANY directory), shim at `~/.local/bin/spiel` + IDE adapters at all 3 IDEs (opencode, Cursor, Claude Code — whichever is installed)
7. Prints `DONE. From any IDE, type /post to ship a post.`

The install is fully non-blocking — the user never has to type anything into the terminal during the install. They just fill the form in the browser.

### Install env vars

| Var | Default | What |
|---|---|---|
| `SPIELOS_INSTALL_DIR` | `$PWD` | Where to install the vault (default: current directory) |
| `SPIELOS_WIZARD_PORT` | `7331` | Port for the local dashboard |
| `SPIELOS_WIZARD_TIMEOUT` | `1800` (30 min) | Max wait for the wizard to finish |
| `SPIELOS_VERSION` | `main` | Git branch / tag / tarball ref |

After install, the user never touches this repo. They edit `strategy/*.md` and `content/*` only.

If they ever install to the wrong directory or move the vault, run:
```
spiel set-vault /path/to/vault
```
This rewrites `~/.config/spielos/config` to point to the correct vault. No re-install needed.

### Vault resolution order

The vault is resolved (first match wins):

1. **`$VAULT_DIR` env var** — explicit per-session override
2. **`~/.config/spielos/config`** — global config (set by installer, persistent)
3. **`<cwd>/.spiel-vault`** — cwd walk-up for `.spiel-vault` file
4. **`<cwd>/team/md.md`** — cwd walk-up for vault marker
5. **`<shim>/..`** — detected when shim lives at `<vault>/bin/spiel`

After install, step 2 (`~/.config/spielos/config`) is always set, so spiel resolves the vault regardless of your current working directory. `/post` content always saves to the vault, even when your IDE is open in a different project.

---

## License

MIT.
