# Submission — Token Optimization Hackathon (Track A)

## The app + repo link

**Edit-War Detective** — a custom Track A app (not a modification of Aarav's
repo). A noir-detective-themed tool-calling agent over the full revision
history of the Wikipedia article "2026 FIFA World Cup," with the retrieval
layer implemented as two explicit, separately-tested stages.

- Local path: `edit-war-detective/`
- Core engine: [`engine.py`](engine.py) (agent loop + tool schemas + persona)
- Retrieval + augment split: [`wikitools/case_tools.py`](wikitools/case_tools.py),
  [`wikitools/augment.py`](wikitools/augment.py)
- Full pipeline: [`wikitools/`](wikitools/) (reverts, chunking, indexing,
  aggregate, retrieve, ledger) — 59 tests, all passing, in [`tests/`](tests/)

Representative query used for all numbers below:

> *"I'm a new editor who wants to add the final match result to the 2026 FIFA
> World Cup article without getting reverted. Based on the full history,
> when's the safest time to edit — and is that window still safe during the
> tournament (June 1 to July 20, 2026)?"*

## BEFORE number

**1,193,518 tokens**, printed by tiktoken (`cl100k_base`) over the raw
revision metadata a naive tool call would return for this query: 7,532
baseline-period revisions + 1,701 live-period (tournament) revisions,
retrieved unmodified by `retrieve_raw_revisions()`.

(This is the conservative, honest baseline: revision *metadata* only —
timestamp, editor, comment, size, sha1, tags — not full article wikitext. If
the naive tool instead dumped full wikitext per revision, as our reference
module's naive baseline does, the number would be in the tens of millions of
tokens; we report the smaller, fairer number here.)

## AFTER number

**61 tokens** — the compressed safety verdict returned by
`find_safe_edit_window()` after the augment stage runs:

```json
{
  "safest_baseline_window": "Thu-08",
  "baseline_rate": 0.0435,
  "baseline_edits_sampled": 23,
  "live_rate": 0.0,
  "live_edits_sampled": 7,
  "still_safe": true
}
```

**Reduction factor: ~19,566x** (1,193,518 / 61).

## Index design

`casefiles/index.json` — one entry per calendar-month chunk (the natural
seam: 165 months, July 2012 to July 2026):

```json
{
  "chunk_id": "2026_FIFA_World_Cup_2026-06",
  "article": "2026 FIFA World Cup",
  "month": "2026-06",
  "revision_count": 1107,
  "editors": ["0m9Ep", "1995hoo", "24Eleven2007", ...],
  "revert_count": 84,
  "path": "casefiles/2026_FIFA_World_Cup_2026-06.json"
}
```

Metadata keys chosen: `chunk_id`, `article`, `month`, `revision_count`,
`editors`, `revert_count`, `path`. No revision content or comment text ever
enters the index — it stays small enough to scan in full before deciding
which chunk files to open.

**Key added after seeing a real query:** `revert_count` wasn't in the
original design (the reference module's index has no equivalent field,
since weather chunks don't have an analogous "how contentious was this
chunk" signal) — we added it once we needed to answer "which months were the
worst" without opening every chunk file first; it lets the retrieval tool (and
a human skimming the index) rank chunks by contentiousness for free, straight
from metadata.

## Cost projection

Model: `llama-3.3-70b-versatile` (Groq), assumed at **$0.59 / million input
tokens**. Volume: **50 queries/day** (conservative for a hot article
during a live tournament — patrollers, admins, and new editors checking
edit-safety repeatedly per day).

| | Daily | Monthly | Yearly |
|---|---|---|---|
| BEFORE | $35.21 | $1,056.26 | $12,851.21 |
| AFTER | $0.0018 | $0.054 | $0.66 |
| **Saved** | **$35.21** | **$1,056.21** | **$12,850.55** |

**Volume bar: cleared.** At 50 queries/day this is a daily, multi-user
workflow (any active/contentious Wikipedia article during a live news event),
well above the threshold where the yearly bill justifies the engineering
time — the naive approach alone would cost **~$12,851/year** for this single
query pattern on this single article; the optimized pipeline drops that to
**66 cents**.
