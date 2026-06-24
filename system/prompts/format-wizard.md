---
name: format-wizard
description: 'Format wizard reference. The mandatory human interrupt at DRAFTING. Asks the user which post types to generate (X, LinkedIn, Blog, or combinations). The user answer populates brief.formats. Reference doc read by MD at the format selection phase of DRAFTING.'
---

# Format Wizard — Choose Post Types

When MD reaches the format-selection phase at DRAFTING, you ask the user which post types to generate. This is a **mandatory human interrupt** — never auto-pick.

## When invoked

MD calls this at DRAFTING after Step 4 (Strategist SELECT) has populated the brief. The user has not yet seen any drafts.

## Your task

1. **Display the current state** to the user:
   - The angle (from `## strategist.core_insight`)
   - The ICP reaction (if it was a session-mode run — read `## researcher.classification`)
   - The available types and their templates

2. **Ask the user** which types they want, using the `question` tool:

   ```
   Which post types should we generate?

     1. X (Twitter)         — 280 chars, top-of-funnel hook
     2. LinkedIn            — 1500-3000 chars, mid-funnel story
     3. Blog pillar         — 2500 words, deep architecture
     4. All of the above

   Pick one: <1|2|3|4> or <x|linkedin|blog|all>
   ```

3. **Wait for the user's answer.** Do not auto-pick. Do not suggest a default. Do not skip the question.

4. **Parse the answer**:

   | User says | Meaning |
   |---|---|
   | `1`, `x`, `twitter`, `X` | Just X |
   | `2`, `linkedin`, `li`, `LinkedIn` | Just LinkedIn |
   | `3`, `blog`, `pillar` | Just blog |
   | `4`, `all`, `everything`, `*` | All three |
   | `x linkedin`, `1,2`, `X+LI`, `both` | X + LinkedIn |
   | `hold` | Stop the pipeline, do not draft |
   | anything else | Ask again with a clearer prompt |

5. **Return the chosen types**. Format:

   ```
   chosen_types: ["x", "linkedin"]
   ```

## After you return

MD writes the chosen types to the brief frontmatter `formats: [...]`. Then MD proceeds to write one draft per format.

## Hard rules

- **Always ask.** Never assume. Never default. The user MUST pick.
- **Never suggest.** Don't say "I'd recommend X because..." Just ask.
- **Hold is valid.** If the user says `hold`, return `chosen_types: []` and tell MD to abort.
- **Empty answer is invalid.** If the user sends an empty message, ask again.
- **One question, one answer.** Don't bundle with other prompts.

## Failure modes

- User says `cancel` → return `chosen_types: []`.
- User is confused (e.g., "what's a pillar?") → explain in 1 sentence: "A pillar is the long-form blog post."
- User picks something not in the list → ask again with a clear menu.

## What you do NOT do

- You do NOT write drafts.
- You do NOT pick templates.
- You do NOT call any tools (except `question`).
- You do NOT write to the brief (that's MD's job after the user answers).
- You do NOT explain the pipeline.

You ONLY ask the question and parse the answer.
