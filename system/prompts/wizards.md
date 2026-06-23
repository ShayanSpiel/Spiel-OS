---
key: wizards
title: Wizard banners
audience: subagent (copywriter, publisher)
status: canonical
---

# Wizard banners

These strings are printed at human checkpoints. The subagent that owns the state must read them, relay them to the user via the `question` tool, and WAIT for the user's exact answer.

## Format wizard (Copywriter, DRAFTING)

Printed by the Copywriter after the Strategist handoff:

```
FORMAT WIZARD — Pick platforms. Copywriter MUST ask the user.

╔════════════════════════════════════════════════════════════╗
║  HUMAN CHECKPOINT — DO NOT AUTO-PICK                      ║
║  Copywriter: relay this prompt to the user and WAIT.      ║
╚════════════════════════════════════════════════════════════╝

CORE INSIGHT
"<one-sentence summary of what the draft will deliver>"

  [x] X (280 chars, high volume)
  [ ] LinkedIn (3000 chars, medium volume)
  [ ] Blog (2500 words, low volume)

Commands: [x/X] Toggle X   [l] Toggle LinkedIn   [b] Toggle Blog
          [a] Select all/none   [h] Hold   [Enter] Confirm
```

Copywriter must:
1. Relay the prompt to the user via `question` tool.
2. WAIT for the user's answer.
3. Parse and write `formats: [...]` to brief frontmatter.

Allowed answer forms: `x`, `linkedin`, `blog`, `x linkedin`, `x,blog`, `all`, `hold`.

## Publish wizard (Publisher, PUBLISHING)

Printed by the Publisher after gates pass, per draft:

```
PUBLISH WIZARD — Per-draft decision. Publisher MUST ask the user.

╔════════════════════════════════════════════════════════════╗
║  HUMAN CHECKPOINT — DO NOT AUTO-PICK                      ║
║  Publisher: show each draft panel and ask the user per    ║
║  draft.                                                    ║
╚════════════════════════════════════════════════════════════╝

  3 draft(s) ready

▸ 1. 2026-06-20-x-draft.md   [X]
    Hook: <first 80 chars of body>
    Gates: 28/29 pass (warn: 1 sentence cap)
    Topic kind: announcement

    p / h / r <reason> / s ?
```

Publisher must:
1. Show each panel via `question` tool.
2. Ask the user per-draft: publish / hold / reject (with reason) / skip.
3. WAIT for the user's full answer set.
4. Write `publish_decisions` to brief frontmatter, dispatch, archive.

## Hard rules for subagents

- **NEVER** auto-pick. Wizard prompts = stop and ask via `question` tool.
- **NEVER** reference internal labels in public drafts (no `S1`, `TOFU`, `L1`, etc.).
- If blocked, report the exact command/output and current phase. Do not invent menu options.
