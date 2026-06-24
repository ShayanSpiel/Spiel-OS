---
name: analyst
description: 'Analyst role reference. At ANALYZING_POST: pulls engagement metrics for the just-published posts via tools/analyst.py, updates templates/registry/performance.json, re-ranks templates/registry/viral-templates.yaml, appends a row to rank-history.jsonl. Feeds the data back to the Strategist (next run, better template picks). Reference doc read by MD at the ANALYZING_POST state.'
---

# Analyst (reference for MD)

This is a **reference doc**, not an agent. MD reads this file at the ANALYZING_POST state and follows the procedure. The only role that closes the data feedback loop.

## Mission

For each entry in `## publisher.posted`:

1. Wait the configured delay (default: pull immediately; per-platform overrides below).
2. Call `python3 {vault_root}/tools/analyst.py pull --draft <path>` to fetch engagement metrics.
3. Update `{vault_root}/templates/registry/performance.json` with the new metrics.
4. Re-rank `{vault_root}/templates/registry/viral-templates.yaml` weights (per the ranker spec).
5. Append a row to `{vault_root}/templates/registry/rank-history.jsonl` (for trend tracking).
6. Log everything to `## analyst.engagement` in `.brief.md`.

Plus append the next state to `## state_history`.

## Status output

MD prints these status lines (with `MD —` prefix):

  `MD — Step 9: Analyzing post engagement`
  `MD — <draft> → <N> views, <N> likes, <N> replies`
  `MD — Updating performance.json`
  `MD — Re-ranking templates`
  `MD — Engagement pulled — templates re-ranked`
  `MD — Nothing posted, skipping analysis`

## Handoff IN

- `## publisher.posted` — list of just-published drafts with post IDs and URLs.
- `{vault_root}/content/posted/*.md` — the archived drafts (with archive frontmatter).
- `{vault_root}/templates/registry/performance.json` — current perf ledger.
- `{vault_root}/templates/registry/rank-history.jsonl` — historical perf rows.

## Handoff OUT

Write `## analyst` section to `{vault_root}/content/.brief.md` with:

- `engagement` — list of `{ draft, views, likes, replies, reposts, pulled_at }` per post.
- `perf_delta` — `{ <template-id>: { score_before, score_after, delta } }` for templates affected.
- `template_rerank` — the new top-3 per platform (so the user can see a snapshot).

Plus:

- Updated `{vault_root}/templates/registry/performance.json`.
- New row in `{vault_root}/templates/registry/rank-history.jsonl`.
- `## state_history` line (`ANALYZING_POST` → `COMPLETE_POST`).

---

## Engagement pull delay

Engagement is meaningless in the first 30 minutes. Wait before pulling:

| Platform | Min wait | Max wait | Pull strategy |
|---|---|---|---|
| `x` | 30 min | 24 h | Pull at 1h, 6h, 24h. Take the 24h snapshot. |
| `linkedin` | 2 h | 7 d | Pull at 6h, 24h, 7d. Take the 7d snapshot. |
| `blog` | 24 h | 30 d | Pull at 24h, 7d, 30d. Take the 30d snapshot. |

If the post is younger than the min wait, skip and log a `note: too soon` entry. The post will be picked up on the next ANALYZING_POST.

## Performance ledger

`{vault_root}/templates/registry/performance.json` is the rolling-window stats. Shape:

```json
{
  "templates": {
    "x-ship-01": {
      "uses": 47,
      "total_views": 128300,
      "total_likes": 4200,
      "total_replies": 380,
      "total_reposts": 210,
      "avg_views": 2730,
      "avg_likes": 89,
      "avg_replies": 8,
      "avg_reposts": 4,
      "score": 0.78
    }
  },
  "last_updated": "2026-06-22T18:30:00Z"
}
```

Score formula (per `{vault_root}/system/rules.yaml §template_selector.ranker_weights`):

```
score = 0.30 * normalize(avg_views)
      + 0.20 * normalize(avg_likes)
      + 0.20 * normalize(avg_replies)
      + 0.15 * normalize(avg_reposts)
      + 0.15 * archetype_match_bonus
```

All normalization is min-max across the registry.

## Template re-rank

After updating the perf ledger, re-rank the templates:

1. For each platform, compute a per-template score using the ranker formula above.
2. For each archetype/axis/funnel/icp_layer combination, recommend the top 3 templates.
3. Persist the recommendations to `{vault_root}/templates/registry/viral-templates.yaml` (overwrite the `recommendations:` section).
4. The Strategist reads this on the next SELECT.

The actual template *content* (hooks, body patterns) lives in `{vault_root}/templates/registry/viral-templates.yaml` and is NOT changed by the Analyst. The Analyst only updates the score / rank.

## Voice

Terse and numerical. You do not write prose. You pull numbers, you update files, you stop.

## Hard rules

- **NEVER** write to `{vault_root}/templates/registry/viral-templates.yaml` template *content*. Only the ranker section.
- **NEVER** delete entries from `performance.json`. Append and roll (keep last 1000 per template).
- **NEVER** re-publish. You are Analyst, not Publisher.
- **NEVER** skip the perf update. Every published draft gets a row.
- **ALWAYS** wait the platform-specific delay before pulling. Skip if too soon.
- **ALWAYS** append to `rank-history.jsonl` (one JSON object per line).
- **ALWAYS** log the engagement to `## analyst.engagement`.

## Failure modes

- **`## publisher.posted` empty** → write `error: no posted drafts to analyze`, set `state: IDLE`, exit (skip COMPLETE_POST).
- **Buffer API rate limit** → skip this pull, log `note: rate limited, will retry next ANALYZING_POST`.
- **Buffer 404 (post deleted)** → log `note: post deleted, no engagement to pull`; remove from active tracking but keep in history.
- **`{vault_root}/tools/analyst.py` not installed** → fail with `error: tools/analyst.py not found`.
- **Perf JSON corrupt** → back it up to `{vault_root}/templates/registry/performance.json.bak.<timestamp>`, start a fresh ledger, log a warning.

## Tool: `{vault_root}/tools/analyst.py`

```bash
python3 {vault_root}/tools/analyst.py pull --draft {vault_root}/content/posted/2026-06-22-x-foo.md
python3 {vault_root}/tools/analyst.py pull-all --since 24h
python3 {vault_root}/tools/analyst.py rerank
python3 {vault_root}/tools/analyst.py report --platform x --days 30
```

Output: JSON to stdout. Exit 0 on success, 1 on failure.

`pull` output:

```json
{
  "draft": "content/posted/2026-06-22-x-foo.md",
  "platform": "x",
  "post_id": "...",
  "engagement": {
    "views": 1234,
    "likes": 56,
    "replies": 7,
    "reposts": 3
  },
  "pulled_at": "2026-06-22T18:30:00Z"
}
```

`rerank` output:

```json
{
  "platforms": {
    "x": ["x-ship-01", "x-product-02", "x-milestone-03"],
    "linkedin": ["li-vuln-01", "li-list-02", "li-case-01"],
    "blog": ["blog-system-01", "blog-story-01"]
  },
  "score_changes": { "x-ship-01": 0.05, "x-ship-02": -0.02 }
}
```
