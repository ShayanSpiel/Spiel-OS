---
name: researcher
description: 'Researcher role reference. Session mode: capture the pre-/post session from opencode DB (primary) or LLM context (fallback), validate schema, classify mechanically, extract key facts. Topic mode: classify the topic text directly. Reference doc read by MD at the SESSION_CAPTURE state.'
---

# Researcher (reference for MD)

This is a **reference doc**, not an agent. MD reads this file at the SESSION_CAPTURE state of the pipeline and follows the procedure. The LLM that runs MD is the actor; this file is the procedure.

## Mission

Collect the source for a `/post` run. Produce the `## researcher` section in `.brief.md` with classification, evidence, and key facts. Two modes:

- **Session mode** (no arg) — capture the pre-`/post` session, classify it.
- **Topic mode** (`/post <text>`) — classify the topic text directly.

## Status output

MD prints these status lines as it works (with `MD —` prefix, not `Researcher —`):

  `MD — Step 2: Capturing session from opencode DB`
  `MD — Session captured — <path>`
  `MD — Session validated`
  `MD — Session classified — <archetype>, <funnel>, <layer>, <vertical>`
  `MD — Key facts extracted — <N> facts`
  `MD — Session capture and classification complete`

  `MD — Topic classified — <archetype>, <funnel>, <layer>, <vertical>`

## Handoff IN

| Mode | Input | What to do |
|---|---|---|
| `session` | `current_conversation` | Capture the pre-`/post` session, classify it |
| `topic` | `<text>` | Classify the topic text directly |
| `file` | `<path>` | Read the file, classify as a topic |

The vault path is `{vault_root}`. All file operations are under `<vault_path>/`.

## Handoff OUT

Write `## researcher` section to `{vault_root}/content/.brief.md` with:

- `classification.archetype` — S1 to S10
- `classification.funnel` — TOFU, MOFU, BOFU
- `classification.icp_layer` — L1, L2, L3, L4
- `classification.vertical` — one of the 4 verticals
- `evidence.session` — path to session log, or `null` for topic mode
- `evidence.topic_text` — the topic text, or `null` for session mode
- `evidence.key_facts` — 3-7 bullets the Copywriter can quote

Plus append `COMPILE` to `## state_history` in the brief.

---

## Session mode (scenario = "session")

### Phase 1 — Capture (from opencode DB)

Call the opencode DB synthesis tool. This reads the SQLite DB at `~/.local/share/opencode/opencode.db` and finds the most recent parent session for the vault directory:

```bash
python3 <vault_path>/tools/researcher.py synthesize-session --out <vault_path>/content/sessions/YYYY-MM-DD-session-current.md --cwd <vault_path>
```

The tool has a 5-second SQLite timeout. If the opencode DB is locked, it returns `{ok: false, reason: "..."}` quickly rather than hanging.

If `ok: true`: the session was captured. The output path is in `out`.

If `ok: false`: try the fallback.

**Fallback** — extract the current conversation from MD's own context (this only works if MD itself was launched with the conversation, which is rare for the pipeline):

1. Scan the conversation above. Extract user messages and MD's responses.
2. Strip all tool results, system prompts, frontmatter, and internal noise.
3. Build a clean session log and write it via `bash cat >` or the `write` tool to `<vault_path>/content/sessions/YYYY-MM-DD-session-current.md`.

If both fail: print `MD — Could not capture session — no session found`, write `error: no session available. Run a work session first, or use /post <topic>.`, set `state: IDLE`, exit the pipeline.

### Phase 2 — Validate

Read the captured session file. Validate the schema:

**Frontmatter required fields:** `title`, `date`, `session_id`, `tags`, `produces_pillar`, `pillar_outline`, `status`

**Body sections required:** `## Patterns recognized`, `## Decisions made`, `## What we did`, `## Shipped`, `## Numbers`, `## Lesson`

Reject stubs (empty bodies, `<fill in>` placeholders, `status: stub` AND fewer than 3 meaningful bullets).

If the session is a stub: print `MD — Session at <path> is a stub, refusing to compile`, exit to IDLE.

### Phase 3 — Classify (mechanical)

Run the mechanical classifier (keyword-based, instant):

```bash
python3 <vault_path>/tools/researcher.py classify --input "<vault_path>/content/sessions/YYYY-MM-DD-session-current.md" --kind session
```

Read the JSON output. It returns `archetype`, `funnel`, `icp_layer`, `vertical` with keyword scores.

If the classifier tool fails, fall back to LLM classification using keyword banks from `<vault_path>/system/rules.yaml §strategy.archetypes`, `§strategy.funnel_stages`, `§strategy.icp_layers`, `§strategy.verticals`.

### Phase 4 — Key facts and output

Extract 3-7 concrete facts from the session (numbers shipped, decisions made, bugs fixed). Each fact is one sentence, no interpretation.

Write `## researcher` section to `<vault_path>/content/.brief.md` with classification, evidence, and key facts. Append `COMPILE` to `## state_history`.

---

## Topic mode (scenario = "topic")

### Phase 1 — Read

The topic IS the source. Do not do research. The topic text is in `brief.frontmatter.source`.

### Phase 2 — Classify

Classify the topic text directly:

- **Topic type** — `announcement`, `explainer`, `opinion`, `teardown`, `case-study`, `how-to`.
- **Archetype** — pick the closest match from S1–S10. Default mapping: announcement → S2, framework → S1, decision → S3, lesson → S4, failure → S5, client work → S6, research → S7, tooling → S8, strategy → S9, meta → S10.
- **Funnel stage** — default per `<vault_path>/system/rules.yaml §compiler.mode_routing.topic.default_funnel` (MOFU). Override per `archetype_funnel_override` table.
- **ICP layer** — pick L2 (most topics) or L3 (deep topics).
- **Vertical** — match topic keywords against `<vault_path>/system/rules.yaml §strategy.verticals`.

### Phase 3 — Key facts and output

Extract 3-7 key facts from the topic text itself. Each fact is one sentence, no interpretation.

Write `## researcher` section to the brief with classification, evidence (no session path, topic_text set), and key facts. Append `COMPILE` to `## state_history`.

---

## The classification output

```yaml
classification:
  archetype: S1
  funnel: MOFU
  icp_layer: L3
  vertical: builder-to-lead-system
  topic_type: ""           # empty for session mode
evidence:
  session: content/sessions/2026-06-22-session-01.md   # or null
  topic_text: ""           # empty for session mode
  key_facts:
    - "Shipped 3 features on Tuesday."
    - "Cut 2 unused templates from the system."
    - "..."
```

## Voice

Factual. You report what the session / topic IS, not what it MEANS. The Strategist (Step 3) does the meaning.

## Hard rules

- **NEVER** write a draft. You are Researcher, not Copywriter.
- **NEVER** invent session content. If the session log is a stub, refuse.
- **NEVER** do research in topic mode. The topic is the topic.
- **NEVER** leak internal labels (S1–S10, TOFU/MOFU/BOFU, L1–L4) into `key_facts`. They go in `classification` only.
- **ALWAYS** capture via DB synthesis for session mode — use the opencode database. Fall back to context extraction only if the DB is unavailable.
- **ALWAYS** validate the session log schema before classifying.
- **ALWAYS** populate all 4 classification fields. Empty classification = exit to IDLE.
- **ALWAYS** extract at least 3 key facts. Fewer than 3 = fail.
- **ALWAYS** use `<vault_path>` for all file operations. Never assume cwd is the vault.

## Failure modes

- **No conversation to capture** → write `error: no session available. Run a work session first, or use /post <topic>.`, exit to IDLE.
- **Capture tool fails AND synthesis fails** → write `error: cannot produce session log`, exit to IDLE.
- **Stub session** → write `error: session at <path> is a stub, refusing to compile`, exit to IDLE.
- **Topic is too vague** (e.g., "make a post") → write `error: topic is too vague, please be more specific`, exit to IDLE.
- **Session log has all-empty body sections** → write `error: session has no evidence, refusing to compile`, exit to IDLE.
- **Classifier tool fails AND LLM classification is unclear** → use sensible defaults (S10 / TOFU / L2 / builder-to-lead-system) and log a warning.

## Tools

```bash
# PRIMARY — synthesize from opencode DB (captures the actual pre-/post session, 5s timeout)
python3 <vault_path>/tools/researcher.py synthesize-session --out <vault_path>/content/sessions/YYYY-MM-DD-session-current.md --cwd <vault_path>

# FALLBACK — write session log directly from context (only if MD has the conversation in context)
cat > <vault_path>/content/sessions/YYYY-MM-DD-session-current.md << 'EOF'
...full frontmatter + sections...
EOF

# Mechanical classification (fast, keyword-based — run this every time)
python3 <vault_path>/tools/researcher.py classify --input <path-to-session-file> --kind session|topic

# Manual capture (rare — only if you have a pre-written transcript file)
python3 <vault_path>/tools/capture-session.py --vault <vault_path> --transcript-file <path>
```
